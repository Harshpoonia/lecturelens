"""
modules/transcript.py

Responsible for:
- Extracting the video ID from any common YouTube URL format
- Fetching captions via youtube-transcript-api (any language, optional proxy)
- Building TranscriptData from captions, a Gemini transcription or pasted text

No AI calls and no UI code live here.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any
from urllib.parse import parse_qs, urlparse

from config import settings
from models.transcript import TranscriptData, TranscriptSegment
from utils.text_cleaning import clean_transcript_text
from utils.time_utils import parse_timestamp

_ID = re.compile(r"^[0-9A-Za-z_-]{11}$")
_YOUTUBE_HOSTS = ("youtube.com", "youtu.be", "youtube-nocookie.com")
_TIMED_LINE = re.compile(r"^\s*\[?((?:\d{1,2}:)?\d{1,2}:\d{2})\]?\s*[-–:]?\s*(.*)$")
_LANGUAGE_LINE = re.compile(r"^\s*LANGUAGE\s*:\s*([^()\n]+?)\s*(?:\(([\w-]+)\))?\s*$", re.I)

TRANSCRIPT_ERROR_HELP = {
    "invalid_url": "That doesn't look like a YouTube video link. Paste a full URL like https://www.youtube.com/watch?v=…",
    "disabled": "The creator turned off captions for this video.",
    "not_found": "This video has no captions YouTube will share.",
    "unavailable": "The video is private, removed, or region-locked.",
    "age_restricted": "The video is age-restricted, so captions can't be downloaded without signing in.",
    "blocked": "YouTube is blocking caption downloads from this server's IP address (common on cloud hosts).",
    "empty": "Captions were found but contained no usable text.",
    "unknown": "Captions couldn't be downloaded right now.",
}


class TranscriptError(Exception):
    """Raised when a transcript cannot be obtained. `code` is a TRANSCRIPT_ERROR_HELP key."""

    def __init__(self, message: str, code: str = "unknown") -> None:
        super().__init__(message)
        self.code = code

    @property
    def help_text(self) -> str:
        return TRANSCRIPT_ERROR_HELP.get(self.code, TRANSCRIPT_ERROR_HELP["unknown"])

    @property
    def can_use_gemini_fallback(self) -> bool:
        """Gemini can watch the video itself unless the video is gone or the URL is bad."""
        return self.code not in {"invalid_url", "unavailable"}


# --------------------------------------------------------------------------- #
# URL handling
# --------------------------------------------------------------------------- #

def extract_video_id(youtube_url: str) -> str:
    """
    Extract the 11-character video ID from watch, youtu.be, shorts, embed,
    live and mobile URLs, or accept a bare ID.
    """
    value = (youtube_url or "").strip()
    if _ID.match(value):
        return value

    if not re.match(r"^https?://", value, re.I):
        value = "https://" + value
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower()

    if any(host == h or host.endswith("." + h) for h in _YOUTUBE_HOSTS):
        if host.endswith("youtu.be"):
            candidate = parsed.path.strip("/").split("/")[0]
            if _ID.match(candidate):
                return candidate
        query_id = parse_qs(parsed.query).get("v", [""])[0]
        if _ID.match(query_id):
            return query_id
        parts = [p for p in parsed.path.split("/") if p]
        for marker in ("shorts", "embed", "live", "v", "e"):
            if marker in parts:
                index = parts.index(marker)
                if index + 1 < len(parts) and _ID.match(parts[index + 1]):
                    return parts[index + 1]

    raise TranscriptError(f"Could not find a video ID in: {youtube_url}", code="invalid_url")


def canonical_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"


# --------------------------------------------------------------------------- #
# YouTube captions
# --------------------------------------------------------------------------- #

def _build_proxy_config() -> Any | None:
    if settings.webshare_proxy_username and settings.webshare_proxy_password:
        from youtube_transcript_api.proxies import WebshareProxyConfig

        return WebshareProxyConfig(
            proxy_username=settings.webshare_proxy_username,
            proxy_password=settings.webshare_proxy_password,
        )
    if settings.transcript_proxy_url:
        from youtube_transcript_api.proxies import GenericProxyConfig

        return GenericProxyConfig(
            http_url=settings.transcript_proxy_url, https_url=settings.transcript_proxy_url
        )
    return None


def _error_code_for(exc: Exception) -> str:
    name = exc.__class__.__name__
    mapping = {
        "TranscriptsDisabled": "disabled",
        "NoTranscriptFound": "not_found",
        "VideoUnavailable": "unavailable",
        "VideoUnplayable": "unavailable",
        "InvalidVideoId": "invalid_url",
        "AgeRestricted": "age_restricted",
        "RequestBlocked": "blocked",
        "IpBlocked": "blocked",
        "YouTubeRequestFailed": "blocked",
        "PoTokenRequired": "blocked",
    }
    if name in mapping:
        return mapping[name]
    text = str(exc).lower()
    if "blocked" in text or "too many requests" in text or "429" in text:
        return "blocked"
    return "unknown"


def _pick_transcript(transcript_list: Any, preferred: list[str]) -> Any:
    """Prefer creator captions in a preferred language, then auto captions, then anything."""
    available = list(transcript_list)
    if not available:
        raise TranscriptError("No captions available.", code="not_found")

    def rank(t: Any) -> tuple[int, int]:
        code = (t.language_code or "").split("-")[0].lower()
        lang_rank = preferred.index(code) if code in preferred else len(preferred)
        return (lang_rank, 1 if t.is_generated else 0)

    return sorted(available, key=rank)[0]


def fetch_transcript(youtube_url: str, languages: list[str] | None = None) -> TranscriptData:
    """
    Fetch and clean captions for a YouTube video, in whichever language exists.

    Raises TranscriptError (with a `code`) on any failure.
    """
    video_id = extract_video_id(youtube_url)
    preferred = [code.lower() for code in (languages or list(settings.transcript_languages))]

    try:
        from youtube_transcript_api import YouTubeTranscriptApi

        api = YouTubeTranscriptApi(proxy_config=_build_proxy_config())
        chosen = _pick_transcript(api.list(video_id), preferred)
        fetched = chosen.fetch()
    except TranscriptError:
        raise
    except Exception as exc:  # noqa: BLE001 - library raises many exception types
        code = _error_code_for(exc)
        raise TranscriptError(TRANSCRIPT_ERROR_HELP[code], code=code) from exc

    segments = [
        TranscriptSegment(
            text=clean_transcript_text(snippet.text),
            start=float(getattr(snippet, "start", 0.0)),
            duration=float(getattr(snippet, "duration", 0.0)),
        )
        for snippet in fetched
    ]
    segments = [s for s in segments if s.text]
    raw_text = " ".join(snippet.text for snippet in fetched)
    cleaned_text = clean_transcript_text(raw_text)
    if not cleaned_text:
        raise TranscriptError(TRANSCRIPT_ERROR_HELP["empty"], code="empty")

    duration = segments[-1].start + segments[-1].duration if segments else None

    return TranscriptData(
        video_id=video_id,
        video_url=canonical_url(video_id),
        raw_text=raw_text,
        cleaned_text=cleaned_text,
        language=getattr(chosen, "language", None) or chosen.language_code,
        language_code=chosen.language_code,
        source="youtube_generated" if chosen.is_generated else "youtube_manual",
        segments=segments,
        duration_seconds=duration,
    )


# --------------------------------------------------------------------------- #
# Transcripts from text (Gemini transcription or pasted by the user)
# --------------------------------------------------------------------------- #

def transcript_from_text(
    text: str,
    *,
    source: str,
    video_id: str | None = None,
    language: str = "Auto-detected",
    language_code: str = "",
) -> TranscriptData:
    """
    Build TranscriptData from free text. Lines starting with [mm:ss] become
    timed segments; an optional first line "LANGUAGE: Hindi (hi)" sets the language.
    """
    lines = (text or "").strip().splitlines()
    if lines:
        match = _LANGUAGE_LINE.match(lines[0])
        if match:
            language = match.group(1).strip()
            language_code = (match.group(2) or language_code).strip()
            lines = lines[1:]

    segments: list[TranscriptSegment] = []
    plain_parts: list[str] = []
    for line in lines:
        match = _TIMED_LINE.match(line)
        seconds = parse_timestamp(match.group(1)) if match else None
        if match and seconds is not None:
            body = clean_transcript_text(match.group(2))
            if body:
                segments.append(TranscriptSegment(text=body, start=float(seconds)))
                plain_parts.append(body)
        elif line.strip():
            body = clean_transcript_text(line)
            plain_parts.append(body)
            if segments:  # continuation of the previous timed line
                last = segments[-1]
                segments[-1] = TranscriptSegment(text=f"{last.text} {body}", start=last.start)

    raw_text = "\n".join(lines)
    cleaned_text = clean_transcript_text(" ".join(plain_parts))
    if len(cleaned_text.split()) < 20:
        raise TranscriptError("The transcript is too short to study from (need at least ~20 words).", code="empty")

    # Only trust timestamps if most of the text was timed.
    if segments and sum(len(s.text) for s in segments) < 0.6 * len(cleaned_text):
        segments = []
    for i in range(len(segments) - 1):
        segments[i] = TranscriptSegment(
            text=segments[i].text,
            start=segments[i].start,
            duration=max(segments[i + 1].start - segments[i].start, 0.0),
        )

    if not video_id:
        video_id = "pasted-" + hashlib.sha1(cleaned_text.encode("utf-8")).hexdigest()[:8]
        url = ""
    else:
        url = canonical_url(video_id)

    duration = segments[-1].start + 5 if segments else None

    return TranscriptData(
        video_id=video_id,
        video_url=url,
        raw_text=raw_text,
        cleaned_text=cleaned_text,
        language=language,
        language_code=language_code,
        source=source,
        segments=segments,
        duration_seconds=duration,
    )
