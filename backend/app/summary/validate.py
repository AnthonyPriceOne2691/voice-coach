"""Summary JSON validation — summary.contract.yaml hard rules as code."""

import json
import re
from typing import Any

SCORE_KEYS = ("clarity", "structure", "technical_depth", "english_fluency", "positioning")


class SummaryInvalidError(ValueError):
    """LLM output failed the summary contract; message is the retry hint."""


def extract_json(raw: str) -> dict[str, Any]:
    """Parse the first {...} block (models love to wrap JSON in prose/fences)."""
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end <= start:
        raise SummaryInvalidError("no JSON object found in output")
    try:
        data = json.loads(raw[start : end + 1])
    except json.JSONDecodeError as exc:
        raise SummaryInvalidError(f"invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise SummaryInvalidError("top-level JSON value must be an object")
    return data


def validate_summary(data: dict[str, Any], *, require_vocabulary: bool) -> dict[str, Any]:
    scores = data.get("scores")
    if not isinstance(scores, dict):
        raise SummaryInvalidError("missing scores object")
    for key in SCORE_KEYS:
        value = scores.get(key)
        if not isinstance(value, int) or not 1 <= value <= 5:  # S-H3
            raise SummaryInvalidError(f"scores.{key} must be an integer 1-5, got {value!r}")

    vocabulary = data.get("vocabulary", [])
    if not isinstance(vocabulary, list):
        raise SummaryInvalidError("vocabulary must be a list")
    complete = [
        item
        for item in vocabulary
        if isinstance(item, dict)
        and str(item.get("term_en", "")).strip()
        and str(item.get("translation_ru", "")).strip()  # S-H4 (FR-6.3)
        and str(item.get("example_en", "")).strip()
    ]
    if require_vocabulary and not complete:
        raise SummaryInvalidError(
            "vocabulary must contain items with term_en/translation_ru/example_en"
        )
    data["vocabulary"] = complete

    for field in ("overall_summary",):
        if re.search(r"[Ѐ-ӿ]", str(data.get(field, ""))):  # S-H2: EN body fields
            raise SummaryInvalidError(f"{field} must be English")
    return data
