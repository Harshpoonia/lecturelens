"""
modules/video_transcriber.py

Fallback transcript source: Gemini watches the public YouTube video and
transcribes it. Used when YouTube blocks caption downloads from the
server (very common on Streamlit Cloud, Render, Railway, etc.) or the
video has no captions at all.
"""

from __future__ import annotations

from models.transcript import TranscriptData
from modules.ai_service import AIService
from modules.transcript import canonical_url, extract_video_id, transcript_from_text
from utils.prompt_loader import load_prompt


def transcribe_with_gemini(ai_service: AIService, youtube_url: str) -> TranscriptData:
    video_id = extract_video_id(youtube_url)
    raw = ai_service.transcribe_youtube_video(
        canonical_url(video_id), load_prompt("video_transcription_prompt.txt")
    )
    return transcript_from_text(raw, source="gemini", video_id=video_id)
