from pathlib import Path

import pytest

SAMPLE_DIR = Path(__file__).resolve().parent.parent.parent / "sample_reports"


@pytest.fixture
def basic_report() -> str:
    return (SAMPLE_DIR / "basic_min_max.txt").read_text()


@pytest.fixture
def sky130_report() -> str:
    return (SAMPLE_DIR / "sky130_with_violation.txt").read_text()


@pytest.fixture
def deep_paths_report() -> str:
    return (SAMPLE_DIR / "sky130_deep_paths.txt").read_text()


@pytest.fixture
def single_setup_report() -> str:
    return (SAMPLE_DIR / "single_setup_path.txt").read_text()


@pytest.fixture
def adder_before() -> str:
    return (SAMPLE_DIR / "adder_before.txt").read_text()


@pytest.fixture
def adder_after() -> str:
    return (SAMPLE_DIR / "adder_after.txt").read_text()
