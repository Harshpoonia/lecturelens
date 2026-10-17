"""
ui/components.py

Reusable UI pieces: error cards, timestamp jump buttons.
"""

from __future__ import annotations

import streamlit as st

from modules.ai_service import AIServiceError
from ui.state import jump_to
from utils.time_utils import format_timestamp


def error_card(title: str, message: str = "", help_text: str = "") -> None:
    with st.container(border=True):
        st.error(f"**{title}**", icon=":material/error:")
        if help_text:
            st.write(help_text)
        if message:
            with st.expander("Technical details"):
                st.code(message, language=None)


def ai_error_card(exc: AIServiceError) -> None:
    error_card(exc.title, str(exc), exc.help_text)


def jump_buttons(seconds_list: list[int], key_prefix: str, max_seconds: float | None = None) -> None:
    """Row of '▶ mm:ss' buttons that move the player above to that moment."""
    valid = [s for s in seconds_list if max_seconds is None or s <= max_seconds + 5]
    if not valid:
        return
    columns = st.columns(min(len(valid), 6))
    for i, seconds in enumerate(valid[:6]):
        with columns[i]:
            if st.button(f"▶ {format_timestamp(seconds)}", key=f"{key_prefix}_{i}_{seconds}", width="stretch"):
                jump_to(seconds)
                st.toast(f"Video jumped to {format_timestamp(seconds)}", icon=":material/play_circle:")
                st.rerun()
