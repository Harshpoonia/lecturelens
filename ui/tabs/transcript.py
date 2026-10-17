"""
ui/tabs/transcript.py

Transcript analytics and a searchable, clickable transcript viewer.
"""

from __future__ import annotations

import re

import pandas as pd
import streamlit as st

from models.transcript import TranscriptData
from modules.export_service import safe_filename, transcript_srt, transcript_txt
from ui.state import jump_to
from utils.text_statistics import top_terms
from utils.time_utils import format_timestamp


def render_transcript_tab(t: TranscriptData) -> None:
    st.markdown("#### Transcript analytics")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Words", f"{t.word_count:,}")
    c2.metric("Characters", f"{t.char_count:,}")
    c3.metric("Reading time", f"{t.reading_time_minutes} min")
    c4.metric("Speaking pace", f"{t.speaking_wpm} wpm" if t.speaking_wpm else "—")

    terms = top_terms(t.cleaned_text)
    if len(terms) >= 5:
        st.markdown("**Most frequent terms**")
        chart = pd.DataFrame(terms, columns=["term", "count"]).set_index("term")
        st.bar_chart(chart, horizontal=True, height=320)

    st.divider()
    st.markdown("#### Transcript")
    query = st.text_input("Search the transcript", placeholder="Type a word or phrase…", key=f"tsearch_{st.session_state.run_id}")

    if t.segments:
        rows = [{"Time": format_timestamp(s.start), "Text": s.text, "_start": s.start} for s in t.segments]
        frame = pd.DataFrame(rows)
        if query.strip():
            frame = frame[frame["Text"].str.contains(re.escape(query.strip()), case=False, na=False)]
            st.caption(f"{len(frame)} matching line(s)")
        hint = "Select a row to jump the video to that moment." if t.is_youtube else ""
        if hint:
            st.caption(hint)
        event = st.dataframe(
            frame[["Time", "Text"]],
            hide_index=True,
            width="stretch",
            height=420,
            on_select="rerun" if t.is_youtube else "ignore",
            selection_mode="single-row",
            key=f"tframe_{st.session_state.run_id}_{query}",
        )
        selected = getattr(getattr(event, "selection", None), "rows", []) if t.is_youtube else []
        if selected:
            start = float(frame.iloc[selected[0]]["_start"])
            marker = (st.session_state.run_id, query, selected[0])
            if st.session_state.get("transcript_last_selection") != marker:  # act on new clicks only
                st.session_state.transcript_last_selection = marker
                jump_to(start)
                st.rerun()
    else:
        text = t.cleaned_text
        if query.strip():
            count = len(re.findall(re.escape(query.strip()), text, flags=re.I))
            st.caption(f"{count} match(es)")
        st.text_area("Transcript text", text, height=420, label_visibility="collapsed", disabled=True)

    base = safe_filename(t.display_title, "transcript")
    d1, d2, _ = st.columns([1, 1, 3])
    d1.download_button(".txt", icon=":material/download:", data=transcript_txt(t), file_name=f"{base}.txt", mime="text/plain", width="stretch")
    srt = transcript_srt(t)
    if srt:
        d2.download_button(".srt", icon=":material/download:", data=srt, file_name=f"{base}.srt", mime="application/x-subrip", width="stretch")
