"""
ui/tabs/chat.py

Chat with the video: streaming, transcript-grounded answers with
clickable timestamps, tutor modes and suggested questions.
"""

from __future__ import annotations

import streamlit as st

from models.chat import ChatMessage
from models.transcript import TranscriptData
from modules.ai_service import AIServiceError
from modules.chat_service import chat_modes
from ui import services
from ui.components import ai_error_card, jump_buttons
from ui.services import AIConfig
from utils.time_utils import find_timestamps, linkify_timestamps

STARTERS = (
    "Summarize this video in 3 sentences",
    "What are the most important terms to know?",
    "What should I already know before watching this?",
)


def render_chat_tab(cfg: AIConfig, t: TranscriptData) -> None:
    modes = chat_modes()
    mode = st.segmented_control(
        "Tutor mode",
        options=list(modes.keys()),
        format_func=lambda key: modes[key]["label"],
        default="ask",
        key=f"chat_mode_{st.session_state.run_id}",
    ) or "ask"

    history: list[ChatMessage] = st.session_state.chat
    if not history:
        _render_suggestions(cfg, t)

    box = st.container(height=520, border=True) if history else st.container()
    with box:
        for i, message in enumerate(history):
            with st.chat_message(message.role, avatar=":material/person:" if message.role == "user" else ":material/school:"):
                st.markdown(_render_text(message.content, t))
                if message.role == "assistant" and t.is_youtube:
                    jump_buttons(find_timestamps(message.content), f"chatjump_{st.session_state.run_id}_{i}", t.duration_seconds)

    placeholder = {
        "ask": "Ask anything about this video…",
        "compare": "Which concepts should I compare?",
        "practice": "Which topic do you want to practise?",
    }.get(mode, "What should I explain?")
    typed = st.chat_input(placeholder, key=f"chat_input_{st.session_state.run_id}")
    question = typed or st.session_state.chat_pending
    st.session_state.chat_pending = None

    if question:
        _answer(cfg, t, question, mode, box)

    if history:
        col_a, col_b = st.columns([1, 5])
        if col_a.button("Clear chat", key="chat_clear", icon=":material/delete_sweep:"):
            st.session_state.chat = []
            st.rerun()
        col_b.caption("Answers come from the video's transcript. Timestamps jump the player to that moment.")


def _render_text(text: str, t: TranscriptData) -> str:
    return linkify_timestamps(text, t.video_id, t.duration_seconds) if t.is_youtube else text


def _answer(cfg: AIConfig, t: TranscriptData, question: str, mode: str, box) -> None:
    history: list[ChatMessage] = st.session_state.chat
    with box:
        with st.chat_message("user", avatar=":material/person:"):
            st.markdown(question)
        with st.chat_message("assistant", avatar=":material/school:"):
            try:
                stream = services.chat_service(cfg).stream_answer(
                    t, history, question, mode=mode, output_language=cfg.output_language
                )
                answer = st.write_stream(stream)
            except AIServiceError as exc:
                ai_error_card(exc)
                return
    history.append(ChatMessage(role="user", content=question, mode=mode))
    history.append(ChatMessage(role="assistant", content=str(answer), mode=mode))
    st.rerun()


def _render_suggestions(cfg: AIConfig, t: TranscriptData) -> None:
    st.markdown("##### Try asking")
    suggestions = st.session_state.suggested_questions or list(STARTERS)
    columns = st.columns(len(suggestions[:4]) or 1)
    for i, text in enumerate(suggestions[:4]):
        if columns[i].button(text, key=f"suggest_{st.session_state.run_id}_{i}", width="stretch"):
            st.session_state.chat_pending = text
            st.rerun()

    if st.session_state.suggested_questions is None:
        if st.button("Suggest questions about this video", key="suggest_more", icon=":material/auto_awesome:"):
            try:
                with st.spinner("Reading the video…"):
                    st.session_state.suggested_questions = services.suggested_questions(cfg, t) or list(STARTERS)
            except (AIServiceError, ValueError) as exc:
                st.toast(f"Couldn't get suggestions: {exc}")
            st.rerun()
