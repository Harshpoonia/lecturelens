"""
config.py

Centralized configuration for LectureLens.

Settings are read (in priority order) from:
1. Streamlit secrets (.streamlit/secrets.toml or the Streamlit Cloud secrets UI)
2. Environment variables / .env file

No other module should read os.environ or st.secrets directly — everything
related to configuration flows through this file.

Importing this module never fails because a key is missing: a public
deployment can run without a server-side key and ask each visitor for
their own Gemini key instead ("bring your own key").
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values

# Always read the .env next to this file, wherever the app is launched from.
ENV_FILE = Path(__file__).resolve().parent / ".env"


def _load_env_file(path: Path) -> None:
    """
    Load .env robustly. Handles files saved by Windows tools as UTF-8 with a
    BOM or as UTF-16, and lets .env fill variables that are missing *or empty*
    in the real environment. Non-empty real environment variables still win,
    so platform secrets on a deployment are never overridden.
    """
    if not path.exists():
        return
    raw = path.read_bytes()
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        encoding = "utf-16"
    else:
        encoding = "utf-8-sig"
    try:
        text = raw.decode(encoding)
    except UnicodeDecodeError:
        text = raw.decode("utf-8", errors="ignore")

    import io

    for key, value in dotenv_values(stream=io.StringIO(text)).items():
        key = key.strip().lstrip("\ufeff")
        if value is not None and not os.environ.get(key):
            os.environ[key] = value.strip().strip('"').strip("'")


_load_env_file(ENV_FILE)

# Gemini 2.0 Flash was shut down on 2026-06-01 and Gemini 2.5 Flash on
# 2026-10-16. The 3.x family is the supported default.
DEFAULT_MODEL = "gemini-3.5-flash"
DEFAULT_MODEL_CHOICES = ("gemini-3.5-flash", "gemini-3.1-flash-lite")

# Output languages offered for generated study material.
# Value is the gTTS / ISO language code used for audio.
OUTPUT_LANGUAGES: dict[str, str] = {
    "Same as video": "",
    "English": "en",
    "Hindi": "hi",
    "Spanish": "es",
    "French": "fr",
    "German": "de",
    "Portuguese": "pt",
    "Japanese": "ja",
    "Bengali": "bn",
    "Tamil": "ta",
    "Marathi": "mr",
}


def _read_streamlit_secret(key: str) -> str | None:
    """Return a value from st.secrets, or None if unavailable."""
    try:
        import streamlit as st  # local import keeps config testable without Streamlit

        if key in st.secrets:
            value = st.secrets[key]
            return str(value) if value is not None else None
    except Exception:  # noqa: BLE001 - no secrets file / not running under Streamlit
        return None
    return None


def _get(key: str, default: str = "") -> str:
    value = _read_streamlit_secret(key)
    if value is None or value == "":
        value = os.getenv(key, default)
    return (value or "").strip()


def _get_bool(key: str, default: bool) -> bool:
    raw = _get(key, "true" if default else "false").lower()
    return raw in {"1", "true", "yes", "on"}


def _get_int(key: str, default: int) -> int:
    try:
        return int(_get(key, str(default)))
    except ValueError:
        return default


def _get_list(key: str, default: tuple[str, ...]) -> tuple[str, ...]:
    raw = _get(key, "")
    if not raw:
        return default
    return tuple(item.strip() for item in raw.split(",") if item.strip())


@dataclass(frozen=True)
class Settings:
    """Immutable application settings."""

    gemini_api_key: str
    gemini_model: str
    model_choices: tuple[str, ...]
    app_title: str
    max_transcript_chars: int
    ai_max_retries: int
    allow_user_api_key: bool
    enable_gemini_video_fallback: bool
    transcript_languages: tuple[str, ...]
    # Optional proxy for youtube-transcript-api (YouTube blocks most cloud IPs).
    webshare_proxy_username: str = ""
    webshare_proxy_password: str = ""
    transcript_proxy_url: str = ""
    cache_ttl_seconds: int = 60 * 60 * 6
    # Max Gemini calls per browser session when the app's own key is used
    # (protects a public deployment's quota). 0 = unlimited. Visitors who
    # bring their own key are never limited.
    session_ai_call_limit: int = 40
    github_url: str = ""

    @property
    def has_server_api_key(self) -> bool:
        return bool(self.gemini_api_key)


def load_settings() -> Settings:
    """Load settings from Streamlit secrets and environment variables."""
    model = _get("GEMINI_MODEL", DEFAULT_MODEL)
    choices = _get_list("GEMINI_MODEL_CHOICES", DEFAULT_MODEL_CHOICES)
    if model not in choices:
        choices = (model, *choices)

    return Settings(
        gemini_api_key=_get("GEMINI_API_KEY"),
        gemini_model=model,
        model_choices=choices,
        app_title=_get("APP_TITLE", "LectureLens"),
        max_transcript_chars=_get_int("MAX_TRANSCRIPT_CHARS", 200_000),
        ai_max_retries=_get_int("AI_MAX_RETRIES", 3),
        allow_user_api_key=_get_bool("ALLOW_USER_API_KEY", True),
        enable_gemini_video_fallback=_get_bool("ENABLE_GEMINI_VIDEO_FALLBACK", True),
        transcript_languages=_get_list("TRANSCRIPT_LANGUAGES", ("en", "hi")),
        webshare_proxy_username=_get("WEBSHARE_PROXY_USERNAME"),
        webshare_proxy_password=_get("WEBSHARE_PROXY_PASSWORD"),
        transcript_proxy_url=_get("TRANSCRIPT_PROXY_URL"),
        cache_ttl_seconds=_get_int("CACHE_TTL_SECONDS", 60 * 60 * 6),
        session_ai_call_limit=_get_int("SESSION_AI_CALL_LIMIT", 40),
        github_url=_get("GITHUB_URL"),
    )


settings = load_settings()


def server_api_key() -> str:
    """
    The server-side Gemini key, read fresh on every call.

    Streamlit Cloud secrets can be added or changed while the app is running;
    `settings` is computed once at import, so the UI uses this instead.
    """
    return _get("GEMINI_API_KEY")
