"""
models/flashcard.py

Flashcards. Kept separate from quiz models: flashcards have their own pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Flashcard:
    front: str
    back: str
    topic: str = "General"
    difficulty: str | None = None
