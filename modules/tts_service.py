"""
modules/tts_service.py

Text-to-speech for study material using gTTS (Google Translate voices).
Returns MP3 bytes; the UI decides how to play or offer them.
"""

from __future__ import annotations

import io

from utils.text_cleaning import strip_markdown

MAX_TTS_CHARS = 6000


class TTSError(Exception):
    pass


def _supported_language(code: str) -> str:
    code = (code or "en").split("-")[0].lower()
    try:
        from gtts.lang import tts_langs

        return code if code in tts_langs() else "en"
    except Exception:  # noqa: BLE001 - language table unavailable offline
        return code or "en"


def prepare_speech_text(markdown_text: str, max_chars: int = MAX_TTS_CHARS) -> str:
    text = strip_markdown(markdown_text)
    if len(text) > max_chars:
        cut = text[:max_chars]
        end = max(cut.rfind(". "), cut.rfind("। "))
        text = cut[: end + 1] if end > max_chars * 0.6 else cut
    return text


def synthesize(markdown_text: str, language_code: str = "en", slow: bool = False) -> bytes:
    """Convert (Markdown) text to MP3 bytes."""
    text = prepare_speech_text(markdown_text)
    if not text:
        raise TTSError("Nothing to read aloud.")
    try:
        from gtts import gTTS

        buffer = io.BytesIO()
        gTTS(text=text, lang=_supported_language(language_code), slow=slow).write_to_fp(buffer)
        return buffer.getvalue()
    except Exception as exc:  # noqa: BLE001
        raise TTSError(f"Text-to-speech failed: {exc}") from exc
