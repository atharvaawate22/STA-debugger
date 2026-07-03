"""Optional natural-language explanations via Groq's chat API.

This is deliberately a thin, optional layer: the diagnosis itself comes from
the rule engine, and the LLM only rewrites it as prose for the report.
Called directly over HTTP — no SDK needed for a single endpoint.
"""

import json

import requests

from .config import GROQ_MODEL
from .schemas import AnalyzedPath

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

_SYSTEM_PROMPT = (
    "You are a senior STA (static timing analysis) engineer reviewing a timing "
    "path. You are given the parsed path and a rule-based diagnosis. Explain to "
    "a junior engineer, in 2-3 short paragraphs of plain prose, why this path "
    "violates timing and how the suggested fixes address it. Do not invent "
    "numbers that are not in the data. No markdown headings or bullet lists."
)


class ExplanationError(Exception):
    pass


def explain_path(analyzed: AnalyzedPath, api_key: str) -> str:
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
        return response.json()["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, ValueError) as exc:
        raise ExplanationError("Unexpected response format from Groq.") from exc
