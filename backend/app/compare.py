"""Compare two analyses of the same design (e.g. before and after a fix).

Paths are matched by (startpoint, endpoint, check type, path group). Only
paths that violate in at least one report are interesting, so paths that meet
timing in both are left out.
"""

from typing import Dict, List, Tuple

from .schemas import AnalysisResult, ComparisonResult, PathDelta

# Slack changes smaller than this (ns) are treated as noise.
EPSILON = 0.005

Key = Tuple[str, str, str, str]


def _index(result: AnalysisResult) -> Dict[Key, "object"]:
    paths = {}
    for a in result.paths:
        key = (a.path.startpoint, a.path.endpoint, a.diagnosis.check_type, a.path.path_group)
        # Multiple paths can share a key (e.g. several corners); keep the worst.
        if key not in paths or a.path.slack < paths[key].path.slack:
            paths[key] = a
    return paths


def _delta(key: Key, before, after) -> PathDelta:
    before_slack = before.path.slack if before else None
    after_slack = after.path.slack if after else None
    delta = None
    if before_slack is not None and after_slack is not None:
        delta = round(after_slack - before_slack, 4)
    return PathDelta(
        startpoint=key[0], endpoint=key[1], check_type=key[2],
        before=before_slack, after=after_slack, delta=delta,
    )


def compare_results(
    base: AnalysisResult, new: AnalysisResult,
    base_id: int, new_id: int, base_filename: str, new_filename: str,
) -> ComparisonResult:
    old_paths, new_paths = _index(base), _index(new)

    fixed: List[PathDelta] = []
    improved: List[PathDelta] = []
    regressed: List[PathDelta] = []
    unchanged: List[PathDelta] = []
    new_violations: List[PathDelta] = []
    dropped: List[PathDelta] = []

    for key in old_paths.keys() | new_paths.keys():
        before, after = old_paths.get(key), new_paths.get(key)
        was_bad = before is not None and before.path.status == "VIOLATED"
        is_bad = after is not None and after.path.status == "VIOLATED"

        if not was_bad and not is_bad:
            continue
        delta = _delta(key, before, after)

        if before is None:
            new_violations.append(delta)
        elif after is None:
            dropped.append(delta)
        elif was_bad and not is_bad:
            fixed.append(delta)
        elif not was_bad and is_bad:
            new_violations.append(delta)
        elif delta.delta > EPSILON:
            improved.append(delta)
        elif delta.delta < -EPSILON:
            regressed.append(delta)
        else:
            unchanged.append(delta)

    # Worst first, so the important rows lead each list.
    for bucket in (fixed, improved, regressed, unchanged, new_violations, dropped):
        bucket.sort(key=lambda d: (d.after if d.after is not None else d.before))

    return ComparisonResult(
        base_id=base_id, new_id=new_id,
        base_filename=base_filename, new_filename=new_filename,
        wns_before=base.summary.wns, wns_after=new.summary.wns,
        tns_before=base.summary.tns, tns_after=new.summary.tns,
        violations_before=base.summary.violated_paths,
        violations_after=new.summary.violated_paths,
        fixed=fixed, improved=improved, regressed=regressed,
        unchanged=unchanged, new_violations=new_violations, dropped=dropped,
    )
