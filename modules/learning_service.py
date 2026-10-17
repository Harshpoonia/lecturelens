"""
modules/learning_service.py

Generates Executive Summary, Key Points, Study Notes, Important Concepts
and (when timing data exists) Video Chapters from a transcript.
"""

from __future__ import annotations

from config import settings
from models.learning_content import LearningContent
from models.transcript import TranscriptData
from modules.ai_service import AIService
from utils.markdown_parser import parse_learning_markdown
from utils.prompt_loader import language_instruction, load_prompt

_CHAPTERS_WITH_TIMESTAMPS = (
    "A bulleted list of 4-10 chapters covering the whole video, one per line, formatted exactly as "
    "`- [mm:ss] Chapter title`, using only timestamp markers that appear in the transcript."
)
_CHAPTERS_WITHOUT_TIMESTAMPS = "Write exactly: - No timestamps available."


class LearningService:
    def __init__(self, ai_service: AIService) -> None:
        self._ai = ai_service

    def generate_learning_content(
        self, transcript: TranscriptData, output_language: str = ""
    ) -> LearningContent:
        prompt = load_prompt(
            "learning_prompt.txt",
            transcript=transcript.timestamped_text(settings.max_transcript_chars),
            language_instruction=language_instruction(output_language),
            chapters_instruction=(
                _CHAPTERS_WITH_TIMESTAMPS if transcript.has_timestamps else _CHAPTERS_WITHOUT_TIMESTAMPS
            ),
        )
        raw_markdown = self._ai.generate(prompt)
        try:
            return parse_learning_markdown(raw_markdown)
        except ValueError:
            # One retry: models occasionally drift from the heading format.
            raw_markdown = self._ai.generate(
                prompt + "\n\nIMPORTANT: Use the exact top-level headings listed above."
            )
            return parse_learning_markdown(raw_markdown)
