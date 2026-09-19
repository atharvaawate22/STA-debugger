"""Tests for the quantitative / structural rules and report-level analysis."""

from app.rules import (
    HOLD_RULES,
    SETUP_RULES,
    analyze_report,
    diagnose_path,
    list_rules,
    split_drive,
)
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


def stage(instance, cell, delay, fanout=None, cap=None):
    return ChainStage(instance=instance, cell=cell, delay=delay, time=0.0,
                      edge="rise", fanout=fanout, cap=cap)


def rule_ids(diagnosis):
    return [s.rule_id for s in diagnosis.suggestions]


# ---------- drive strength ----------

def test_split_drive_handles_both_naming_styles():
    assert split_drive("NAND2_X1") == ("NAND2_X", 1)
    assert split_drive("sky130_fd_sc_hd__maj3_2") == ("sky130_fd_sc_hd__maj3_", 2)
    assert split_drive("NAND2") == ("NAND2", None)
    assert split_drive("in") == ("in", None)


def test_bottleneck_suggests_a_concrete_next_size():
    chain = [stage("u1/Z", "BUF_X1", 0.1), stage("u2/ZN", "NAND2_X2", 0.9), stage("u3/Z", "INV_X1", 0.1)]
    fix = diagnose_path(make_path(logic_chain=chain)).suggestions[0]
    assert fix.rule_id == "slow-cell"
    assert "NAND2_X4" in fix.fix            # 2 -> 4, skipping sizes libraries don't have


def test_bottleneck_at_max_drive_suggests_splitting_load_instead():
    chain = [stage("u1/Z", "BUF_X1", 0.1), stage("u2/ZN", "NAND2_X8", 0.9), stage("u3/Z", "INV_X1", 0.1)]
    fix = diagnose_path(make_path(logic_chain=chain)).suggestions[0]
    assert "upsize" not in fix.fix.lower()
    assert "load" in fix.fix.lower() or "fanout" in fix.fix.lower()


def test_bottleneck_reason_quantifies_the_gap():
    chain = [stage("u1/Z", "BUF_X1", 0.1), stage("u2/ZN", "NAND2_X1", 0.9), stage("u3/Z", "INV_X1", 0.1)]
    reason = diagnose_path(make_path(slack=-0.45, logic_chain=chain)).suggestions[0].reason
    assert "0.45 ns" in reason and "50%" in reason      # 0.45 of a 0.9 ns stage


# ---------- serial chain / fanout ----------

def test_repeated_cell_run_detected_ignoring_drive_strength():
    chain = [stage("u1/Z", "NAND2_X1", 0.2), stage("u2/Z", "NAND2_X2", 0.2),
             stage("u3/Z", "NAND2_X1", 0.2), stage("u4/Z", "INV_X1", 0.1)]
    d = diagnose_path(make_path(logic_chain=chain))
    assert d.repeated_run == 3
    assert d.repeated_delay == 0.6


def test_ripple_carry_chain_gets_a_structural_fix(sky130_report):
    violated = analyze_report(STAParser(sky130_report).parse()).paths[1]
    assert violated.diagnosis.repeated_run == 5
    serial = next(s for s in violated.diagnosis.suggestions if s.rule_id == "serial-chain")
    assert "carry-lookahead" in serial.fix
    assert serial.priority == "high"


def test_short_repeated_run_is_not_flagged():
    chain = [stage(f"u{i}/Z", "INV_X1", 0.2) for i in range(3)]
    assert "serial-chain" not in rule_ids(diagnose_path(make_path(logic_chain=chain)))


def test_high_fanout_driver_flagged():
    chain = [stage("u1/Z", "BUF_X1", 0.3, fanout=12, cap=0.05), stage("u2/Z", "AND2_X1", 0.3)]
    d = diagnose_path(make_path(logic_chain=chain))
    fanout = next(s for s in d.suggestions if s.rule_id == "high-fanout")
    assert "u1/Z" in fanout.fix and "12" in fanout.fix


def test_fanout_rule_silent_without_fanout_data():
    chain = [stage("u1/Z", "BUF_X1", 0.3), stage("u2/Z", "AND2_X1", 0.3)]
    assert "high-fanout" not in rule_ids(diagnose_path(make_path(logic_chain=chain)))


# ---------- io constraints ----------

def io_path(external, slack):
    chain = [stage("u1/Z", "BUF_X1", 0.3), stage("resp", "out", 0.0)]
    return make_path(endpoint="resp", external_delay=external, slack=slack, logic_chain=chain)


