from __future__ import annotations

import os
from typing import Any, Dict

import anthropic

from src.json_utils import extract_json_object


def get_client() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set.")
    return anthropic.Anthropic(api_key=api_key)


def default_model() -> str:
    return os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")


def complete_json(
    system: str,
    user: str,
    max_tokens: int = 8192,
) -> Dict[str, Any]:
    client = get_client()
    msg = client.messages.create(
        model=default_model(),
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    parts: list[str] = []
    for block in msg.content:
        if block.type == "text":
            parts.append(block.text)
    return extract_json_object("\n".join(parts))
