"""
ui/sidebar.py

Sidebar: Gemini key (server key or bring-your-own), model, output
language, caption language preference, recent videos.
"""

from __future__ import annotations

import streamlit as st

from config import ENV_FILE, OUTPUT_LANGUAGES, settings
from ui.services import AIConfig
from ui.state import reset_video_state
from ui.styles import brand_html

CAPTION_LANGUAGES = {
    "en": "English", "hi": "Hindi", "es": "Spanish", "fr": "French", "de": "German",
    "pt": "Portuguese", "ja": "Japanese", "ko": "Korean", "bn": "Bengali", "ta": "Tamil",
    "te": "Telugu", "mr": "Marathi", "ur": "Urdu", "ar": "Arabic", "ru": "Russian", "zh-Hans": "Chinese",
}


def render_sidebar() -> tuple[AIConfig, tuple[str, ...]]:
    with st.sidebar:
        st.markdown(brand_html(settings.app_title), unsafe_allow_html=True)

        if st.session_state.transcript is not None:
            if st.button("New video", width="stretch", icon=":material/add:", key="new_video"):
                reset_video_state()
                st.rerun()

        _recent_section()

        st.markdown('<div class="ll-eyebrow">Gemini</div>', unsafe_allow_html=True)
        api_key, uses_own_key = _api_key_section()

        st.markdown('<div class="ll-eyebrow">Settings</div>', unsafe_allow_html=True)

        model = st.selectbox(
            "Gemini model",
            settings.model_choices,
            index=settings.model_choices.index(settings.gemini_model),
            help="Flash is the best balance of quality and speed. Flash-Lite is cheaper and has higher free limits.",
        )
        language_label = st.selectbox(
            "Write study material in",
            list(OUTPUT_LANGUAGES.keys()),
            help="Generate notes, quizzes and chat answers in another language than the video.",
        )
        caption_langs = st.multiselect(
            "Preferred caption languages",
            list(CAPTION_LANGUAGES.keys()),
            default=[c for c in settings.transcript_languages if c in CAPTION_LANGUAGES] or ["en"],
            format_func=lambda c: CAPTION_LANGUAGES.get(c, c),
            help="Used to pick between caption tracks. Any available language is used as a fallback.",
        )

        st.divider()
        if not uses_own_key and settings.session_ai_call_limit > 0 and api_key:
            used, limit = st.session_state.ai_calls, settings.session_ai_call_limit
            st.markdown(
                f'<div class="ll-meter-row"><span>Demo requests</span><span>{used} / {limit}</span></div>'
                f'<div class="ll-meter"><div style="width:{min(100, round(100 * used / limit))}%"></div></div>',
                unsafe_allow_html=True,
            )
        links = "[Get a free Gemini key](https://aistudio.google.com/apikey)"
        if settings.github_url:
            links += f" · [Source on GitHub]({settings.github_url})"
        st.caption(links)

    cfg = AIConfig(
        api_key=api_key,
        model=model,
        output_language="" if language_label == "Same as video" else language_label,
        uses_own_key=uses_own_key,
    )
    return cfg, tuple(caption_langs or ["en"])


def _api_key_section() -> tuple[str, bool]:
    if settings.has_server_api_key:
        if not settings.allow_user_api_key:
            st.markdown(_status("Connected · server key"), unsafe_allow_html=True)
            return settings.gemini_api_key, False
        own = st.session_state.get("user_api_key", "") or ""
        st.markdown(_status("Connected · your key" if own.strip() else "Connected · server key"), unsafe_allow_html=True)
        with st.expander("Use my own key", expanded=False, icon=":material/key:"):
            st.caption("Add your own key for unlimited use — it stays in this browser session only.")
            own = st.text_input("Your Gemini API key (optional)", type="password", key="user_api_key")
        if own.strip():
            return own.strip(), True
        return settings.gemini_api_key, False

    if not settings.allow_user_api_key:
        st.error("No Gemini API key is configured on the server.")
        return "", False

    own = st.text_input(
        "Gemini API key",
        type="password",
        key="user_api_key",
        placeholder="AIza…",
        help="Free from Google AI Studio. Used only for your session and never stored.",
    )
    if own.strip():
        st.markdown(_status("Connected · your key"), unsafe_allow_html=True)
    else:
        st.markdown(_status("Add a key to start", warn=True), unsafe_allow_html=True)
        st.caption("[Get a free key from Google AI Studio →](https://aistudio.google.com/apikey)")
        if ENV_FILE.exists():
            st.caption(
                "A .env file exists but no GEMINI_API_KEY was read from it. Check the line is "
                "`GEMINI_API_KEY=your-key`, the file is saved as UTF-8, then restart the app."
            )
    return own.strip(), True


def _status(text: str, warn: bool = False) -> str:
    return f'<div class="ll-status{" warn" if warn else ""}"><span class="ll-dot"></span>{text}</div>'


def _recent_section() -> None:
    recent = st.session_state.recent
    if not recent:
        return
    st.markdown('<div class="ll-eyebrow">Recent</div>', unsafe_allow_html=True)
    current = st.session_state.transcript.video_id if st.session_state.transcript else None
    for item in recent:
        label = item["title"] if len(item["title"]) <= 42 else item["title"][:40] + "…"
        if st.button(label, key=f"recent_{item['video_id']}", width="stretch",
                     disabled=item["video_id"] == current):
            st.session_state.pending_load = {"kind": "youtube", "url": item["url"]}
            st.rerun()
    st.write("")
