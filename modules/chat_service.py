"""
modules/chat_service.py

"Chat with the video": multi-turn, transcript-grounded tutoring with
timestamp citations, tutor modes and suggested questions.
"""

from __future__ import annotations

from collections.abc import Iterator

from config import settings
from models.chat import ChatMessage
from models.transcript import TranscriptData
from modules.ai_service import AIService
from utils.json_utils import extract_json_list
from utils.prompt_loader import language_instruction, load_prompt, load_prompt_json

MAX_HISTORY_MESSAGES = 10
MAX_HISTORY_CHARS_PER_MESSAGE = 1500


def chat_modes() -> dict[str, dict[str, str]]:
    """Tutor modes: key -> {label, instruction}."""
    return load_prompt_json("chat_modes.json")


class ChatService:
    def __init__(self, ai_service: AIService) -> None:
        self._ai = ai_service

    def _system_prompt(self, transcript: TranscriptData, output_language: str) -> str:
        return load_prompt(
            "chat_system_prompt.txt",
            title=transcript.display_title,
            transcript=transcript.timestamped_text(settings.max_transcript_chars),
            language_instruction=language_instruction(output_language),
        )

    @staticmethod
    def build_turn_prompt(history: list[ChatMessage], question: str, mode: str = "ask") -> str:
        modes = chat_modes()
        mode_instruction = modes.get(mode, modes["ask"])["instruction"]

        recent = history[-MAX_HISTORY_MESSAGES:]
        lines = []
        for message in recent:
            speaker = "Student" if message.role == "user" else "Tutor"
            content = message.content
            if len(content) > MAX_HISTORY_CHARS_PER_MESSAGE:
                content = content[:MAX_HISTORY_CHARS_PER_MESSAGE] + " …"
            lines.append(f"{speaker}: {content}")

        return load_prompt(
            "chat_turn_prompt.txt",
            history="\n".join(lines) if lines else "(this is the first question)",
            mode_instruction=mode_instruction,
            question=question.strip(),
        )

    def stream_answer(
        self,
        transcript: TranscriptData,
        history: list[ChatMessage],
        question: str,
        mode: str = "ask",
        output_language: str = "",
    ) -> Iterator[str]:
        return self._ai.generate_stream(
            self.build_turn_prompt(history, question, mode),
            system_instruction=self._system_prompt(transcript, output_language),
        )

    def suggest_questions(
        self, transcript: TranscriptData, num_questions: int = 4, output_language: str = ""
    ) -> list[str]:
        prompt = load_prompt(
            "suggested_questions_prompt.txt",
            transcript=transcript.timestamped_text(min(settings.max_transcript_chars, 60_000)),
            num_questions=num_questions,
            language_instruction=language_instruction(output_language),
        )
        items = extract_json_list(self._ai.generate(prompt, json_mode=True), ("questions",))
        questions = [str(item).strip() for item in items if str(item).strip()]
        return questions[:num_questions]
