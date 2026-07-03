"""Rule-based diagnosis of timing paths.

Works entirely from the parsed report — no external services. Each rule
inspects structural features of a path (logic depth, dominant stage delay,
clock skew, endpoint type) and contributes fix suggestions with priorities.
"""

from typing import List, Optional

from .schemas import (
    AnalysisResult,
    AnalyzedPath,
    PathDiagnosis,
    ReportSummary,
    Suggestion,
    TimingPath,
)

# A single stage eating this fraction of the path delay is a bottleneck.
BOTTLENECK_SHARE = 0.35
# Paths at least this deep are candidates for pipelining.
DEEP_LOGIC_DEPTH = 8
# Moderately deep paths get a restructuring suggestion instead.
MODERATE_LOGIC_DEPTH = 5

_CLOCK_PIN_SUFFIXES = ("/CK", "/CLK", "/CKN", "/G")
_PORT_CELLS = {"in", "out", "inout"}


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


def _setup_suggestions(path: TimingPath, diagnosis: PathDiagnosis) -> List[Suggestion]:
    suggestions = []

    if (
        diagnosis.bottleneck_share is not None
        and diagnosis.bottleneck_share >= BOTTLENECK_SHARE
        and diagnosis.bottleneck_delay
        and diagnosis.bottleneck_delay > 0
    ):
        suggestions.append(Suggestion(
            fix=f"Upsize or swap {diagnosis.bottleneck_instance} ({diagnosis.bottleneck_cell}) "
                f"for a higher drive-strength variant",
            priority="high",
            reason=f"This single stage contributes {diagnosis.bottleneck_delay:.2f} ns, "
                   f"{diagnosis.bottleneck_share:.0%} of the path's logic delay — the path "
                   f"is limited by one slow cell, not overall depth.",
        ))

    if diagnosis.logic_depth >= DEEP_LOGIC_DEPTH:
        suggestions.append(Suggestion(
            fix="Pipeline the path: insert a register stage near its midpoint",
            priority="high",
            reason=f"{diagnosis.logic_depth} levels of combinational logic between "
                   f"launch and capture is too deep to close at this clock period; "
                   f"splitting it across two cycles halves the per-cycle delay.",
        ))
    elif diagnosis.logic_depth >= MODERATE_LOGIC_DEPTH:
        suggestions.append(Suggestion(
            fix="Restructure the logic cone to reduce depth",
            priority="medium",
            reason=f"{diagnosis.logic_depth} logic levels is on the deep side; "
                   f"re-synthesis with a depth constraint, or rebalancing the "
                   f"expression tree, can usually save one or two levels.",
        ))

    if diagnosis.clock_skew is not None and diagnosis.clock_skew < -0.01:
        suggestions.append(Suggestion(
            fix="Balance the clock tree between launch and capture flops",
            priority="medium",
            reason=f"The capture clock arrives {abs(diagnosis.clock_skew):.2f} ns earlier "
                   f"than the launch clock; this negative skew directly reduces the "
                   f"time available for the data path.",
        ))

    if path.endpoint and path.logic_chain and path.logic_chain[-1].cell in _PORT_CELLS:
        suggestions.append(Suggestion(
            fix=f"Revisit the output external delay budgeted on port {path.endpoint}",
            priority="low",
            reason="The endpoint is an output port, so part of the budget is the "
                   "assumed external delay in the constraints — if it is pessimistic, "
                   "the violation may not be real.",
        ))

    if not suggestions:
        suggestions.append(Suggestion(
            fix="Reduce load on the path: shorten routes, lower fanout, or use "
                "faster threshold-voltage cells",
            priority="medium",
            reason="No single stage or structural feature dominates this path; the "
                   "delay is spread evenly, so incremental sizing and load "
                   "reduction across the path is the usual approach.",
        ))

    return suggestions


def _hold_suggestions(path: TimingPath, diagnosis: PathDiagnosis) -> List[Suggestion]:
    suggestions = [Suggestion(
        fix="Insert delay buffers on the data path",
        priority="high",
        reason=f"The data arrives {abs(path.slack):.2f} ns too early at the capture "
               f"flop; padding the short path with buffer delay is the standard "
               f"hold fix and does not affect the setup-critical paths.",
    )]

    if diagnosis.clock_skew is not None and diagnosis.clock_skew > 0.01:
        suggestions.append(Suggestion(
            fix="Reduce clock skew into the capture flop",
            priority="medium",
            reason=f"The capture clock arrives {diagnosis.clock_skew:.2f} ns after the "
                   f"launch clock; positive skew tightens the hold requirement, so "
                   f"balancing the clock tree relaxes this check.",
        ))

    suggestions.append(Suggestion(
        fix="Re-check this path after clock tree synthesis and routing",
        priority="low",
        reason="Hold violations with ideal clocks are often optimistic or "
               "pessimistic; the real skew after CTS decides whether a fix is "
               "actually needed.",
    ))

    return suggestions


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

    if path.status == "VIOLATED":
        diagnosis.severity = _severity(path)
        if check_type == "setup":
            diagnosis.suggestions = _setup_suggestions(path, diagnosis)
        else:
            diagnosis.suggestions = _hold_suggestions(path, diagnosis)

    return diagnosis


def analyze_report(paths: List[TimingPath]) -> AnalysisResult:
    analyzed = [AnalyzedPath(path=p, diagnosis=diagnose_path(p)) for p in paths]

    violated = [a for a in analyzed if a.path.status == "VIOLATED"]
    negative_slacks = [a.path.slack for a in violated]

    summary = ReportSummary(
        total_paths=len(analyzed),
        violated_paths=len(violated),
        met_paths=len(analyzed) - len(violated),
        wns=min(negative_slacks) if negative_slacks else None,
        tns=round(sum(s for s in negative_slacks if s < 0), 4),
        setup_violations=sum(1 for a in violated if a.diagnosis.check_type == "setup"),
        hold_violations=sum(1 for a in violated if a.diagnosis.check_type == "hold"),
    )

    return AnalysisResult(summary=summary, paths=analyzed)
