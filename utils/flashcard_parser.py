"""
utils/flashcard_parser.py

Parses Gemini's JSON flashcard output into Flashcard objects.
Kept separate from quiz_parser.py: flashcards have their own pipeline.
"""

from __future__ import annotations

from models.flashcard import Flashcard
from utils.json_utils import extract_json_list

_VALID_DIFFICULTIES = {"easy": "Easy", "medium": "Medium", "hard": "Hard"}


def parse_flashcard_json(raw_response: str) -> list[Flashcard]:
    try:
        data = extract_json_list(raw_response, preferred_keys=("flashcards", "cards"))
    except ValueError as exc:
        raise ValueError(f"Failed to parse flashcard JSON from Gemini: {exc}") from exc

    cards: list[Flashcard] = []
    seen_fronts: set[str] = set()
    for item in data:
        try:
            card = _parse_card(item)
        except (KeyError, TypeError, ValueError):
            continue
        key = card.front.casefold()
        if key in seen_fronts:
            continue
        seen_fronts.add(key)
        cards.append(card)

    if not cards:
        raise ValueError("Gemini returned no usable flashcards.")

    return cards


def _parse_card(item: dict) -> Flashcard:
    if not isinstance(item, dict):
        raise TypeError("card is not an object")
    front = str(item["front"]).strip()
    back = str(item["back"]).strip()
    if not front or not back:
        raise ValueError("empty card face")

    topic = str(item.get("topic") or "General").strip()
    difficulty = _VALID_DIFFICULTIES.get(str(item.get("difficulty", "")).strip().lower())

    return Flashcard(front=front, back=back, topic=topic, difficulty=difficulty)
