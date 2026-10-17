"""
utils/json_utils.py

Tolerant JSON extraction for LLM output. Even with JSON mode enabled,
models occasionally wrap output in code fences, add a sentence before
the array, or return {"items": [...]} instead of a bare list.
"""

from __future__ import annotations

import json
import re
from typing import Any

_FENCE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.I)


def extract_json(raw: str) -> Any:
    """Parse JSON from raw model output, tolerating common wrappers."""
    if raw is None:
        raise ValueError("No response text to parse.")
    text = _FENCE.sub("", raw.strip()).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Fall back to the outermost array or object in the text.
    for opener, closer in (("[", "]"), ("{", "}")):
        start, end = text.find(opener), text.rfind(closer)
        if start != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                continue
    raise ValueError("Response is not valid JSON.")


def extract_json_list(raw: str, preferred_keys: tuple[str, ...] = ()) -> list[Any]:
    """Return a JSON list, unwrapping {"questions": [...]}-style objects."""
    data = extract_json(raw)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in preferred_keys:
            if isinstance(data.get(key), list):
                return data[key]
        lists = [value for value in data.values() if isinstance(value, list)]
        if len(lists) == 1:
            return lists[0]
    raise ValueError("Expected a JSON list in the model response.")
