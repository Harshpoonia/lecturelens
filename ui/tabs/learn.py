"""
ui/tabs/learn.py

Study notes: summary, key points, notes, concepts, and clickable chapters.
Generated automatically once a transcript is loaded.
"""

from __future__ import annotations

import streamlit as st

from models.transcript import TranscriptData
from modules.ai_service import AIServiceError
from ui import services
from ui.components import ai_error_card, error_card
from ui.services import AIConfig
from ui.state import jump_to
from utils.time_utils import format_timestamp, linkify_timestamps


def ensure_learning_content(cfg: AIConfig, t: TranscriptData) -> None:
    if st.session_state.learning is not None:
        return
    try:
        with st.spinner("Writing your study notes…"):
            st.session_state.learning = services.learning_content(cfg, t, st.session_state.learning_nonce)
            st.session_state.learning_error = None
    except AIServiceError as exc:
        st.session_state.learning_error = {"type": "ai", "code": exc.code, "message": str(exc)}
    except ValueError as exc:
        st.session_state.learning_error = {"type": "parse", "message": str(exc)}


def render_learn_tab(cfg: AIConfig, t: TranscriptData) -> None:
    error = st.session_state.learning_error
    content = st.session_state.learning

    if content is None:
        if error:
            if error["type"] == "ai":
                ai_error_card(AIServiceError(error["message"], code=error["code"]))
            else:
                error_card("Couldn't structure the notes", error["message"], "The model's answer wasn't in the expected format. Retrying usually fixes it.")
            if st.button("🔄 Try again", key="learn_retry"):
                st.session_state.learning_error = None
                ensure_learning_content(cfg, t)
                st.rerun()
        return

    link = (lambda text: linkify_timestamps(text, t.video_id, t.duration_seconds)) if t.is_youtube else (lambda text: text)

    if content.chapters and t.is_youtube:
        col_notes, col_chapters = st.columns([3, 1], gap="large")
    else:
        col_notes, col_chapters = st.container(), None

    with col_notes:
        tabs = st.tabs(["Summary", "Key points", "Study notes", "Concepts"])
        with tabs[0]:
            st.markdown(link(content.executive_summary))
        with tabs[1]:
            st.markdown(link(content.key_points))
        with tabs[2]:
            st.markdown(link(content.study_notes))
        with tabs[3]:
            st.markdown(link(content.important_concepts))

    if col_chapters is not None:
        with col_chapters:
            st.markdown("**🧭 Chapters**")
            for i, chapter in enumerate(content.chapters):
                if t.duration_seconds and chapter.seconds > t.duration_seconds + 5:
                    continue
                label = f"{format_timestamp(chapter.seconds)} · {chapter.title}"
                if st.button(label, key=f"chapter_{st.session_state.run_id}_{i}", width="stretch"):
                    jump_to(chapter.seconds)
                    st.rerun()

    with st.expander("Not quite right?"):
        st.caption("Regenerate the notes, or change the output language / model in the sidebar first.")
        if st.button("🔄 Regenerate notes", key="learn_regen"):
            st.session_state.learning = None
            st.session_state.learning_nonce += 1
            ensure_learning_content(cfg, t)
            st.rerun()
