"""Rule-based diagnosis of timing paths.

Works entirely from the parsed report — no external services. Diagnosis has
three layers:

1. Per-path features (logic depth, dominant stage, repeated-cell runs, clock
   skew) computed in `diagnose_path`.
2. Rules: small functions registered with `@setup_rule` / `@hold_rule`. Each
   inspects one path and returns a `Suggestion` or None, and the suggestion
   carries the rule's id so the UI can show which rule fired.
3. Report-level analysis in `analyze_report`: hold/setup interplay on the same
   endpoint, and grouping of violations that share a root cause.
"""

import math
import re
import statistics
from collections import defaultdict
from typing import Callable, Dict, List, Optional

from .schemas import (
    AnalysisResult,
    AnalyzedPath,
    PathDiagnosis,
    ReportSummary,
    Suggestion,
    TimingPath,
    ViolationGroup,
)

# A single stage eating this fraction of the path delay is a bottleneck.
BOTTLENECK_SHARE = 0.35
# Paths at least this deep are candidates for pipelining.
DEEP_LOGIC_DEPTH = 8
# Moderately deep paths get a restructuring suggestion instead.
MODERATE_LOGIC_DEPTH = 5
# This many identical cells in a row looks like a serial (ripple-style) chain.
REPEATED_RUN_MIN = 4
# A driver with at least this fanout is worth buffering or duplicating.
HIGH_FANOUT = 8
# Drive strengths from this value up are treated as "already big".
MAX_USEFUL_DRIVE = 8
# Drive strengths nearly every library offers (some add 3, 6, 12), used to pick the next size up.
DRIVE_STEPS = [1, 2, 4, 8, 16]

_CLOCK_PIN_SUFFIXES = ("/CK", "/CLK", "/CKN", "/G")
_PORT_CELLS = {"in", "out", "inout"}

# "NAND2_X1" -> ("NAND2_X", 1); "sky130_fd_sc_hd__maj3_2" -> ("...maj3_", 2)
_DRIVE_SUFFIX = re.compile(r"^(.*[_X])(\d+)$")


# ---------- helpers ----------

def _is_clock_pin(instance: str) -> bool:
    return instance.upper().endswith(_CLOCK_PIN_SUFFIXES)


def _combinational_stages(path: TimingPath) -> list:
    """Chain stages that are actual logic, excluding clock pins and ports."""
    start_inst = path.startpoint.split("/")[0]
    end_inst = path.endpoint.split("/")[0]
    stages = []
    for stage in path.logic_chain:
        if _is_clock_pin(stage.instance) or stage.cell in _PORT_CELLS:
            continue
        inst = stage.instance.split("/")[0]
        if inst in (start_inst, end_inst):
            continue
        stages.append(stage)
    return stages


def split_drive(cell: str):
    """Split a library cell name into (family, drive strength).

    Works for Nangate-style `NAND2_X1` and sky130-style `..._nand2_4`. Returns
    (cell, None) when the name has no recognizable drive suffix.
    """
    match = _DRIVE_SUFFIX.match(cell)
    if not match:
        return cell, None
    return match.group(1), int(match.group(2))


def _next_drive(drive: int) -> Optional[int]:
    for step in DRIVE_STEPS:
        if step > drive:
            return step
    return None


def _cell_family(cell: str) -> str:
    return split_drive(cell)[0]


def _short_family(cell: str) -> str:
    """Readable family name: drop library prefix and drive suffix."""
    return _cell_family(cell).split("__")[-1].rstrip("_X")


def _severity(path: TimingPath) -> str:
    """Bucket severity by how large the violation is relative to the clock
    period when we know it, or by absolute slack otherwise."""
    magnitude = abs(path.slack)
    if path.capture_edge and path.capture_edge > 0:
        ratio = magnitude / path.capture_edge
        if ratio > 0.20:
            return "critical"
        if ratio > 0.10:
            return "high"
        if ratio > 0.03:
            return "medium"
        return "low"
    if magnitude > 1.0:
        return "critical"
    if magnitude > 0.5:
        return "high"
    if magnitude > 0.1:
        return "medium"
    return "low"


# ---------- rule registry ----------

