"""
models/quiz.py

Quiz questions and per-question answer records.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class QuizQuestion:
    question: str
    options: list[str]
    correct_answer: str
    explanation: str
    difficulty: str | None = None
    timestamp_seconds: int | None = None

    def is_correct(self, selected_option: str | None) -> bool:
        if selected_option is None:
            return False
        return selected_option.strip() == self.correct_answer.strip()


@dataclass
class QuizAnswer:
    question_index: int
    selected_option: str
    is_correct: bool
