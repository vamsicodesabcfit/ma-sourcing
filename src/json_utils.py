"""Extract JSON objects from LLM or Cursor chat output."""

from __future__ import annotations

import json
import re
from typing import Any


def extract_json_object(text: str) -> dict[str, Any]:
    """Parse first JSON object from model or pasted chat output."""
    text = text.strip()
    m = re.search(r"\{[\s\S]*\}\s*$", text)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, re.I)
    if fence:
        try:
            return json.loads(fence.group(1).strip())
        except json.JSONDecodeError:
            pass
    return json.loads(text)


def extract_json_array(text: str) -> list[Any]:
    """Parse first JSON array from pasted text."""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, re.I)
    if fence:
        try:
            parsed = json.loads(fence.group(1).strip())
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass
    m = re.search(r"\[[\s\S]*\]\s*$", text)
    if m:
        parsed = json.loads(m.group(0))
        if isinstance(parsed, list):
            return parsed
    parsed = json.loads(text)
    if not isinstance(parsed, list):
        raise ValueError("Expected JSON array")
    return parsed