Rule = Callable[[TimingPath, PathDiagnosis], Optional[Suggestion]]

SETUP_RULES: Dict[str, Rule] = {}
HOLD_RULES: Dict[str, Rule] = {}


def _register(table: Dict[str, Rule], rule_id: str):
    def wrap(fn: Rule) -> Rule:
        table[rule_id] = fn
        return fn
    return wrap


def setup_rule(rule_id: str):
    return _register(SETUP_RULES, rule_id)


def hold_rule(rule_id: str):
    return _register(HOLD_RULES, rule_id)


def _suggest(rule_id: str, fix: str, priority: str, reason: str) -> Suggestion:
    return Suggestion(rule_id=rule_id, fix=fix, priority=priority, reason=reason)


# ---------- setup rules ----------

@setup_rule("slow-cell")
def _slow_cell(path: TimingPath, d: PathDiagnosis) -> Optional[Suggestion]:
    if not (d.bottleneck_share is not None and d.bottleneck_share >= BOTTLENECK_SHARE
            and d.bottleneck_delay):
        return None

    _, drive = split_drive(d.bottleneck_cell)
    gap = abs(path.slack)
    gap_share = gap / d.bottleneck_delay if d.bottleneck_delay else 0
    reason = (
        f"This single stage contributes {d.bottleneck_delay:.2f} ns, "
        f"{d.bottleneck_share:.0%} of the path's logic delay — the path is limited "
        f"by one slow cell, not overall depth. The violation is {gap:.2f} ns, "
        f"{gap_share:.0%} of this stage's delay"
    )

    if drive is not None and drive >= MAX_USEFUL_DRIVE:
        return _suggest(
            "slow-cell",
            f"Split the load of {d.bottleneck_instance} ({d.bottleneck_cell}) or move its "
            f"fanout to a buffer",
            "high",
            reason + f". The cell is already at drive strength {drive}, so resizing "
            f"further won't help much; reduce what it drives instead.",
        )

    if drive is not None:
        target = _next_drive(drive)
        base, _ = split_drive(d.bottleneck_cell)
        fix = (f"Upsize {d.bottleneck_instance} from {d.bottleneck_cell} to "
               f"{base}{target} (next drive strength)")
        return _suggest("slow-cell", fix, "high",
                        reason + ", so a step up in drive is a realistic way to close it "
                        "(check the variant exists in your library and the input-cap "
                        "increase doesn't slow the previous stage).")

    return _suggest(
        "slow-cell",
        f"Upsize or swap {d.bottleneck_instance} ({d.bottleneck_cell}) for a "
        f"higher drive-strength variant",
        "high",
        reason + ".",
    )


@setup_rule("serial-chain")
def _serial_chain(path: TimingPath, d: PathDiagnosis) -> Optional[Suggestion]:
    if d.repeated_run < REPEATED_RUN_MIN or d.repeated_cell is None:
        return None
    total = d.total_logic_delay or 1.0
    share = (d.repeated_delay or 0) / total
    family = _short_family(d.repeated_cell)
    carry_like = bool(re.search(r"maj|(^|_)(fa|ha)\d*$", family.lower()))
    if carry_like:
        fix = (f"Replace the {d.repeated_run}-stage serial chain of {family} cells "
               f"with a parallel-prefix / carry-lookahead structure")
        why = ("A chain of identical majority / adder cells is a ripple-carry "
               "structure: delay grows linearly with width. ")
    else:
        fix = (f"Rebalance the {d.repeated_run}-stage serial chain of {family} cells "
               f"into a tree")
        why = ("A long run of the same gate usually means a reduction written as a "
               "linear chain; a balanced tree has logarithmic depth. ")
    return _suggest(
        "serial-chain", fix, "high" if share >= 0.4 else "medium",
        why + f"The run accounts for {d.repeated_delay:.2f} ns, {share:.0%} of the "
              f"path's logic delay, and resizing cells won't remove that structure.",
    )


