import json

import pytest

from utils.flashcard_parser import parse_flashcard_json
from utils.json_utils import extract_json, extract_json_list
from utils.markdown_parser import parse_learning_markdown
from utils.quiz_parser import parse_quiz_json

QUESTION = {
    "question": "What kind of language is Python?",
    "options": ["Compiled", "Interpreted", "Assembly", "Markup"],
    "correct_answer": "Interpreted",
    "explanation": "The video says Python is interpreted.",
    "difficulty": "Easy",
    "timestamp": "00:00",
}


def test_extract_json_handles_fences_and_prose():
    assert extract_json('```json\n[1, 2]\n```') == [1, 2]
    assert extract_json('Here you go:\n[{"a": 1}]\nHope it helps!') == [{"a": 1}]


def test_extract_json_list_unwraps_objects():
    assert extract_json_list('{"questions": [1, 2]}', ("questions",)) == [1, 2]
    assert extract_json_list('{"anything": [3]}') == [3]
    with pytest.raises(ValueError):
        extract_json_list('{"a": 1}')


def test_parse_quiz_basic():
    questions = parse_quiz_json(json.dumps([QUESTION]))
    assert len(questions) == 1
    q = questions[0]
    assert q.correct_answer == "Interpreted"
    assert q.timestamp_seconds == 0
    assert q.is_correct("Interpreted") and not q.is_correct("Compiled") and not q.is_correct(None)


@pytest.mark.parametrize("answer", ["B", "b)", "(B)", "Option B", 1, "interpreted", "B) Interpreted"])
def test_parse_quiz_resolves_answer_variants(answer):
    item = dict(QUESTION, correct_answer=answer)
    assert parse_quiz_json(json.dumps([item]))[0].correct_answer == "Interpreted"


def test_parse_quiz_skips_bad_questions_but_keeps_good_ones():
    bad = dict(QUESTION, options=["a", "b", "c"])
    questions = parse_quiz_json(json.dumps({"questions": [bad, QUESTION]}))
    assert len(questions) == 1


def test_parse_quiz_all_bad_raises():
    with pytest.raises(ValueError):
        parse_quiz_json(json.dumps([dict(QUESTION, correct_answer="Nope")]))
    with pytest.raises(ValueError):
        parse_quiz_json("not json at all")


def test_parse_flashcards_dedupes_and_normalizes():
    raw = json.dumps(
        [
            {"front": "What is a list?", "back": "An ordered, mutable sequence.", "topic": "Types", "difficulty": "easy"},
            {"front": "what is a list?", "back": "dup", "topic": "Types"},
            {"front": "", "back": "empty front is skipped"},
            {"front": "Tuple?", "back": "Immutable sequence.", "difficulty": "Impossible"},
        ]
    )
    cards = parse_flashcard_json(raw)
    assert [c.front for c in cards] == ["What is a list?", "Tuple?"]
    assert cards[0].difficulty == "Easy"
    assert cards[1].difficulty is None and cards[1].topic == "General"


LEARNING_MD = """# Executive Summary
Python basics.

# 2. Key Points:
- Interpreted
- Used in AI

# **Study Notes**
## Lists
Ordered and mutable (see [00:35]).
### Detail
More.

# Important Concepts
- **List**: ordered sequence

# Video Chapters
- [00:00] Introduction
- [01:10] Tuples
- 00:35 – Lists
"""


def test_parse_learning_markdown_with_forgiving_headings_and_chapters():
    content = parse_learning_markdown(LEARNING_MD)
    assert content.executive_summary == "Python basics."
    assert "## Lists" in content.study_notes and "### Detail" in content.study_notes
    assert [c.seconds for c in content.chapters] == [0, 35, 70]
    assert content.chapters[1].title == "Lists"


def test_parse_learning_markdown_missing_section():
    with pytest.raises(ValueError, match="Important Concepts"):
        parse_learning_markdown("# Executive Summary\nx\n# Key Points\ny\n# Study Notes\nz")
