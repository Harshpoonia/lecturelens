"""
modules/ai_service.py

AIService is the single point of contact with the Gemini API.

Responsible for:
- Creating the Gemini client (server key or the visitor's own key)
- Sending prompts (plain, JSON mode, streaming, YouTube video input)
- Retrying transient failures (rate limits, 5xx) with backoff
- Translating SDK exceptions into AIServiceError with a stable `code`

It knows nothing about quizzes, flashcards or notes. Higher-level
services build prompts and parse responses.
"""

from __future__ import annotations

import logging
import re
import time
from collections.abc import Callable, Iterator
from typing import Any

from config import settings

logger = logging.getLogger(__name__)

RETRYABLE_CODES = {"rate_limited", "unavailable"}

ERROR_HELP = {
    "missing_key": (
        "Gemini API key needed",
        "Add your key in the sidebar (get one free at aistudio.google.com/apikey), "
        "or set GEMINI_API_KEY in .env / Streamlit secrets.",
    ),
    "unauthenticated": (
        "Gemini rejected the API key",
        "Check that the key is correct and active in Google AI Studio. Keys that were "
        "shared publicly are often revoked automatically.",
    ),
    "model_not_found": (
        "Model not available",
        "This model ID was retired or isn't enabled for your key. Pick another model in "
        "the sidebar (gemini-3.5-flash is the current default).",
    ),
    "quota_exhausted": (
        "Gemini quota exhausted",
        "Your daily or per-model quota is used up. Try a lighter model such as "
        "gemini-3.1-flash-lite, wait for the quota to reset, or enable billing.",
    ),
    "rate_limited": (
        "Gemini is rate-limiting requests",
        "Too many requests in a short time. Wait a minute and try again.",
    ),
    "unavailable": (
        "Gemini is temporarily unavailable",
        "Google's servers are overloaded or timed out. Please retry shortly.",
    ),
    "blocked": (
        "Response blocked",
        "Gemini declined to answer this content because of its safety filters.",
    ),
    "empty_response": (
        "Gemini returned no content",
        "The model sent back an empty answer. Please retry.",
    ),
    "api_error": (
        "AI generation error",
        "Something went wrong while generating content. Please retry.",
    ),
}


