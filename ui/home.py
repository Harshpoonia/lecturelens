"""
ui/home.py

Landing view (hero, URL / paste input, feature grid) and the loading
pipeline that turns a request into a TranscriptData in session state.
"""

from __future__ import annotations

import html

import streamlit as st

from config import settings
from modules.ai_service import AIServiceError
from modules.transcript import TranscriptError, extract_video_id, transcript_from_text
from ui import services
from ui.components import ai_error_card, error_card
from ui.services import AIConfig
from ui.state import remember_recent, reset_video_state

FEATURES = (
    ("📘", "Study notes", "Summary, key points, detailed notes, concepts and clickable chapters."),
    ("💬", "Chat with the video", "Ask anything. Answers cite the exact moment in the video."),
    ("📝", "Adaptive quiz", "Pick difficulty, get instant feedback, retry what you missed."),
    ("🗂️", "Flashcards", "Flip, shuffle, mark what you know, export to Anki."),
    ("🔊", "Listen", "Turn notes into audio for revision on the go."),
    ("📤", "Export", "Download a study pack as PDF, HTML or Markdown."),
)


def _split_title(title: str) -> tuple[str, str]:
    """'LectureLens' -> ('Lecture', 'Lens'); 'Study Stream' -> ('Study ', 'Stream')."""
    if " " in title.strip():
        first, _, rest = title.strip().partition(" ")
        return first + " ", rest
    capitals = [i for i, ch in enumerate(title) if ch.isupper()]
    if len(capitals) >= 2:
        return title[: capitals[-1]], title[capitals[-1]:]
    return title, ""


def render_hero(title: str) -> None:
    first, accent = _split_title(html.escape(title))
    st.markdown(
        f"""<div class="hero"><h1>{first}<span class="accent">{accent}</span></h1>
        <p class="hero-kicker">AI video learning platform</p>
        <p>Turn any YouTube lecture into study notes, a quiz, flashcards and a personal AI tutor.</p></div>""",
        unsafe_allow_html=True,
    )


def render_input(cfg: AIConfig) -> None:
    link_tab, paste_tab = st.tabs(["▶️ YouTube link", "📋 Paste a transcript"])

    with link_tab:
        with st.form("url_form", border=False):
            col_input, col_button = st.columns([5, 1], vertical_alignment="bottom")
            url = col_input.text_input(
                "YouTube video URL",
                placeholder="https://www.youtube.com/watch?v=…  or  https://youtu.be/…",
                label_visibility="collapsed",
            )
            submitted = col_button.form_submit_button("Analyze", type="primary", width="stretch")
        if submitted:
            if not url.strip():
                st.warning("Paste a YouTube link first.")
            elif not cfg.api_key:
                st.warning("Add your Gemini API key in the sidebar first.")
            else:
                st.session_state.pending_load = {"kind": "youtube", "url": url.strip()}
                st.rerun()

    with paste_tab:
        with st.form("paste_form", border=False):
            title = st.text_input("Title (optional)", placeholder="e.g. Lecture 3 — Neural networks")
            text = st.text_area(
                "Transcript",
                height=200,
                placeholder="Paste any transcript or lecture text. Lines starting with [mm:ss] keep their timestamps.",
            )
            link = st.text_input("Matching YouTube link (optional — enables the video player and timestamp links)")
            submitted_paste = st.form_submit_button("Analyze text", type="primary")
        if submitted_paste:
            if not cfg.api_key:
                st.warning("Add your Gemini API key in the sidebar first.")
            else:
                st.session_state.pending_load = {"kind": "paste", "text": text, "title": title, "url": link}
                st.rerun()


def render_features() -> None:
    st.write("")
    for row in (FEATURES[:3], FEATURES[3:]):
        columns = st.columns(3)
        for column, (icon, name, text) in zip(columns, row):
            column.markdown(
                f'<div class="feature-card"><div class="icon">{icon}</div><h4>{name}</h4><p>{text}</p></div>',
                unsafe_allow_html=True,
            )
        st.write("")


# --------------------------------------------------------------------------- #
# Loading pipeline
# --------------------------------------------------------------------------- #

def process_pending_load(cfg: AIConfig, caption_languages: tuple[str, ...]) -> None:
    request = st.session_state.pending_load
    if not request:
        return
    st.session_state.pending_load = None
    reset_video_state()

    try:
        if request["kind"] == "youtube":
            with st.spinner("Fetching captions…"):
                transcript = services.cached_transcript(request["url"], caption_languages)
        elif request["kind"] == "gemini":
            with st.spinner("Gemini is watching the video and transcribing it — this can take a minute…"):
                transcript = services.gemini_transcript(cfg, extract_video_id(request["url"]))
        else:
            video_id = extract_video_id(request["url"]) if request.get("url", "").strip() else None
            transcript = transcript_from_text(request["text"], source="manual", video_id=video_id)
            if request.get("title"):
                transcript.title = request["title"].strip()
    except TranscriptError as exc:
        st.session_state.load_error = {
            "kind": "transcript", "code": exc.code, "message": str(exc), "help": exc.help_text,
            "url": request.get("url", ""), "can_fallback": (
                settings.enable_gemini_video_fallback
                and exc.can_use_gemini_fallback
                and request["kind"] == "youtube"
            ),
        }
        return
    except AIServiceError as exc:
        st.session_state.load_error = {"kind": "ai", "code": exc.code, "message": str(exc), "title": exc.title, "help": exc.help_text}
        return

    transcript = services.with_metadata(transcript)
    st.session_state.transcript = transcript
    if transcript.is_youtube:
        remember_recent(transcript.video_id, transcript.display_title, transcript.video_url)


def render_load_error(cfg: AIConfig) -> None:
    error = st.session_state.load_error
    if not error:
        return

    if error["kind"] == "ai":
        ai_error_card(AIServiceError(error["message"], code=error["code"]))
        return

    error_card("Couldn't get the captions", error["message"], error["help"])
    if error.get("can_fallback"):
        st.markdown("**Two ways to keep going:**")
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("🎬 **Let Gemini watch the video** and transcribe it (uses more of your Gemini quota).")
            if st.button("Transcribe with Gemini", type="primary", width="stretch", disabled=not cfg.api_key):
                st.session_state.pending_load = {"kind": "gemini", "url": error["url"]}
                st.rerun()
        with col_b:
            st.markdown("📋 **Paste the transcript yourself** — on YouTube, open *…more → Show transcript* and copy it.")
            st.caption("Use the “Paste a transcript” tab above.")
