"""
utils/prompt_loader.py

Single place that reads prompt templates from prompts/.

Prompt engineering always lives in prompts/*.txt (and prompts/*.json for
small lookup tables), never inside service or UI code.
"""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path
from typing import Any

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


@cache
def _read_prompt_file(filename: str) -> str:
    path = PROMPTS_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return path.read_text(encoding="utf-8")


def load_prompt(filename: str, **kwargs: Any) -> str:
    """
    Load a prompt template and fill its {placeholders}.

    Example:
        load_prompt("quiz_prompt.txt", transcript=text, num_questions=5)
    """
    template = _read_prompt_file(filename)
    try:
        return template.format(**{k: str(v) for k, v in kwargs.items()})
    except KeyError as exc:
        raise ValueError(f"Missing placeholder value for prompt '{filename}': {exc}") from exc


@cache
def load_prompt_json(filename: str) -> Any:
    """Load a JSON lookup table stored alongside the prompts."""
    return json.loads(_read_prompt_file(filename))


def language_instruction(output_language: str) -> str:
    """Sentence telling the model which language to write in."""
    if not output_language or output_language.lower().startswith("same"):
        return "Write your entire response in the same language as the transcript."
    return f"Write your entire response in {output_language}, even if the transcript is in another language."
