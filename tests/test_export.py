from models.chat import ChatMessage
from models.flashcard import Flashcard
from models.quiz import QuizAnswer, QuizQuestion
from modules.export_service import (
    StudyPack,
    chat_markdown,
    flashcards_anki_tsv,
    quiz_report_markdown,
    safe_filename,
    study_pack_html,
    study_pack_markdown,
    study_pack_pdf,
    transcript_srt,
    transcript_txt,
)
from modules.tts_service import prepare_speech_text
from tests.test_parsers import LEARNING_MD
from utils.markdown_parser import parse_learning_markdown


def _pack(transcript):
    q = QuizQuestion("Q1?", ["a", "b", "c", "d"], "b", "because", timestamp_seconds=35)
    return StudyPack(
        transcript=transcript,
        learning=parse_learning_markdown(LEARNING_MD),
        quiz=[q],
        quiz_answers=[QuizAnswer(0, "a", False)],
        flashcards=[Flashcard("Front | pipe", "Back\ttab", "Data Types")],
        chat=[ChatMessage("user", "hi"), ChatMessage("assistant", "hello")],
    )


def test_markdown_pack_contains_everything(transcript):
    md = study_pack_markdown(_pack(transcript))
    assert md.startswith("# Python Basics")
    for heading in ("## Executive Summary", "## Study Notes", "### Lists", "## Video Chapters", "## Practice Quiz", "## Flashcards"):
        assert heading in md
    assert "&t=35s" in md
    assert "**B) b** — because" in md
    assert "Front \\| pipe" in md


def test_markdown_pack_can_exclude_sections(transcript):
    md = study_pack_markdown(_pack(transcript), include_quiz=False, include_flashcards=False)
    assert "Practice Quiz" not in md and "## Flashcards" not in md


def test_html_pack_is_self_contained_and_escaped(transcript):
    pack = _pack(transcript)
    pack.learning.executive_summary = "Danger </script><script>alert(1)</script>"
    page = study_pack_html(pack)
    assert page.startswith("<!doctype html>")
    assert "</script><script>alert" not in page


def test_pdf_pack_or_none_without_fpdf(transcript):
    result = study_pack_pdf(_pack(transcript))
    assert result is None or result.startswith(b"%PDF")


def test_small_exports(transcript):
    tsv = flashcards_anki_tsv([Flashcard("Front | pipe", "Back\ttab", "Data Types")])
    assert tsv.splitlines()[-1] == "Front | pipe\tBack tab\tData_Types"
    report = quiz_report_markdown(transcript, _pack(transcript).quiz, [QuizAnswer(0, "a", False)])
    assert "**Score:** 0 / 1 (0%)" in report and "❌" in report
    assert "**AI Tutor**" in chat_markdown(transcript, _pack(transcript).chat)
    assert transcript_txt(transcript).startswith("[00:00] Python")
    srt = transcript_srt(transcript)
    assert srt.startswith("1\n00:00:00,000 --> 00:00:04,000")
    assert safe_filename("Lecture 3: Neural Nets! (Part 1)") == "lecture-3-neural-nets-part-1"
    assert safe_filename("???") == "study-pack"


def test_prepare_speech_text_trims():
    text = prepare_speech_text("# Heading\n\n" + "Sentence here. " * 1000, max_chars=200)
    assert len(text) <= 200 and text.endswith(".")
