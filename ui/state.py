"""
ui/state.py

Session-state schema for the Streamlit app. Every key the UI uses is
declared here with its default, so state is easy to reason about and
to reset when a new video is loaded.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

# State that belongs to the currently loaded video.
VIDEO_DEFAULTS: dict[str, Any] = {
    "transcript": None,
    "learning": None,
    "learning_error": None,
    "learning_nonce": 0,
    # quiz
    "quiz": None,
    "quiz_nonce": 0,
    "quiz_order": [],
    "quiz_pos": 0,
    "quiz_answers": [],
    "quiz_submitted": False,
    "quiz_selected": None,
    "quiz_round": 0,
    "quiz_report": [],  # answers from the last complete first-round attempt
    # flashcards
    "flashcards": None,
    "fc_nonce": 0,
    "fc_order": [],
    "fc_pos": 0,
    "fc_flipped": False,
    "fc_known": set(),
    "fc_only_learning": False,
    # chat
    "chat": [],
    "chat_pending": None,
    "suggested_questions": None,
    # player
    "player_start": 0,
    "player_autoplay": False,
    # audio
    "audio": {},
}

# State that survives switching videos.
SESSION_DEFAULTS: dict[str, Any] = {
    "recent": [],
    "pending_load": None,
    "load_error": None,
    "ai_calls": 0,
    "run_id": 0,
}


def init_state() -> None:
    for defaults in (SESSION_DEFAULTS, VIDEO_DEFAULTS):
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = _fresh(value)


def reset_video_state() -> None:
    for key, value in VIDEO_DEFAULTS.items():
        st.session_state[key] = _fresh(value)
    st.session_state.load_error = None
    st.session_state.run_id += 1  # gives widgets fresh keys for the new video


def _fresh(value: Any) -> Any:
    if isinstance(value, (list, dict, set)):
        return type(value)()
    return value


def remember_recent(video_id: str, title: str, url: str) -> None:
    recent = [item for item in st.session_state.recent if item["video_id"] != video_id]
    recent.insert(0, {"video_id": video_id, "title": title, "url": url})
    st.session_state.recent = recent[:6]


def jump_to(seconds: int | float) -> None:
    """Move the embedded player to a timestamp (applied on the next rerun)."""
    st.session_state.player_start = int(seconds)
    st.session_state.player_autoplay = True