@setup_rule("high-fanout")
def _high_fanout(path: TimingPath, d: PathDiagnosis) -> Optional[Suggestion]:
    loaded = [s for s in _combinational_stages(path)
              if s.fanout is not None and s.fanout >= HIGH_FANOUT]
    if not loaded:
        return None
    worst = max(loaded, key=lambda s: s.fanout)
    cap_note = f" ({worst.cap:.3f} pF)" if worst.cap is not None else ""
    return _suggest(
        "high-fanout",
        f"Buffer or duplicate the driver {worst.instance} (fanout {worst.fanout})",
        "medium",
        f"{worst.instance} ({worst.cell}) drives {worst.fanout} loads{cap_note}; "
        f"its stage takes {worst.delay:.2f} ns. Splitting the fanout with a buffer "
        f"tree or cloning the driver reduces load-dependent delay.",
    )


@setup_rule("logic-depth")
def _logic_depth(path: TimingPath, d: PathDiagnosis) -> Optional[Suggestion]:
    if d.logic_depth >= DEEP_LOGIC_DEPTH:
        return _suggest(
            "logic-depth",
            "Pipeline the path: insert a register stage near its midpoint",
            "high",
            f"{d.logic_depth} levels of combinational logic between launch and "
            f"capture is too deep to close at this clock period; splitting it across "
            f"two cycles halves the per-cycle delay.",
        )
    if d.logic_depth >= MODERATE_LOGIC_DEPTH:
        return _suggest(
            "logic-depth",
            "Restructure the logic cone to reduce depth",
            "medium",
            f"{d.logic_depth} logic levels is on the deep side; re-synthesis with a "
            f"depth constraint, or rebalancing the expression tree, can usually save "
            f"one or two levels.",
        )
    return None


@setup_rule("negative-skew")
def _negative_skew(path: TimingPath, d: PathDiagnosis) -> Optional[Suggestion]:
    if d.clock_skew is None or d.clock_skew >= -0.01:
        return None
    return _suggest(
        "negative-skew",
        "Balance the clock tree between launch and capture flops",
        "medium",
        f"The capture clock arrives {abs(d.clock_skew):.2f} ns earlier than the "
        f"launch clock; this negative skew directly reduces the time available for "
        f"the data path.",
    )


@setup_rule("io-constraint")
def _io_constraint(path: TimingPath, d: PathDiagnosis) -> Optional[Suggestion]:
    if not (path.endpoint and path.logic_chain and path.logic_chain[-1].cell in _PORT_CELLS):
        return None
    if path.external_delay is None:
        return _suggest(
            "io-constraint",
            f"Revisit the output external delay budgeted on port {path.endpoint}",
            "low",
            "The endpoint is an output port, so part of the budget is the assumed "
            "external delay in the constraints — if it is pessimistic, the violation "
            "may not be real.",
        )
    period = path.capture_edge if path.capture_edge else None
    share = f" ({path.external_delay / period:.0%} of the {period:.2f} ns period)" if period else ""
    covers = path.external_delay >= abs(path.slack)
    return _suggest(
        "io-constraint",
        f"Revisit the output external delay ({path.external_delay:.2f} ns) budgeted on "
        f"port {path.endpoint}",
        "medium" if covers else "low",
        f"The endpoint is an output port with {path.external_delay:.2f} ns of "
        f"external delay{share}. "
        + (f"Relaxing that budget by {abs(path.slack):.2f} ns would close this path "
           f"with no design change — worth confirming it matches the real off-chip "
           f"requirement." if covers else
           "The violation is larger than the external delay, so relaxing the "
           "constraint alone would not close it."),
    )


def _fallback_setup(path: TimingPath, d: PathDiagnosis) -> Suggestion:
    pct = f" (about {d.required_speedup:.0%} of the logic delay)" if d.required_speedup else ""
    return _suggest(
        "distributed-delay",
        "Reduce load on the path: shorten routes, lower fanout, or use faster "
        "threshold-voltage cells",
        "medium",
        f"No single stage or structural feature dominates this path; the delay is "
        f"spread evenly and {abs(path.slack):.2f} ns must be recovered{pct}, so "
        f"incremental sizing and load reduction across the path is the usual approach.",
    )


# ---------- hold rules ----------

