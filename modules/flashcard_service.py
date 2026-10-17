"""
modules/flashcard_service.py

Generates a flashcard deck from a transcript. Independent of QuizService:
own prompt, own parser, own model.
"""

from __future__ import annotations

from config import settings
from models.flashcard import Flashcard
from models.transcript import TranscriptData
from modules.ai_service import AIService
from utils.flashcard_parser import parse_flashcard_json
from utils.prompt_loader import language_instruction, load_prompt


class FlashcardService:
    def __init__(self, ai_service: AIService) -> None:
        self._ai = ai_service

    def generate_flashcards(
        self, transcript: TranscriptData, num_cards: int = 10, output_language: str = ""
    ) -> list[Flashcard]:
        prompt = load_prompt(
            "flashcard_prompt.txt",
            transcript=transcript.timestamped_text(settings.max_transcript_chars),
            num_cards=num_cards,
            language_instruction=language_instruction(output_language),
        )
        try:
            cards = parse_flashcard_json(self._ai.generate(prompt, json_mode=True))
        except ValueError:
            cards = parse_flashcard_json(self._ai.generate(prompt, json_mode=True))
        return cards[:num_cards]
