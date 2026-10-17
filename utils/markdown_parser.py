"""
utils/markdown_parser.py

Parses Gemini's Markdown learning-content output into sections.

Splits only on top-level ("# ") headings, so nested headings inside
Study Notes (##, ###) stay part of that section. Heading matching is
forgiving: "# 1. Key Points:", "# **Key Points**" and "# key points"
all map to "Key Points".
"""

from __future__ import annotations

import re

from models.learning_content import Chapter, LearningContent
from utils.time_utils import parse_timestamp

_TOP_LEVEL_HEADING = re.compile(r"^#\s+(.+?)\s*#*\s*$", re.MULTILINE)
_CHAPTER_LINE = re.compile(r"^\s*[-*]?\s*\[?((?:\d{1,2}:)?\d{1,2}:\d{2})\]?\s*[-–—:]?\s*(.+?)\s*$")

REQUIRED_SECTIONS = ("Executive Summary", "Key Points", "Study Notes", "Important Concepts")
OPTIONAL_SECTIONS = ("Video Chapters",)


def _normalize(title: str) -> str:
    title = re.sub(r"[*_`]", "", title)
    title = re.sub(r"^[^\w]*(\d+[.)]\s*)?", "", title)  # leading emoji / numbering
    return title.rstrip(":").strip().casefold()


_CANONICAL = {_normalize(name): name for name in (*REQUIRED_SECTIONS, *OPTIONAL_SECTIONS)}
_CANONICAL.update({"chapters": "Video Chapters", "timeline": "Video Chapters", "key concepts": "Important Concepts"})


def parse_learning_markdown(markdown_text: str) -> LearningContent:
    """Parse raw Markdown into LearningContent; raise ValueError if sections are missing."""
    sections = _split_top_level_sections(markdown_text or "")

    missing = [name for name in REQUIRED_SECTIONS if name not in sections]
    if missing:
        raise ValueError(
            f"Learning content is missing expected section(s): {', '.join(missing)}. "
            f"Found sections: {list(sections.keys()) or 'none'}"
        )

    return LearningContent(
        executive_summary=sections["Executive Summary"].strip(),
        key_points=sections["Key Points"].strip(),
        study_notes=sections["Study Notes"].strip(),
        important_concepts=sections["Important Concepts"].strip(),
        chapters=parse_chapters(sections.get("Video Chapters", "")),
    )


def parse_chapters(section_text: str) -> list[Chapter]:
    chapters: list[Chapter] = []
    for line in section_text.splitlines():
        match = _CHAPTER_LINE.match(line)
        if not match:
            continue
        seconds = parse_timestamp(match.group(1))
        title = re.sub(r"[*_`]", "", match.group(2)).strip()
        if seconds is not None and title:
            chapters.append(Chapter(seconds=seconds, title=title))
    chapters.sort(key=lambda chapter: chapter.seconds)
    return chapters


def _split_top_level_sections(markdown_text: str) -> dict[str, str]:
    matches = list(_TOP_LEVEL_HEADING.finditer(markdown_text))
    sections: dict[str, str] = {}
    for i, match in enumerate(matches):
        raw_title = match.group(1).strip()
        title = _CANONICAL.get(_normalize(raw_title), raw_title)
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(markdown_text)
        sections[title] = markdown_text[start:end]
    return sections