def test_output_delay_larger_than_violation_is_a_medium_constraint_suggestion():
    d = diagnose_path(io_path(external=1.0, slack=-0.18))
    io = next(s for s in d.suggestions if s.rule_id == "io-constraint")
    assert io.priority == "medium"
    assert "0.18 ns" in io.reason


def test_output_delay_smaller_than_violation_is_low_priority():
    d = diagnose_path(io_path(external=0.1, slack=-0.5))
    io = next(s for s in d.suggestions if s.rule_id == "io-constraint")
    assert io.priority == "low"
    assert "would not close" in io.reason


# ---------- hold ----------

def test_hold_estimates_number_of_delay_cells():
    chain = [stage("b1/X", "BUF_X1", 0.05)]
    d = diagnose_path(make_path(path_type="min", slack=-0.12, logic_chain=chain))
    assert "3 delay cell" in d.suggestions[0].reason      # ceil(0.12 / 0.05)


def test_hold_setup_headroom_conflict(adder_before):
    result = analyze_report(STAParser(adder_before).parse())
    conflict = next(a for a in result.paths
                    if a.diagnosis.check_type == "hold" and a.path.endpoint == "st")
    headroom = next(s for s in conflict.diagnosis.suggestions if s.rule_id == "hold-setup-headroom")
    assert headroom.priority == "high"
    assert "cannot fix" in headroom.fix


def test_hold_setup_headroom_safe(adder_before):
    result = analyze_report(STAParser(adder_before).parse())
    safe = next(a for a in result.paths
                if a.diagnosis.check_type == "hold" and a.path.endpoint == "q0")
    headroom = next(s for s in safe.diagnosis.suggestions if s.rule_id == "hold-setup-headroom")
    assert "safe" in headroom.fix
    assert headroom.priority == "low"


# ---------- grouping ----------

def test_groups_find_shared_logic_across_bus(adder_before):
    result = analyze_report(STAParser(adder_before).parse())
    shared = next(g for g in result.groups if g.kind == "shared_logic" and g.key == "m1")
    assert shared.count == 3
    assert shared.check_type == "setup"
    assert shared.worst_slack == -0.83
    # All three sumreg violations are setup, so together they are the setup TNS.
    assert shared.tns == round(-0.11 - 0.47 - 0.83, 2)
    assert shared.tns_share == 1.0


def test_groups_indices_point_at_violations_of_the_same_check(adder_before):
    result = analyze_report(STAParser(adder_before).parse())
    assert result.groups
    for group in result.groups:
        for i in group.path_indices:
            assert result.paths[i].path.status == "VIOLATED"
            assert result.paths[i].diagnosis.check_type == group.check_type


def test_bus_group_when_paths_share_no_logic():
    def bus_path(n):
        return make_path(endpoint=f"q[{n}]", startpoint=f"r{n}",
                         logic_chain=[stage(f"own{n}/Z", "AND2_X1", 0.2)])
    result = analyze_report([bus_path(1), bus_path(2)])
    assert [g.kind for g in result.groups] == ["endpoint_bus"]
    assert result.groups[0].key == "q[*]"


def test_no_groups_for_single_violation(sky130_report):
    assert analyze_report(STAParser(sky130_report).parse()).groups == []


def test_skipped_blocks_reach_the_summary(sky130_report):
    assert analyze_report(STAParser(sky130_report).parse(), skipped_blocks=2).summary.skipped_blocks == 2


# ---------- registry ----------

def test_every_suggestion_carries_a_registered_rule_id(adder_before):
    known = set(SETUP_RULES) | set(HOLD_RULES) | {"distributed-delay", "hold-setup-headroom"}
    for a in analyze_report(STAParser(adder_before).parse()).paths:
        for s in a.diagnosis.suggestions:
            assert s.rule_id in known


def test_suggestions_are_ordered_by_priority(adder_before):
    order = {"high": 0, "medium": 1, "low": 2}
    for a in analyze_report(STAParser(adder_before).parse()).paths:
        ranks = [order[s.priority] for s in a.diagnosis.suggestions]
        assert ranks == sorted(ranks)


def test_fallback_when_no_rule_fires():
    chain = [stage(f"u{i}/Z", cell, 0.2) for i, cell in enumerate(["INV_X1", "AND2_X1", "OR2_X1"])]
    d = diagnose_path(make_path(slack=-0.1, logic_chain=chain))
    assert rule_ids(d) == ["distributed-delay"]
    assert "%" in d.suggestions[0].reason            # states the required speed-up


def test_list_rules_lists_both_checks():
    rules = list_rules()
    assert {"id": "slow-cell", "check": "setup"} in rules
    assert {"id": "hold-buffers", "check": "hold"} in rules
