"""
utils/quiz_parser.py

Parses Gemini's JSON quiz output into QuizQuestion objects.

Lenient about harmless deviations (code fences, a wrapper object,
"B" instead of the option text for the answer) and strict about real
schema problems (wrong option count, answer not among the options).
"""

from __future__ import annotations

from models.quiz import QuizQuestion
from utils.json_utils import extract_json_list
from utils.time_utils import parse_timestamp

_LETTERS = "ABCD"


def parse_quiz_json(raw_response: str) -> list[QuizQuestion]:
    try:
        data = extract_json_list(raw_response, preferred_keys=("questions", "quiz"))
    except ValueError as exc:
        raise ValueError(f"Failed to parse quiz JSON from Gemini: {exc}") from exc

    questions: list[QuizQuestion] = []
    errors: list[str] = []
    for i, item in enumerate(data):
        try:
            questions.append(_parse_question(item))
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"question {i + 1}: {exc}")

    if not questions:
        detail = f" ({'; '.join(errors[:3])})" if errors else ""
        raise ValueError(f"Gemini returned no usable quiz questions{detail}.")

    return questions


def _parse_question(item: dict) -> QuizQuestion:
    if not isinstance(item, dict):
        raise TypeError("question is not an object")

    question = str(item["question"]).strip()
    options = [str(option).strip() for option in item["options"]]
    if len(options) != 4:
        raise ValueError(f"expected exactly 4 options, got {len(options)}")
    if len(set(options)) != 4:
        raise ValueError("options are not unique")

    correct_answer = _resolve_answer(item.get("correct_answer", item.get("answer")), options)

    timestamp = item.get("timestamp")
    timestamp_seconds = parse_timestamp(str(timestamp)) if timestamp else None

    return QuizQuestion(
        question=question,
        options=options,
        correct_answer=correct_answer,
        explanation=str(item.get("explanation", "")).strip(),
        difficulty=str(item.get("difficulty", "")).strip() or None,
        timestamp_seconds=timestamp_seconds,
    )


def _resolve_answer(raw_answer: object, options: list[str]) -> str:
    if raw_answer is None:
        raise KeyError("correct_answer")

    if isinstance(raw_answer, int) and 0 <= raw_answer < len(options):
        return options[raw_answer]

    answer = str(raw_answer).strip()
    for option in options:
        if option == answer or option.casefold() == answer.casefold():
            return option

    # "B", "B)", "(B)", "Option B"
    letter = answer.upper().replace("OPTION", "").strip(" ().:")
    if len(letter) == 1 and letter in _LETTERS:
        return options[_LETTERS.index(letter)]

    # "B) Some text" — strip a leading letter label and retry.
    if len(answer) > 3 and answer[0].upper() in _LETTERS and answer[1] in ").:":
        stripped = answer[2:].strip()
        for option in options:
            if option.casefold() == stripped.casefold():
                return option

    raise ValueError(f"correct_answer '{answer}' does not match any option")
