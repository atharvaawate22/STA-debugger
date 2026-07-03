from app.rules import analyze_report, diagnose_path
from app.schemas import ChainStage, TimingPath
from app.sta_parser import STAParser


def make_path(**overrides) -> TimingPath:
    defaults = dict(
        startpoint="r1",
        endpoint="r2",
        path_group="clk",
        path_type="max",
        capture_edge=10.0,
        slack=-0.5,
        status="VIOLATED",
        logic_chain=[],
    )
    defaults.update(overrides)
    return TimingPath(**defaults)


def stage(instance, cell, delay):
    return ChainStage(instance=instance, cell=cell, delay=delay, time=0.0, edge="rise")


def test_setup_vs_hold_classification():
    assert diagnose_path(make_path(path_type="max")).check_type == "setup"
    assert diagnose_path(make_path(path_type="min")).check_type == "hold"


def test_met_path_gets_no_severity_or_suggestions():
    diagnosis = diagnose_path(make_path(slack=1.2, status="MET"))
    assert diagnosis.severity is None
    assert diagnosis.suggestions == []


def test_severity_relative_to_clock_period():
    # 2.5ns violation on a 10ns clock = 25% of the period -> critical
    assert diagnose_path(make_path(slack=-2.5)).severity == "critical"
    # 1.5ns on 10ns -> high
    assert diagnose_path(make_path(slack=-1.5)).severity == "high"
    # 0.5ns on 10ns -> medium
    assert diagnose_path(make_path(slack=-0.5)).severity == "medium"
    # 0.1ns on 10ns -> low
    assert diagnose_path(make_path(slack=-0.1)).severity == "low"


def test_severity_falls_back_to_absolute_slack():
    diagnosis = diagnose_path(make_path(slack=-1.5, capture_edge=None))
    assert diagnosis.severity == "critical"


def test_bottleneck_detection():
    chain = [
        stage("r1/CK", "DFF_X1", 0.0),
        stage("r1/Q", "DFF_X1", 0.2),
        stage("u1/Z", "BUF_X1", 0.1),
        stage("u2/ZN", "NAND2_X1", 0.9),  # dominant stage
        stage("u3/Z", "INV_X1", 0.1),
        stage("r2/D", "DFF_X1", 0.0),
    ]
    diagnosis = diagnose_path(make_path(logic_chain=chain))

    assert diagnosis.bottleneck_instance == "u2/ZN"
    assert diagnosis.bottleneck_share > 0.35
    # Rule should fire: first suggestion targets the slow cell.
    assert "u2/ZN" in diagnosis.suggestions[0].fix
    assert diagnosis.suggestions[0].priority == "high"


def test_logic_depth_excludes_clock_pins_and_endpoints():
    chain = [
        stage("r1/CK", "DFF_X1", 0.0),   # clock pin: excluded
        stage("r1/Q", "DFF_X1", 0.2),    # startpoint flop: excluded
        stage("u1/Z", "BUF_X1", 0.1),
        stage("u2/ZN", "NAND2_X1", 0.2),
        stage("r2/D", "DFF_X1", 0.0),    # endpoint flop: excluded
    ]
    diagnosis = diagnose_path(make_path(logic_chain=chain))
    assert diagnosis.logic_depth == 2


def test_deep_path_suggests_pipelining():
    chain = [stage(f"u{i}/Z", "INV_X1", 0.2) for i in range(9)]
    diagnosis = diagnose_path(make_path(logic_chain=chain))
    fixes = " ".join(s.fix.lower() for s in diagnosis.suggestions)
    assert "pipeline" in fixes


def test_hold_violation_suggests_delay_buffers():
    diagnosis = diagnose_path(make_path(path_type="min", slack=-0.05))
    assert diagnosis.suggestions[0].priority == "high"
    assert "buffer" in diagnosis.suggestions[0].fix.lower()


def test_hold_with_positive_skew_flags_clock_tree():
    diagnosis = diagnose_path(make_path(
        path_type="min",
        slack=-0.05,
        launch_clock_latency=0.10,
        capture_clock_latency=0.40,
    ))
    assert diagnosis.clock_skew == 0.30
    fixes = " ".join(s.fix.lower() for s in diagnosis.suggestions)
    assert "skew" in fixes or "clock" in fixes


def test_report_summary_from_real_report(deep_paths_report):
    paths = STAParser(deep_paths_report).parse()
    result = analyze_report(paths)

    assert result.summary.total_paths == 2
    assert result.summary.violated_paths == 0
    assert result.summary.wns is None
    assert result.summary.tns == 0.0


def test_report_summary_with_violation(sky130_report):
    paths = STAParser(sky130_report).parse()
    result = analyze_report(paths)

    assert result.summary.violated_paths == 1
    assert result.summary.wns == -0.18
    assert result.summary.tns == -0.18
    assert result.summary.setup_violations == 1
    assert result.summary.hold_violations == 0

    violated = next(p for p in result.paths if p.path.status == "VIOLATED")
    # 13 combinational stages -> the pipelining rule should fire.
    assert violated.diagnosis.logic_depth >= 8
    fixes = " ".join(s.fix.lower() for s in violated.diagnosis.suggestions)
    assert "pipeline" in fixes
    # Endpoint is an output port -> the constraints rule should fire too.
    assert "external delay" in fixes
