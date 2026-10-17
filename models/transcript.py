"""
models/transcript.py

Data model for a fetched (or pasted / AI-transcribed) transcript.
Structure plus small derived properties only — no I/O.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from utils.text_statistics import reading_time, speaking_pace
from utils.time_utils import format_timestamp

SOURCE_LABELS = {
    "youtube_manual": "Creator captions",
    "youtube_generated": "Auto-generated captions",
    "gemini": "Transcribed by Gemini",
    "manual": "Pasted by you",
}


@dataclass(frozen=True)
class TranscriptSegment:
    text: str
    start: float
    duration: float = 0.0


@dataclass
class TranscriptData:
    """A cleaned transcript for a single video."""

    video_id: str
    video_url: str
    raw_text: str
    cleaned_text: str
    language: str
    language_code: str = ""
    source: str = "youtube_generated"
    segments: list[TranscriptSegment] = field(default_factory=list)
    duration_seconds: float | None = None
    title: str | None = None
    channel: str | None = None

    @property
    def char_count(self) -> int:
        return len(self.cleaned_text)

    @property
    def word_count(self) -> int:
        return len(self.cleaned_text.split())

    @property
    def reading_time_minutes(self) -> int:
        return reading_time(self.cleaned_text)

    @property
    def speaking_wpm(self) -> int | None:
        return speaking_pace(self.word_count, self.duration_seconds)

    @property
    def has_timestamps(self) -> bool:
        return bool(self.segments)

    @property
    def is_youtube(self) -> bool:
        return bool(self.video_id) and not self.video_id.startswith("pasted-")

    @property
    def source_label(self) -> str:
        return SOURCE_LABELS.get(self.source, self.source)

    @property
    def content_hash(self) -> str:
        """Stable key for caching AI output derived from this transcript."""
        return hashlib.sha256(self.cleaned_text.encode("utf-8")).hexdigest()[:16]

    @property
    def display_title(self) -> str:
        if self.title:
            return self.title
        return "Pasted transcript" if not self.is_youtube else f"Video {self.video_id}"

    def timestamped_text(self, max_chars: int = 0, block_seconds: int = 30) -> str:
        """
        Transcript text with a [mm:ss] marker roughly every `block_seconds`.

        Used as model input so generated notes, chapters, quiz questions
        and chat answers can cite exact moments of the video. Falls back
        to plain cleaned text when no timing data exists.
        """
        if not self.segments:
            text = self.cleaned_text
        else:
            parts: list[str] = []
            next_marker = 0.0
            for segment in self.segments:
                if segment.start >= next_marker:
                    parts.append(f"\n[{format_timestamp(segment.start)}]")
                    next_marker = segment.start + block_seconds
                parts.append(segment.text.strip())
            text = " ".join(parts).strip()

        if max_chars and len(text) > max_chars:
            cut = text[:max_chars]
            text = cut[: cut.rfind(" ")] if " " in cut else cut
        return text
