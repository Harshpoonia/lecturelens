"""
utils/text_cleaning.py

Pure text-processing helpers for transcripts and AI output.
"""

from __future__ import annotations

import html
import re

_NOISE_TAGS = re.compile(r"\[(?:music|applause|laughter|laughs|inaudible|silence|noise|cheering)[^\]]*\]", re.I)
_WHITESPACE = re.compile(r"\s+")


def clean_transcript_text(raw_text: str) -> str:
    """
    Normalize whitespace and remove filler artifacts commonly found in
    auto-generated YouTube transcripts ([Music], [Applause], ...).

    Only known noise tags are removed, so real bracketed content such as
    "[x]" in a maths lecture survives.
    """
    text = html.unescape(raw_text or "")
    text = _NOISE_TAGS.sub(" ", text)
    text = text.replace(">>", " ")
    text = _WHITESPACE.sub(" ", text)
    return text.strip()


def truncate_text(text: str, max_chars: int) -> str:
    """Truncate text to a maximum character length, on a word boundary."""
    if max_chars <= 0 or len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    last_space = truncated.rfind(" ")
    if last_space > 0:
        truncated = truncated[:last_space]
    return truncated.strip()


def strip_markdown(text: str) -> str:
    """Convert Markdown to plain text suitable for text-to-speech."""
    text = re.sub(r"```.*?```", " ", text or "", flags=re.S)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"^\s{0,3}#{1,6}\s*", "", text, flags=re.M)
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.M)
    text = re.sub(r"^\s*\d+[.)]\s+", "", text, flags=re.M)
    text = re.sub(r"(\*\*|__|\*|_|~~)(.+?)\1", r"\2", text)
    text = re.sub(r"\[(\d{1,2}:)?\d{1,2}:\d{2}\]", " ", text)
    text = re.sub(r"\n{2,}", ". ", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\.\s*\.", ".", text)
    return text.strip()