def _typical_stage_delay(path: TimingPath) -> Optional[float]:
    delays = [s.delay for s in path.logic_chain if s.delay > 0]
    return statistics.median(delays) if delays else None


@hold_rule("hold-buffers")
def _hold_buffers(path: TimingPath, d: PathDiagnosis) -> Optional[Suggestion]:
    gap = abs(path.slack)
    typical = _typical_stage_delay(path)
    estimate = ""
    if typical and typical > 0:
        count = max(1, math.ceil(gap / typical))
        estimate = (f" Roughly {count} delay cell(s) at this path's typical "
                    f"{typical:.2f} ns per stage — a rough estimate; a real delay "
                    f"cell is usually slower per stage, so fewer may do.")
    return _suggest(
        "hold-buffers",
        "Insert delay buffers on the data path",
        "high",
        f"The data arrives {gap:.2f} ns too early at the capture flop; padding the "
        f"short path with buffer delay is the standard hold fix and does not affect "
        f"the setup-critical paths.{estimate}",
    )


@hold_rule("positive-skew")
def _positive_skew(path: TimingPath, d: PathDiagnosis) -> Optional[Suggestion]:
    if d.clock_skew is None or d.clock_skew <= 0.01:
        return None
    return _suggest(
        "positive-skew",
        "Reduce clock skew into the capture flop",
        "medium",
        f"The capture clock arrives {d.clock_skew:.2f} ns after the launch clock; "
        f"positive skew tightens the hold requirement, so balancing the clock tree "
        f"relaxes this check.",
    )


@hold_rule("recheck-post-cts")
def _recheck(path: TimingPath, d: PathDiagnosis) -> Optional[Suggestion]:
    return _suggest(
        "recheck-post-cts",
        "Re-check this path after clock tree synthesis and routing",
        "low",
        "Hold violations with ideal clocks are often optimistic or pessimistic; the "
        "real skew after CTS decides whether a fix is actually needed.",
    )


def list_rules() -> List[Dict[str, str]]:
    """Registered rule ids, for documentation and tests."""
    return (
        [{"id": rid, "check": "setup"} for rid in SETUP_RULES]
        + [{"id": rid, "check": "hold"} for rid in HOLD_RULES]
    )


# ---------- per-path diagnosis ----------

def _longest_repeated_run(stages: list):
    """Longest run of consecutive stages from the same cell family, ignoring
    drive strength. Returns (family cell name, length, total delay)."""
    best = (None, 0, 0.0)
    run_cell, run_len, run_delay = None, 0, 0.0
    for stage in stages:
        family = _cell_family(stage.cell)
        if family == run_cell:
            run_len += 1
            run_delay += stage.delay
        else:
            run_cell, run_len, run_delay = family, 1, stage.delay
        if run_len > best[1]:
            best = (stage.cell, run_len, run_delay)
    return best


def diagnose_path(path: TimingPath) -> PathDiagnosis:
    check_type = "hold" if path.path_type == "min" else "setup"

    stages = _combinational_stages(path)
    total_delay = sum(s.delay for s in stages)
    depth = len(stages)

    bottleneck = max(stages, key=lambda s: s.delay, default=None)

    skew = None
    if path.launch_clock_latency is not None and path.capture_clock_latency is not None:
        skew = round(path.capture_clock_latency - path.launch_clock_latency, 4)

    diagnosis = PathDiagnosis(
        check_type=check_type,
        logic_depth=depth,
        total_logic_delay=round(total_delay, 4),
        clock_skew=skew,
    )

    if bottleneck is not None and total_delay > 0:
        diagnosis.bottleneck_instance = bottleneck.instance
        diagnosis.bottleneck_cell = bottleneck.cell
        diagnosis.bottleneck_delay = bottleneck.delay
        diagnosis.bottleneck_share = round(bottleneck.delay / total_delay, 4)

    cell, length, run_delay = _longest_repeated_run(stages)
    if length >= 2:
        diagnosis.repeated_cell = cell
        diagnosis.repeated_run = length
        diagnosis.repeated_delay = round(run_delay, 4)

    if path.status == "VIOLATED":
        diagnosis.severity = _severity(path)
        if check_type == "setup":
            if total_delay > 0:
                diagnosis.required_speedup = round(abs(path.slack) / total_delay, 4)
            diagnosis.suggestions = _run_rules(SETUP_RULES, path, diagnosis)
            if not diagnosis.suggestions:
                diagnosis.suggestions = [_fallback_setup(path, diagnosis)]
        else:
            diagnosis.suggestions = _run_rules(HOLD_RULES, path, diagnosis)

    return diagnosis


