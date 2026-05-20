"""Groq OpenAI-compatible chat completions with JSON extraction."""

from __future__ import annotations

import os
from typing import Any, Dict

from groq import Groq

from src.json_utils import extract_json_object


def get_groq_client() -> Groq:
    key = os.environ.get("MA_GROQ_KEY") or os.environ.get("GROQ_API_KEY")
    if not key or not str(key).strip():
        raise RuntimeError(
            "Groq API key is not set. Set environment variable MA_GROQ_KEY or GROQ_API_KEY "
            "where Streamlit is launched."
        )
    return Groq(api_key=key.strip())


def default_groq_model() -> str:
    return os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")


def complete_json_groq(
    system: str,
    user: str,
    max_tokens: int = 8192,
) -> Dict[str, Any]:
    """Call Groq chat completions and parse the first JSON object from the reply."""
    client = get_groq_client()
    model = default_groq_model()
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": 0.15,
        "max_tokens": max_tokens,
    }
    try:
        completion = client.chat.completions.create(
            **kwargs,
            response_format={"type": "json_object"},
        )
    except Exception:
        completion = client.chat.completions.create(**kwargs)
    text = (completion.choices[0].message.content or "").strip() or "{}"
    return extract_json_object(text)