class AIServiceError(Exception):
    """Raised when a Gemini call fails. `code` is one of ERROR_HELP's keys."""

    def __init__(self, message: str, code: str = "api_error", retry_after: float | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.retry_after = retry_after

    @property
    def title(self) -> str:
        return ERROR_HELP.get(self.code, ERROR_HELP["api_error"])[0]

    @property
    def help_text(self) -> str:
        return ERROR_HELP.get(self.code, ERROR_HELP["api_error"])[1]


def classify_error(exc: Exception) -> tuple[str, float | None]:
    """Map an SDK exception to (error code, suggested retry delay in seconds)."""
    message = str(exc) or exc.__class__.__name__
    lower = message.lower()
    status_code = getattr(exc, "code", None)
    if not isinstance(status_code, int):
        match = re.match(r"^\s*(\d{3})\b", message)
        status_code = int(match.group(1)) if match else None

    retry_after = _parse_retry_delay(message)

    if "api_key_invalid" in lower or "api key not valid" in lower or "api key expired" in lower:
        return "unauthenticated", None
    if status_code in (401, 403) or "unauthenticated" in lower or "permission_denied" in lower:
        return "unauthenticated", None
    if status_code == 404 or ("not found" in lower and "model" in lower):
        return "model_not_found", None
    if status_code == 429 or "resource_exhausted" in lower or "quota" in lower:
        if "perday" in lower or "per day" in lower or "limit: 0" in lower or "daily" in lower:
            return "quota_exhausted", None
        return "rate_limited", retry_after
    if status_code in (500, 502, 503, 504) or any(
        word in lower for word in ("unavailable", "overloaded", "deadline", "timed out", "timeout")
    ):
        return "unavailable", retry_after
    return "api_error", None


def _parse_retry_delay(message: str) -> float | None:
    match = re.search(r"retry(?:delay)?['\"]?\s*(?:in|:)\s*['\"]?([\d.]+)\s*s", message, re.I)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None


class AIService:
    """Thin wrapper around the Gemini API for text generation."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        max_retries: int | None = None,
        client: Any | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.model = model or settings.gemini_model
        self.max_retries = settings.ai_max_retries if max_retries is None else max_retries
        self._sleep = sleep

        if client is not None:
            self._client = client
            return

        key = (api_key or settings.gemini_api_key or "").strip()
        if not key:
            raise AIServiceError("No Gemini API key configured.", code="missing_key")

        from google import genai  # imported lazily so the rest of the app is testable without the SDK

        self._client = genai.Client(api_key=key)

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def generate(
        self,
        prompt: str | list[Any],
        *,
        json_mode: bool = False,
        temperature: float | None = None,
        system_instruction: str | None = None,
        extra_config: dict[str, Any] | None = None,
    ) -> str:
        """Send a prompt and return the full response text."""
        config = self._build_config(json_mode, temperature, system_instruction, extra_config)

        def _call() -> str:
            response = self._client.models.generate_content(
                model=self.model, contents=prompt, config=config or None
            )
            return self._extract_text(response)

        return self._with_retries(_call)

    def generate_stream(
        self,
        prompt: str | list[Any],
        *,
        temperature: float | None = None,
        system_instruction: str | None = None,
    ) -> Iterator[str]:
        """
        Stream response text chunk by chunk.

        Retries only happen before the first chunk arrives, so a user never
        sees a duplicated half-answer.
        """
        config = self._build_config(False, temperature, system_instruction, None)

        def _open() -> tuple[Any, Iterator[Any]]:
            stream = self._client.models.generate_content_stream(
                model=self.model, contents=prompt, config=config or None
            )
            iterator = iter(stream)
            return next(iterator, None), iterator

        first, iterator = self._with_retries(_open)
        produced = False
        try:
            chunks = iterator if first is None else _prepend(first, iterator)
            for chunk in chunks:
                text = getattr(chunk, "text", None)
                if text:
                    produced = True
                    yield text
        except AIServiceError:
            raise
        except Exception as exc:  # noqa: BLE001
            code, _ = classify_error(exc)
            raise AIServiceError(f"Gemini stream failed: {exc}", code=code) from exc

        if not produced:
            raise AIServiceError("Gemini returned an empty response.", code="empty_response")

    def transcribe_youtube_video(self, youtube_url: str, prompt: str) -> str:
        """
        Ask Gemini to watch a public YouTube video and transcribe it.

        Fallback for when YouTube blocks caption downloads from the server
        (common on cloud hosts). Uses low media resolution to cut token use.
        """
        contents = [
            {
                "role": "user",
                "parts": [
                    {"file_data": {"file_uri": youtube_url, "mime_type": "video/*"}},
                    {"text": prompt},
                ],
            }
        ]
        return self.generate(contents, extra_config={"media_resolution": "MEDIA_RESOLUTION_LOW"})

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #

    @staticmethod
    def _build_config(
        json_mode: bool,
        temperature: float | None,
        system_instruction: str | None,
        extra_config: dict[str, Any] | None,
    ) -> dict[str, Any]:
        # Gemini 3 models are tuned for the default temperature (1.0), so we
        # only send one when a caller explicitly asks for it.
        config: dict[str, Any] = {}
        if temperature is not None:
            config["temperature"] = temperature
        if json_mode:
            config["response_mime_type"] = "application/json"
        if system_instruction:
            config["system_instruction"] = system_instruction
        if extra_config:
            config.update(extra_config)
        return config

    @staticmethod
    def _extract_text(response: Any) -> str:
        text = getattr(response, "text", None)
        if text:
            return text

        feedback = getattr(response, "prompt_feedback", None)
        if feedback is not None and getattr(feedback, "block_reason", None):
            raise AIServiceError(f"Prompt blocked: {feedback.block_reason}", code="blocked")

        candidates = getattr(response, "candidates", None) or []
        if candidates:
            reason = str(getattr(candidates[0], "finish_reason", "") or "")
            if "SAFETY" in reason or "PROHIBITED" in reason:
                raise AIServiceError(f"Response blocked ({reason}).", code="blocked")

        raise AIServiceError("Gemini returned an empty response.", code="empty_response")

    def _with_retries(self, func: Callable[[], Any]) -> Any:
        attempt = 0
        while True:
            try:
                return func()
            except AIServiceError as exc:
                if exc.code == "empty_response" and attempt < min(self.max_retries, 1):
                    attempt += 1
                    continue
                raise
            except Exception as exc:  # noqa: BLE001 - surface as a domain error
                code, retry_after = classify_error(exc)
                if code in RETRYABLE_CODES and attempt < self.max_retries:
                    delay = min(retry_after or 2 ** (attempt + 1), 30.0)
                    logger.warning("Gemini %s (attempt %d), retrying in %.1fs", code, attempt + 1, delay)
                    self._sleep(delay)
                    attempt += 1
                    continue
                raise AIServiceError(_short(exc), code=code, retry_after=retry_after) from exc


def _prepend(first: Any, rest: Iterator[Any]) -> Iterator[Any]:
    yield first
    yield from rest


def _short(exc: Exception, limit: int = 400) -> str:
    message = " ".join(str(exc).split())
    return message if len(message) <= limit else message[:limit] + "…"