def _run_rules(table: Dict[str, Rule], path: TimingPath, diagnosis: PathDiagnosis):
    results = []
    for rule in table.values():
        suggestion = rule(path, diagnosis)
        if suggestion is not None:
            results.append(suggestion)
    return _by_priority(results)


_PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def _by_priority(suggestions: List[Suggestion]) -> List[Suggestion]:
    # sorted() is stable, so rules of equal priority keep registration order.
    return sorted(suggestions, key=lambda s: _PRIORITY_ORDER[s.priority])


# ---------- report-level analysis ----------

def _add_hold_headroom(analyzed: List[AnalyzedPath]) -> None:
    """For each violated hold path, look up the setup slack of the same
    endpoint in this report. Padding a path for hold eats that setup slack, so
    it tells us whether the standard buffer fix is actually safe."""
    setup_slack: Dict[tuple, float] = {}
    for a in analyzed:
        if a.diagnosis.check_type == "setup":
            key = (a.path.startpoint, a.path.endpoint)
            setup_slack[key] = min(a.path.slack, setup_slack.get(key, a.path.slack))

    for a in analyzed:
        if a.diagnosis.check_type != "hold" or a.path.status != "VIOLATED":
            continue
        headroom = setup_slack.get((a.path.startpoint, a.path.endpoint))
        if headroom is None:
            continue
        gap = abs(a.path.slack)
        if headroom >= gap:
            suggestion = _suggest(
                "hold-setup-headroom",
                f"Delay padding up to {headroom:.2f} ns is safe on this path pair",
                "low",
                f"The matching setup path {a.path.startpoint} → {a.path.endpoint} has "
                f"{headroom:.2f} ns of slack, enough to absorb the {gap:.2f} ns of "
                f"delay this hold fix adds.",
            )
        else:
            suggestion = _suggest(
                "hold-setup-headroom",
                "Buffer padding alone cannot fix this: the setup side lacks room",
                "high",
                f"Fixing {gap:.2f} ns of hold needs that much extra delay, but the "
                f"matching setup path {a.path.startpoint} → {a.path.endpoint} only has "
                f"{headroom:.2f} ns of slack. Fix the clock skew or restructure the "
                f"path instead of padding it.",
            )
        a.diagnosis.suggestions = _by_priority(a.diagnosis.suggestions + [suggestion])


def _bus_key(name: str) -> str:
    """`resp_msg[15]` and `reg_3_/D`-style names -> a shared bus pattern."""
    return re.sub(r"\[\d+\]", "[*]", name)


def _find_groups(analyzed: List[AnalyzedPath]) -> List[ViolationGroup]:
    """Setup and hold violations have unrelated causes, so group them apart."""
    groups: List[ViolationGroup] = []
    for check in ("setup", "hold"):
        groups += _find_groups_for(analyzed, check)
    groups.sort(key=lambda g: (g.tns, -g.count))   # most negative TNS first
    return groups[:8]


