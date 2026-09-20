import pytest
import requests

from app import llm
from app.llm import ExplanationError, explain_path, find_unsupported_numbers
from app.rules import analyze_report
from app.sta_parser import STAParser


class FakeResponse:
    def __init__(self, status_code=200, body=None):
        self.status_code = status_code
        self._body = body
        self.ok = 200 <= status_code < 300

    def json(self):
        if isinstance(self._body, Exception):
            raise self._body
        return self._body


def completion(text):
    return {"choices": [{"message": {"content": text}}]}


@pytest.fixture
def violated(sky130_report):
    result = analyze_report(STAParser(sky130_report).parse())
    return next(a for a in result.paths if a.path.status == "VIOLATED")


def mock_post(monkeypatch, response=None, error=None):
    calls = []

    def fake_post(url, json=None, headers=None, timeout=None):
        calls.append({"url": url, "json": json, "headers": headers})
        if error:
            raise error
        return response

    monkeypatch.setattr(llm.requests, "post", fake_post)
    return calls


# ---------- the HTTP call ----------

def test_successful_explanation(monkeypatch, violated):
    calls = mock_post(monkeypatch, FakeResponse(body=completion("  The path misses by 0.18 ns.  ")))
    result = explain_path(violated, "secret-key")

    assert result.explanation == "The path misses by 0.18 ns."
    assert calls[0]["headers"]["Authorization"] == "Bearer secret-key"
    # The model is given the rule engine's diagnosis, not just the raw path.
    assert "suggestions" in calls[0]["json"]["messages"][1]["content"]


def test_rejected_key(monkeypatch, violated):
    mock_post(monkeypatch, FakeResponse(status_code=401, body={}))
    with pytest.raises(ExplanationError, match="rejected"):
        explain_path(violated, "bad")


def test_server_error(monkeypatch, violated):
    mock_post(monkeypatch, FakeResponse(status_code=503, body={}))
    with pytest.raises(ExplanationError, match="503"):
        explain_path(violated, "k")


def test_network_failure(monkeypatch, violated):
    mock_post(monkeypatch, error=requests.ConnectionError("no route"))
    with pytest.raises(ExplanationError, match="Could not reach"):
        explain_path(violated, "k")


@pytest.mark.parametrize("body", [
    {"unexpected": "shape"},
    {"choices": []},
    {"choices": [{"message": {"content": None}}]},
    ValueError("not json"),
])
def test_malformed_response(monkeypatch, violated, body):
    mock_post(monkeypatch, FakeResponse(body=body))
    with pytest.raises(ExplanationError, match="Unexpected response"):
        explain_path(violated, "k")


def test_empty_explanation(monkeypatch, violated):
    mock_post(monkeypatch, FakeResponse(body=completion("   ")))
    with pytest.raises(ExplanationError, match="empty"):
        explain_path(violated, "k")


# ---------- number checking ----------

def test_numbers_from_the_data_are_supported(violated):
    # 1.78 of 3.38 ns is 53%, quoted here as a percentage the data never states directly.
    text = ("The path violates by 0.18 ns, and the 5 stage maj3 chain adds 1.78 ns, "
            "53% of the logic delay across 13 stages.")
    assert find_unsupported_numbers(text, violated) == []


def test_invented_numbers_are_reported(violated):
    text = "The slack is -0.18 ns, but the clock period should be 3.7 ns and there are 42 stages."
    assert find_unsupported_numbers(text, violated) == ["3.7", "42"]


def test_percentages_match_fractions_in_the_data(violated):
    share = round(violated.diagnosis.bottleneck_share * 100)
    assert find_unsupported_numbers(f"one cell is {share}% of the delay", violated) == []
    assert find_unsupported_numbers(f"one cell is {share + 20}% of the delay", violated) == [f"{share + 20}%"]


def test_percentages_spelled_out_are_treated_as_percentages(violated):
    share = round(violated.diagnosis.bottleneck_share * 100)
    # "35 percent" means the same as "35%" and must not be flagged over the wording.
    assert find_unsupported_numbers(f"one cell is {share} percent of the delay", violated) == []
    assert find_unsupported_numbers(f"one cell is {share} per cent of the delay", violated) == []
    assert find_unsupported_numbers(f"one cell is {share + 20} percent of the delay", violated) == [
        f"{share + 20}%"
    ]


def test_sign_is_ignored_and_duplicates_reported_once(violated):
    assert find_unsupported_numbers("miss of -0.18 ns", violated) == []
    assert find_unsupported_numbers("about 99.9 or 99.9 ns", violated) == ["99.9"]


def test_explain_response_carries_unverified_numbers(monkeypatch, violated):
    mock_post(monkeypatch, FakeResponse(body=completion("It fails by 0.18 ns at 777 MHz.")))
    result = explain_path(violated, "k")
    assert result.unverified_numbers == ["777"]
