"""JSON parsing and validation for LLM structured output."""

from __future__ import annotations

import json
from typing import Any


def parse_json_response(text: str) -> tuple[dict[str, Any] | None, str | None]:
    """Attempt to parse JSON from an LLM response.

    Handles common issues like markdown-wrapped JSON blocks.
    Returns (parsed_data, error_message).
    """
    cleaned = text.strip()

    # Strip markdown code fences if present
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = [line for line in lines if not line.strip().startswith("```")]
        cleaned = "\n".join(lines).strip()

    try:
        data = json.loads(cleaned)
        return data, None
    except json.JSONDecodeError as e:
        return None, f"JSON parse error: {e}"
