"""
ui/tabs/export.py

Listen to study material (text-to-speech) and download everything.
"""

from __future__ import annotations

import streamlit as st

from config import OUTPUT_LANGUAGES
from models.transcript import TranscriptData
from modules.export_service import (
    StudyPack,
    chat_markdown,
    flashcards_anki_tsv,
    quiz_report_markdown,
    safe_filename,
    study_pack_html,
    study_pack_markdown,
    study_pack_pdf,
)
from modules.tts_service import TTSError
from ui import services
from ui.services import AIConfig


def render_export_tab(cfg: AIConfig, t: TranscriptData) -> None:
    learning = st.session_state.learning
    _render_audio(cfg, t, learning)
    st.divider()
    _render_downloads(t, learning)


def _render_audio(cfg: AIConfig, t: TranscriptData, learning) -> None:
    st.markdown("#### Listen")
    sources: dict[str, str] = {}
    if learning:
        sources = {
            "Executive summary": learning.executive_summary,
            "Key points": learning.key_points,
            "Important concepts": learning.important_concepts,
            "Study notes": learning.study_notes,
        }
    if st.session_state.flashcards:
        sources["Flashcards (question, then answer)"] = "\n\n".join(
            f"{c.front}. ... {c.back}" for c in st.session_state.flashcards
        )
    if not sources:
        st.caption("Audio becomes available once your study notes are ready.")
        return

    col_pick, col_button = st.columns([3, 1], vertical_alignment="bottom")
    choice = col_pick.selectbox("What should I read aloud?", list(sources.keys()), key="tts_choice")
    language_code = OUTPUT_LANGUAGES.get(cfg.output_language, "") or (t.language_code or "en")
    if col_button.button("Create audio", width="stretch", icon=":material/headphones:"):
        text = sources[choice]
        try:
            with st.spinner("Recording…"):
                st.session_state.audio[choice] = services.cached_tts(services.text_hash(text + language_code), language_code, text)
        except TTSError as exc:
            st.error(str(exc))

    audio = st.session_state.audio.get(choice)
    if audio:
        st.audio(audio, format="audio/mp3")
        st.download_button(
            "Download MP3", audio, icon=":material/download:", file_name=f"{safe_filename(t.display_title)}-{safe_filename(choice)}.mp3",
            mime="audio/mpeg",
        )
        if len(sources[choice]) > 6000:
            st.caption("Long sections are trimmed to the first ~6,000 characters for audio.")


def _render_downloads(t: TranscriptData, learning) -> None:
    st.markdown("#### Download your study pack")
    if not learning:
        st.caption("Downloads become available once your study notes are ready.")
        return

    c1, c2 = st.columns(2)
    include_quiz = c1.checkbox("Include quiz + answer key", value=bool(st.session_state.quiz),
                               disabled=not st.session_state.quiz)
    include_cards = c2.checkbox("Include flashcards", value=bool(st.session_state.flashcards),
                                disabled=not st.session_state.flashcards)

    pack = StudyPack(
        transcript=t,
        learning=learning,
        quiz=(st.session_state.quiz or []) if include_quiz else [],
        flashcards=(st.session_state.flashcards or []) if include_cards else [],
    )
    base = safe_filename(t.display_title)

    d1, d2, d3 = st.columns(3)
    pdf_bytes = _pdf(pack)
    if pdf_bytes:
        d1.download_button("PDF", pdf_bytes, icon=":material/picture_as_pdf:", file_name=f"{base}.pdf", mime="application/pdf", width="stretch")
    else:
        d1.button("PDF (install fpdf2)", disabled=True, width="stretch", icon=":material/picture_as_pdf:")
    d2.download_button("Printable HTML", study_pack_html(pack), icon=":material/print:", file_name=f"{base}.html", mime="text/html", width="stretch")
    d3.download_button("Markdown", study_pack_markdown(pack), icon=":material/description:", file_name=f"{base}.md", mime="text/markdown", width="stretch")
    st.caption("Tip: for non-Latin scripts (Hindi, Japanese…), open the HTML file and use your browser's “Save as PDF”.")

    extras = []
    if st.session_state.flashcards:
        extras.append(("Flashcards for Anki (.txt)", flashcards_anki_tsv(st.session_state.flashcards), f"{base}-anki.txt", "text/plain"))
    if st.session_state.quiz and st.session_state.quiz_report:
        report = quiz_report_markdown(t, st.session_state.quiz, st.session_state.quiz_report)
        extras.append(("Quiz report", report, f"{base}-quiz-report.md", "text/markdown"))
    if st.session_state.chat:
        extras.append(("Chat transcript", chat_markdown(t, st.session_state.chat), f"{base}-chat.md", "text/markdown"))
    if extras:
        columns = st.columns(len(extras))
        for column, (label, data, name, mime) in zip(columns, extras):
            column.download_button(label, data, file_name=name, mime=mime, width="stretch")


@st.cache_data(show_spinner=False, max_entries=16)
def _cached_pdf(key: str, _pack: StudyPack) -> bytes | None:
    return study_pack_pdf(_pack)


def _pdf(pack: StudyPack) -> bytes | None:
    key = services.text_hash(study_pack_markdown(pack))
    try:
        return _cached_pdf(key, pack)
    except Exception:  # noqa: BLE001 - never break the page over a PDF
        return None
