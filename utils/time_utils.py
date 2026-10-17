"""
utils/time_utils.py

Helpers for working with video timestamps: formatting seconds as
[mm:ss], parsing them back, finding them in AI responses and turning
them into YouTube deep links.
"""

from __future__ import annotations

import re

# Matches [mm:ss] or [h:mm:ss] (brackets required, so plain ratios like
# "3:2" in prose are not mistaken for timestamps).
TIMESTAMP_PATTERN = re.compile(r"\[(?:(\d{1,2}):)?(\d{1,2}):(\d{2})\]")


def format_timestamp(seconds: float | int | None) -> str:
    """Format seconds as m:ss or h:mm:ss."""
    if seconds is None:
        return "--:--"
    total = max(int(seconds), 0)
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def parse_timestamp(text: str) -> int | None:
    """Parse '05:32', '1:02:03' or '[05:32]' into seconds."""
    cleaned = text.strip().strip("[]").strip()
    parts = cleaned.split(":")
    if not 2 <= len(parts) <= 3 or not all(p.isdigit() for p in parts):
        return None
    numbers = [int(p) for p in parts]
    if len(numbers) == 2:
        minutes, secs = numbers
        hours = 0
    else:
        hours, minutes, secs = numbers
    if secs >= 60 or (hours and minutes >= 60):
        return None
    return hours * 3600 + minutes * 60 + secs


def _match_to_seconds(match: re.Match[str]) -> int:
    hours = int(match.group(1) or 0)
    return hours * 3600 + int(match.group(2)) * 60 + int(match.group(3))


def find_timestamps(text: str, limit: int = 8) -> list[int]:
    """Return unique timestamps (in seconds) found in text, in order."""
    seen: list[int] = []
    for match in TIMESTAMP_PATTERN.finditer(text or ""):
        seconds = _match_to_seconds(match)
        if seconds not in seen:
            seen.append(seconds)
        if len(seen) >= limit:
            break
    return seen


def youtube_link(video_id: str, seconds: int | float = 0) -> str:
    return f"https://www.youtube.com/watch?v={video_id}&t={int(seconds)}s"


def linkify_timestamps(text: str, video_id: str | None, max_seconds: float | None = None) -> str:
    """Turn [mm:ss] markers into Markdown links that open the video at that time."""
    if not video_id or not text:
        return text

    def _replace(match: re.Match[str]) -> str:
        seconds = _match_to_seconds(match)
        if max_seconds is not None and seconds > max_seconds + 5:
            return match.group(0)
        label = match.group(0)
        return f"[{label[1:-1]}]({youtube_link(video_id, seconds)})"

    return TIMESTAMP_PATTERN.sub(_replace, text)
