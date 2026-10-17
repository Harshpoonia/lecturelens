"""
modules/quiz_service.py

Generates an interactive multiple-choice quiz from a transcript.
"""

from __future__ import annotations

import random

from config import settings
from models.quiz import QuizQuestion
from models.transcript import TranscriptData
from modules.ai_service import AIService
from utils.prompt_loader import language_instruction, load_prompt
from utils.quiz_parser import parse_quiz_json

DIFFICULTY_LEVELS = ("Mixed", "Easy", "Medium", "Hard")

_DIFFICULTY_TEXT = {
    "Mixed": "a mix — roughly one third Easy, one third Medium, one third Hard",
    "Easy": "Easy — recall of the main facts and definitions",
    "Medium": "Medium — understanding and applying the ideas",
    "Hard": "Hard — analysis, edge cases and connecting several ideas",
}


class QuizService:
    def __init__(self, ai_service: AIService, rng: random.Random | None = None) -> None:
        self._ai = ai_service
        self._rng = rng or random.Random()

    def generate_quiz(
        self,
        transcript: TranscriptData,
        num_questions: int = 5,
        difficulty: str = "Mixed",
        output_language: str = "",
    ) -> list[QuizQuestion]:
        prompt = load_prompt(
            "quiz_prompt.txt",
            transcript=transcript.timestamped_text(settings.max_transcript_chars),
            num_questions=num_questions,
            difficulty=_DIFFICULTY_TEXT.get(difficulty, _DIFFICULTY_TEXT["Mixed"]),
            language_instruction=language_instruction(output_language),
        )
        try:
            questions = parse_quiz_json(self._ai.generate(prompt, json_mode=True))
        except ValueError:
            questions = parse_quiz_json(self._ai.generate(prompt, json_mode=True))

        # LLMs tend to place the right answer in the same slot; shuffle options.
        for question in questions:
            self._rng.shuffle(question.options)
        return questions[:num_questions]
