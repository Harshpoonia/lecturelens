"""
ui/video_header.py

Embedded player + video facts shown above the study tabs.
"""

from __future__ import annotations

import html

import streamlit as st

from config import settings
from models.transcript import TranscriptData
from utils.time_utils import format_timestamp


def render_video_header(t: TranscriptData) -> None:
    if t.is_youtube:
        col_video, col_info = st.columns([3, 2], gap="large")
        with col_video:
            _player(t)
    else:
        col_info = st.container()

    with col_info:
        st.markdown(f'<div class="video-title">{html.escape(t.display_title)}</div>', unsafe_allow_html=True)
        if t.channel:
            st.markdown(f'<div class="video-sub">{html.escape(t.channel)}</div>', unsafe_allow_html=True)
        st.markdown(
            f'<span class="badge">{html.escape(t.source_label)}</span>'
            f'<span class="badge neutral">{html.escape(t.language)}</span>',
            unsafe_allow_html=True,
        )
        duration = format_timestamp(t.duration_seconds) if t.duration_seconds else "—"
        st.markdown(
            '<div class="ll-stats">'
            f'<div class="ll-stat"><small>Duration</small><b>{duration}</b></div>'
            f'<div class="ll-stat"><small>Words</small><b>{t.word_count:,}</b></div>'
            f'<div class="ll-stat"><small>Read time</small><b>{t.reading_time_minutes} min</b></div>'
            "</div>",
            unsafe_allow_html=True,
        )

        if t.char_count > settings.max_transcript_chars:
            share = round(100 * settings.max_transcript_chars / t.char_count)
            st.warning(
                f"Long video: the AI uses the first ~{share}% of the transcript. "
                "Raise MAX_TRANSCRIPT_CHARS to include more.",
                icon=":material/content_cut:",
            )


def _player(t: TranscriptData) -> None:
    start = int(st.session_state.player_start or 0)
    autoplay = bool(st.session_state.player_autoplay)
    try:
        st.video(t.video_url, start_time=start, autoplay=autoplay)
    except TypeError:  # older Streamlit without autoplay
        st.video(t.video_url, start_time=start)
    st.session_state.player_autoplay = False
