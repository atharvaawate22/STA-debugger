from app.compare import compare_results
from app.rules import analyze_report
from app.schemas import TimingPath
from app.sta_parser import STAParser


def analyze(text):
    return analyze_report(STAParser(text).parse())


def compare(base, new):
    return compare_results(base, new, 1, 2, "before.txt", "after.txt")


def tp(end, slack, ptype="max", start="r1"):
    return TimingPath(startpoint=start, endpoint=end, path_group="clk", path_type=ptype,
                      slack=slack, status="VIOLATED" if slack < 0 else "MET", logic_chain=[])


def endpoints(bucket):
    return sorted(d.endpoint for d in bucket)


def test_before_after_pair(adder_before, adder_after):
    result = compare(analyze(adder_before), analyze(adder_after))

    assert endpoints(result.fixed) == ["q0", "sumreg[4]"]
    assert endpoints(result.improved) == ["sumreg[5]", "sumreg[6]"]
    assert endpoints(result.unchanged) == ["st"]          # the hold conflict is still there
    # The setup fix on `ctl -> st` and the deeper `ptr -> st` path both went bad.
    assert len(result.new_violations) == 2
    assert result.regressed == []
    assert result.dropped == []

    assert result.wns_before == -0.83 and result.wns_after == -0.47
    assert result.tns_before < result.tns_after < 0
    assert (result.violations_before, result.violations_after) == (5, 5)


def test_regression_is_reported_with_delta():
    base = analyze_report([tp("a", -0.10)])
    new = analyze_report([tp("a", -0.40)])
    result = compare(base, new)
    assert [(d.before, d.after, d.delta) for d in result.regressed] == [(-0.10, -0.40, -0.30)]
    assert result.fixed == result.improved == result.new_violations == []


def test_tiny_slack_changes_are_noise():
    result = compare(analyze_report([tp("a", -0.100)]), analyze_report([tp("a", -0.102)]))
    assert endpoints(result.unchanged) == ["a"]
    assert result.improved == result.regressed == []


def test_met_in_both_reports_is_omitted():
    result = compare(analyze_report([tp("a", 0.5)]), analyze_report([tp("a", 0.7)]))
    assert not any([result.fixed, result.improved, result.regressed,
                    result.unchanged, result.new_violations, result.dropped])


def test_paths_only_in_one_report():
    base = analyze_report([tp("old", -0.2)])
    new = analyze_report([tp("fresh", -0.3)])
    result = compare(base, new)
    assert endpoints(result.dropped) == ["old"]
    assert endpoints(result.new_violations) == ["fresh"]
    assert result.new_violations[0].before is None


def test_setup_and_hold_on_same_pair_are_kept_apart():
    base = analyze_report([tp("a", -0.2, "max"), tp("a", 0.3, "min")])
    new = analyze_report([tp("a", 0.1, "max"), tp("a", -0.3, "min")])
    result = compare(base, new)
    assert [(d.check_type, d.after) for d in result.fixed] == [("setup", 0.1)]
    assert [(d.check_type, d.after) for d in result.new_violations] == [("hold", -0.3)]
