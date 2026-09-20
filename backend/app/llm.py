"""Optional natural-language explanations via Groq's chat API.

This is deliberately a thin, optional layer: the diagnosis itself comes from
the rule engine, and the LLM only rewrites it as prose for the report.
Called directly over HTTP — no SDK needed for a single endpoint.

Models sometimes invent numbers, so every number in the explanation is checked
against the diagnosis it was given; anything that can't be traced back is
returned alongside the text so the UI can warn about it.
"""

import json
import re
from typing import List, Set

import requests

from .config import GROQ_MODEL
from .schemas import AnalyzedPath, ExplainResponse

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

_SYSTEM_PROMPT = (
    "You are a senior STA (static timing analysis) engineer reviewing a timing "
    "path. You are given the parsed path and a rule-based diagnosis. Explain to "
    "a junior engineer, in 2-3 short paragraphs of plain prose, why this path "
    "violates timing and how the suggested fixes address it. Explain only the "
    "listed suggestions; do not propose other fixes. Do not invent numbers that "
    "are not in the data. No markdown headings or bullet lists."
)

# A number, optionally followed by a percent sign.
_NUMBER = re.compile(r"(\d+(?:\.\d+)?)(\s*%)?")

# Rounding slack when comparing a quoted number to the data (report values are
# printed to two decimals; percentages are rounded to whole numbers).
_ABS_TOLERANCE = 0.006
_PERCENT_TOLERANCE = 0.5


class ExplanationError(Exception):
    pass


def _numbers_in(value, found: Set[float]) -> None:
    """Collect every number in a nested structure, including digits inside
    strings such as cell names and the rule engine's own reason text."""
    if isinstance(value, bool) or value is None:
        return
    if isinstance(value, (int, float)):
        found.add(abs(float(value)))
    elif isinstance(value, str):
        found.update(float(match.group(1)) for match in _NUMBER.finditer(value))
    elif isinstance(value, dict):
        for item in value.values():
            _numbers_in(item, found)
    elif isinstance(value, list):
        for item in value:
            _numbers_in(item, found)


def _fractions(analyzed: AnalyzedPath) -> Set[float]:
    """Genuine fractions in the diagnosis, which the text may quote as percentages."""
    d, p = analyzed.diagnosis, analyzed.path
    fractions = {d.bottleneck_share, d.required_speedup}
    if d.repeated_delay and d.total_logic_delay:
        fractions.add(d.repeated_delay / d.total_logic_delay)
    if p.external_delay and p.capture_edge:
        fractions.add(p.external_delay / p.capture_edge)
    return {f for f in fractions if f is not None}


def find_unsupported_numbers(explanation: str, analyzed: AnalyzedPath) -> List[str]:
    """Numbers quoted in `explanation` that don't appear in the diagnosis.

    A plain number must match a data value (ignoring sign). A number written
    with a percent sign may instead match a fraction in the data: "0.35" in the
    diagnosis, "35%" in the text.
    """
    values: Set[float] = set()
    _numbers_in(analyzed.model_dump(), values)
    percents = {f * 100 for f in _fractions(analyzed)}

    unsupported = []
    for match in _NUMBER.finditer(explanation):
        token, is_percent = match.group(1), bool(match.group(2))
        number = float(token)
        supported = any(abs(number - v) <= _ABS_TOLERANCE for v in values)
        if is_percent and not supported:
            supported = any(abs(number - v) <= _PERCENT_TOLERANCE for v in percents)
        label = token + "%" if is_percent else token
        if not supported and label not in unsupported:
            unsupported.append(label)
    return unsupported


def explain_path(analyzed: AnalyzedPath, api_key: str) -> ExplainResponse:
    payload = {
        "model": GROQ_MODEL,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(analyzed.model_dump(), indent=2)},
        ],
    }
    try:
        response = requests.post(
            GROQ_URL,
            json=payload,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30,
        )
    except requests.RequestException as exc:
        raise ExplanationError(f"Could not reach Groq: {exc}") from exc

    if response.status_code == 401:
        raise ExplanationError("The Groq API key was rejected.")
    if not response.ok:
        raise ExplanationError(f"Groq returned an error (HTTP {response.status_code}).")

    try:
        text = response.json()["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, ValueError, AttributeError) as exc:
        raise ExplanationError("Unexpected response format from Groq.") from exc
    if not text:
        raise ExplanationError("Groq returned an empty explanation.")

    return ExplainResponse(
        explanation=text,
        unverified_numbers=find_unsupported_numbers(text, analyzed),
    )
