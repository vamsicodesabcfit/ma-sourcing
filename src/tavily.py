from __future__ import annotations

import os
from typing import Any, List

import httpx


async def tavily_search(query: str, max_results: int = 5) -> List[dict[str, Any]]:
    key = os.environ.get("TAVILY_API_KEY")
    if not key:
        return []
    payload = {
        "api_key": key,
        "query": query,
        "search_depth": "basic",
        "include_answer": False,
        "max_results": max_results,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post("https://api.tavily.com/search", json=payload)
        r.raise_for_status()
        data = r.json()
    out: List[dict[str, Any]] = []
    for item in data.get("results") or []:
        out.append(
            {
                "title": item.get("title"),
                "url": item.get("url"),
                "content": item.get("content"),
            }
        )
    return out


def tavily_search_sync(query: str, max_results: int = 5) -> List[dict[str, Any]]:
    key = os.environ.get("TAVILY_API_KEY")
    if not key:
        return []
    payload = {
        "api_key": key,
        "query": query,
        "search_depth": "basic",
        "include_answer": False,
        "max_results": max_results,
    }
    with httpx.Client(timeout=30.0) as client:
        r = client.post("https://api.tavily.com/search", json=payload)
        r.raise_for_status()
        data = r.json()
    out: List[dict[str, Any]] = []
    for item in data.get("results") or []:
        out.append(
            {
                "title": item.get("title"),
                "url": item.get("url"),
                "content": item.get("content"),
            }
        )
    return out