def _find_groups_for(analyzed: List[AnalyzedPath], check: str) -> List[ViolationGroup]:
    violated = [(i, a) for i, a in enumerate(analyzed)
                if a.path.status == "VIOLATED" and a.diagnosis.check_type == check]
    if len(violated) < 2:
        return []
    total_tns = sum(a.path.slack for _, a in violated if a.path.slack < 0)

    def make(kind: str, key: str, members: List[int], detail: str) -> ViolationGroup:
        slacks = [analyzed[i].path.slack for i in members]
        tns = round(sum(s for s in slacks if s < 0), 4)
        return ViolationGroup(
            kind=kind, key=key, check_type=check, path_indices=sorted(members), count=len(members),
            worst_slack=min(slacks), tns=tns,
            tns_share=round(tns / total_tns, 4) if total_tns else 0.0,
            detail=detail,
        )

    groups: List[ViolationGroup] = []

    # Shared logic: an instance sitting on several violating paths. Instances
    # that sit on exactly the same set of paths are one cone; report the one
    # contributing the most delay.
    by_instance = defaultdict(lambda: defaultdict(float))
    for i, a in violated:
        for stage in _combinational_stages(a.path):
            by_instance[stage.instance.split("/")[0]][i] += stage.delay
    by_pathset = defaultdict(list)
    for inst, contrib in by_instance.items():
        if len(contrib) >= 2:
            by_pathset[frozenset(contrib)].append((sum(contrib.values()), inst))
    for pathset, insts in by_pathset.items():
        insts.sort(reverse=True)
        _, top = insts[0]
        others = len(insts) - 1
        extra = f" (plus {others} more cell(s) shared by exactly these paths)" if others else ""
        groups.append(make(
            "shared_logic", top, list(pathset),
            f"{top} sits on {len(pathset)} violating paths{extra}. A fix to this "
            f"shared logic helps all of them.",
        ))

    # Buses: endpoints that differ only by an index.
    by_bus = defaultdict(list)
    for i, a in violated:
        by_bus[_bus_key(a.path.endpoint)].append(i)
    for key, members in by_bus.items():
        if len(members) >= 2 and "[*]" in key:
            groups.append(make(
                "endpoint_bus", key, members,
                f"{len(members)} violating paths end on the same bus ({key}); "
                f"likely one shared cause upstream (a common structure such as a "
                f"carry chain or shared control signal).",
            ))

    # Common startpoint.
    by_start = defaultdict(list)
    for i, a in violated:
        by_start[a.path.startpoint].append(i)
    for key, members in by_start.items():
        if len(members) >= 2:
            groups.append(make(
                "startpoint", key, members,
                f"{len(members)} violating paths launch from {key}; upsizing it or "
                f"reducing its fanout helps all of them.",
            ))

    # Same bottleneck cell type across paths.
    by_cell = defaultdict(list)
    for i, a in violated:
        cell = a.diagnosis.bottleneck_cell
        share = a.diagnosis.bottleneck_share or 0
        # A slow cell only matters for setup; hold paths are short on purpose.
        if check == "setup" and cell and share >= BOTTLENECK_SHARE:
            by_cell[cell].append(i)
    for key, members in by_cell.items():
        if len(members) >= 2:
            groups.append(make(
                "bottleneck_cell", key, members,
                f"{key} is the dominant slow stage on {len(members)} violating "
                f"paths; a library or sizing change for this cell has wide effect.",
            ))

    # Several kinds often describe the same set of paths; keep the most
    # actionable one (order below) and drop the repeats.
    seen = set()
    unique = []
    order = {"shared_logic": 0, "endpoint_bus": 1, "startpoint": 2, "bottleneck_cell": 3}
    for g in sorted(groups, key=lambda g: (order[g.kind], -g.count)):
        signature = tuple(g.path_indices)
        if signature not in seen:
            seen.add(signature)
            unique.append(g)

    return unique


def analyze_report(paths: List[TimingPath], skipped_blocks: int = 0) -> AnalysisResult:
    analyzed = [AnalyzedPath(path=p, diagnosis=diagnose_path(p)) for p in paths]
    _add_hold_headroom(analyzed)

    violated = [a for a in analyzed if a.path.status == "VIOLATED"]
    negative_slacks = [a.path.slack for a in violated]
    tns = round(sum(s for s in negative_slacks if s < 0), 4)

    summary = ReportSummary(
        total_paths=len(analyzed),
        violated_paths=len(violated),
        met_paths=len(analyzed) - len(violated),
        wns=min(negative_slacks) if negative_slacks else None,
        tns=tns,
        setup_violations=sum(1 for a in violated if a.diagnosis.check_type == "setup"),
        hold_violations=sum(1 for a in violated if a.diagnosis.check_type == "hold"),
        skipped_blocks=skipped_blocks,
    )

    return AnalysisResult(
        summary=summary,
        paths=analyzed,
        groups=_find_groups(analyzed),
    )
