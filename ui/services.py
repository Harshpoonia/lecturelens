"""
ui/services.py

Wires the Streamlit session to the business services, with caching:

- Clients are cached per (api key, model) with st.cache_resource.
- Transcripts and AI output are cached with st.cache_data, keyed by the
  transcript's content hash + generation settings. Re-opening a video or
  switching tabs never re-bills the Gemini API.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace

import streamlit as st

from config import settings
from models.flashcard import Flashcard
from models.learning_content import LearningContent
from models.quiz import QuizQuestion
from models.transcript import TranscriptData
from modules.ai_service import AIService, AIServiceError
from modules.chat_service import ChatService
from modules.flashcard_service import FlashcardService
from modules.learning_service import LearningService
from modules.quiz_service import QuizService
from modules.transcript import fetch_transcript
from modules.tts_service import synthesize
from modules.video_transcriber import transcribe_with_gemini
from modules.youtube import VideoMetadata, fetch_video_metadata

TTL = settings.cache_ttl_seconds


@dataclass(frozen=True)
class AIConfig:
    api_key: str
    model: str
    output_language: str
    uses_own_key: bool


# --------------------------------------------------------------------------- #
# Clients and quota guard
# --------------------------------------------------------------------------- #

@st.cache_resource(show_spinner=False, max_entries=32)
def _ai_client(api_key: str, model: str) -> AIService:
    return AIService(api_key=api_key, model=model)


def get_ai(cfg: AIConfig) -> AIService:
    if not cfg.api_key:
        raise AIServiceError("No Gemini API key configured.", code="missing_key")
    return _ai_client(cfg.api_key, cfg.model)


def check_quota(cfg: AIConfig) -> None:
    """Per-session cap on AI calls when the app's own key pays for them."""
    limit = settings.session_ai_call_limit
    if cfg.uses_own_key or limit <= 0:
        return
    if st.session_state.ai_calls >= limit:
        raise AIServiceError(
            f"This demo allows {limit} AI requests per session on the shared key.",
            code="quota_exhausted",
        )
    st.session_state.ai_calls += 1


# --------------------------------------------------------------------------- #
# Transcript sources
# --------------------------------------------------------------------------- #

@st.cache_data(ttl=TTL, show_spinner=False, max_entries=64)
def cached_transcript(url: str, languages: tuple[str, ...]) -> TranscriptData:
    return fetch_transcript(url, list(languages))


@st.cache_data(ttl=TTL, show_spinner=False, max_entries=128)
def cached_metadata(video_id: str) -> VideoMetadata:
    return fetch_video_metadata(video_id)


@st.cache_data(ttl=TTL, show_spinner=False, max_entries=32)
def _cached_gemini_transcript(video_id: str, model: str, _ai: AIService) -> TranscriptData:
    return transcribe_with_gemini(_ai, f"https://www.youtube.com/watch?v={video_id}")


def gemini_transcript(cfg: AIConfig, video_id: str) -> TranscriptData:
    check_quota(cfg)
    return _cached_gemini_transcript(video_id, cfg.model, get_ai(cfg))


def with_metadata(transcript: TranscriptData) -> TranscriptData:
    if not transcript.is_youtube:
        return transcript
    meta = cached_metadata(transcript.video_id)
    return replace(transcript, title=meta.title or transcript.title, channel=meta.channel or transcript.channel)


# --------------------------------------------------------------------------- #
# Generations
# --------------------------------------------------------------------------- #

@st.cache_data(ttl=TTL, show_spinner=False, max_entries=64)
def _cached_learning(
    content_hash: str, model: str, language: str, nonce: int, _ai: AIService, _t: TranscriptData
) -> LearningContent:
    return LearningService(_ai).generate_learning_content(_t, output_language=language)


@st.cache_data(ttl=TTL, show_spinner=False, max_entries=64)
def _cached_quiz(
    content_hash: str, model: str, language: str, n: int, difficulty: str, nonce: int,
    _ai: AIService, _t: TranscriptData,
) -> list[QuizQuestion]:
    return QuizService(_ai).generate_quiz(_t, num_questions=n, difficulty=difficulty, output_language=language)


@st.cache_data(ttl=TTL, show_spinner=False, max_entries=64)
def _cached_flashcards(
    content_hash: str, model: str, language: str, n: int, nonce: int, _ai: AIService, _t: TranscriptData
) -> list[Flashcard]:
    return FlashcardService(_ai).generate_flashcards(_t, num_cards=n, output_language=language)


@st.cache_data(ttl=TTL, show_spinner=False, max_entries=64)
def _cached_suggestions(content_hash: str, model: str, language: str, _ai: AIService, _t: TranscriptData) -> list[str]:
    return ChatService(_ai).suggest_questions(_t, output_language=language)


@st.cache_data(ttl=TTL, show_spinner=False, max_entries=64)
def cached_tts(text_hash: str, language_code: str, _text: str) -> bytes:
    return synthesize(_text, language_code)


def learning_content(cfg: AIConfig, t: TranscriptData, nonce: int = 0) -> LearningContent:
    check_quota(cfg)
    return _cached_learning(t.content_hash, cfg.model, cfg.output_language, nonce, get_ai(cfg), t)


def quiz(cfg: AIConfig, t: TranscriptData, n: int, difficulty: str, nonce: int) -> list[QuizQuestion]:
    check_quota(cfg)
    questions = _cached_quiz(t.content_hash, cfg.model, cfg.output_language, n, difficulty, nonce, get_ai(cfg), t)
    return [replace(q, options=list(q.options)) for q in questions]


def flashcards(cfg: AIConfig, t: TranscriptData, n: int, nonce: int) -> list[Flashcard]:
    check_quota(cfg)
    return list(_cached_flashcards(t.content_hash, cfg.model, cfg.output_language, n, nonce, get_ai(cfg), t))


def suggested_questions(cfg: AIConfig, t: TranscriptData) -> list[str]:
    check_quota(cfg)
    return _cached_suggestions(t.content_hash, cfg.model, cfg.output_language, get_ai(cfg), t)


def chat_service(cfg: AIConfig) -> ChatService:
    check_quota(cfg)
    return ChatService(get_ai(cfg))


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
