"""
app.py

Entry point for LectureLens, the AI video learning platform (Streamlit).

    streamlit run app.py

This file only wires views together. Rendering lives in ui/, business
logic in modules/, prompts in prompts/, parsing in utils/.
"""

from __future__ import annotations

import logging

import streamlit as st

from config import settings
from ui.home import process_pending_load, render_features, render_hero, render_input, render_load_error
from ui.sidebar import render_sidebar
from ui.state import init_state
from ui.styles import inject_css
from ui.tabs.chat import render_chat_tab
from ui.tabs.export import render_export_tab
from ui.tabs.flashcards import render_flashcards_tab
from ui.tabs.learn import ensure_learning_content, render_learn_tab
from ui.tabs.quiz import render_quiz_tab
from ui.tabs.transcript import render_transcript_tab
from ui.video_header import render_video_header

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

st.set_page_config(
    page_title=settings.app_title,
    page_icon="🔎",
    layout="wide",
    menu_items={"About": "LectureLens — turn YouTube lectures into notes, quizzes, flashcards and an AI tutor. Powered by Google Gemini."},
)


def main() -> None:
    init_state()
    inject_css()
    cfg, caption_languages = render_sidebar()

    process_pending_load(cfg, caption_languages)
    transcript = st.session_state.transcript

    if transcript is None:
        render_hero(settings.app_title)
        render_input(cfg)
        render_load_error(cfg)
        if not st.session_state.load_error:
            render_features()
        return

    render_video_header(transcript)

    # Regenerate notes (from cache when possible) if model or output language changed.
    signature = (cfg.model, cfg.output_language)
    if st.session_state.get("learning_signature") != signature:
        st.session_state.learning = None
        st.session_state.learning_error = None
        st.session_state.learning_signature = signature
    if not st.session_state.learning_error:
        ensure_learning_content(cfg, transcript)

    st.write("")
    learn, chat, quiz, cards, text, export = st.tabs(
        ["Study notes", "Chat", "Quiz", "Flashcards", "Transcript", "Export & audio"]
    )
    for tab, render in (
        (learn, lambda: render_learn_tab(cfg, transcript)),
        (chat, lambda: render_chat_tab(cfg, transcript)),
        (quiz, lambda: render_quiz_tab(cfg, transcript)),
        (cards, lambda: render_flashcards_tab(cfg, transcript)),
        (text, lambda: render_transcript_tab(transcript)),
        (export, lambda: render_export_tab(cfg, transcript)),
    ):
        with tab:
            _safe_render(render)


def _safe_render(render) -> None:
    """Render one tab; an unexpected error is shown in that tab instead of breaking the whole page."""
    try:
        render()
    except Exception as exc:  # noqa: BLE001
        name = type(exc).__name__
        if "Rerun" in name or "Stop" in name:
            raise  # st.rerun() / st.stop() work by raising — let them through
        logging.getLogger(__name__).exception("Tab failed to render")
        st.error("Something went wrong in this tab. The other tabs still work.", icon=":material/error:")
        with st.expander("Technical details"):
            st.exception(exc)


main()
