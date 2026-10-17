import json
import random

import pytest

from models.chat import ChatMessage
from modules.ai_service import AIService, AIServiceError, classify_error
from modules.chat_service import ChatService
from modules.flashcard_service import FlashcardService
from modules.learning_service import LearningService
from modules.quiz_service import QuizService
from modules.video_transcriber import transcribe_with_gemini
from tests.test_parsers import LEARNING_MD, QUESTION


# --------------------------------------------------------------------------- #
# AIService with a fake SDK client
# --------------------------------------------------------------------------- #

class _Resp:
    def __init__(self, text):
        self.text = text


class APIError(Exception):
    def __init__(self, code, message):
        super().__init__(f"{code} {message}")
        self.code = code


class FakeModels:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = []

    def generate_content(self, model, contents, config):
        self.calls.append({"model": model, "contents": contents, "config": config})
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return _Resp(outcome)

    def generate_content_stream(self, model, contents, config):
        self.calls.append({"model": model, "contents": contents, "config": config})
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return iter(_Resp(part) for part in outcome)


class FakeClient:
    def __init__(self, outcomes):
        self.models = FakeModels(outcomes)


def make_service(*outcomes, retries=3):
    sleeps = []
    service = AIService(model="m", client=FakeClient(outcomes), max_retries=retries, sleep=sleeps.append)
    return service, sleeps


def test_generate_retries_rate_limits_then_succeeds():
    service, sleeps = make_service(APIError(429, "RESOURCE_EXHAUSTED. Please retry in 3.5s."), APIError(503, "UNAVAILABLE"), "ok")
    assert service.generate("hi", json_mode=True) == "ok"
    assert sleeps == [3.5, 4]
    config = service._client.models.calls[-1]["config"]
    assert config == {"response_mime_type": "application/json"}  # no temperature for Gemini 3


def test_generate_gives_up_after_max_retries():
    service, sleeps = make_service(*[APIError(503, "UNAVAILABLE")] * 3, retries=2)
    with pytest.raises(AIServiceError) as info:
        service.generate("hi")
    assert info.value.code == "unavailable" and len(sleeps) == 2


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (APIError(400, "API key not valid. Please pass a valid API key. API_KEY_INVALID"), "unauthenticated"),
        (APIError(403, "PERMISSION_DENIED"), "unauthenticated"),
        (APIError(404, "models/gemini-2.0-flash is not found"), "model_not_found"),
        (APIError(429, "Quota exceeded for metric generate_content_free_tier_requests, limit: 0"), "quota_exhausted"),
        (APIError(429, "RESOURCE_EXHAUSTED GenerateRequestsPerDayPerProjectPerModel"), "quota_exhausted"),
        (APIError(429, "RESOURCE_EXHAUSTED per minute"), "rate_limited"),
        (APIError(500, "INTERNAL"), "unavailable"),
        (ValueError("something odd"), "api_error"),
    ],
)
def test_classify_error(error, code):
    assert classify_error(error)[0] == code


def test_non_retryable_error_is_raised_immediately():
    service, sleeps = make_service(APIError(404, "model not found"))
    with pytest.raises(AIServiceError) as info:
        service.generate("hi")
    assert info.value.code == "model_not_found" and sleeps == []
    assert "sidebar" in info.value.help_text


def test_empty_response_retried_once_then_raises():
    service, _ = make_service("", "")
    with pytest.raises(AIServiceError) as info:
        service.generate("hi")
    assert info.value.code == "empty_response"


def test_stream_yields_chunks_and_retries_before_first_chunk():
    service, sleeps = make_service(APIError(503, "UNAVAILABLE"), ["Hel", "lo"])
    assert "".join(service.generate_stream("hi", system_instruction="sys")) == "Hello"
    assert sleeps == [2]
    assert service._client.models.calls[-1]["config"] == {"system_instruction": "sys"}


def test_missing_key_raises(monkeypatch):
    import dataclasses

    import modules.ai_service as ai

    monkeypatch.setattr(ai, "settings", dataclasses.replace(ai.settings, gemini_api_key=""))
    with pytest.raises(AIServiceError) as info:
        AIService(api_key="   ", model="m")
    assert info.value.code == "missing_key"


def test_transcribe_youtube_sends_file_data():
    service, _ = make_service("LANGUAGE: English (en)\n[00:00] hello")
    service.transcribe_youtube_video("https://www.youtube.com/watch?v=abc", "transcribe")
    call = service._client.models.calls[-1]
    assert call["contents"][0]["parts"][0]["file_data"]["file_uri"].endswith("abc")
    assert call["config"]["media_resolution"] == "MEDIA_RESOLUTION_LOW"


# --------------------------------------------------------------------------- #
# Higher-level services with FakeAI
# --------------------------------------------------------------------------- #

def test_learning_service_uses_timestamps_and_language(transcript, fake_ai):
    ai = fake_ai(LEARNING_MD)
    content = LearningService(ai).generate_learning_content(transcript, output_language="Hindi")
    prompt = ai.prompts[0][0]
    assert "[00:35]" in prompt and "Write your entire response in Hindi" in prompt
    assert "`- [mm:ss] Chapter title`" in prompt
    assert content.chapters


def test_learning_service_retries_once_on_bad_format(transcript, fake_ai):
    ai = fake_ai("no headings here", LEARNING_MD)
    assert LearningService(ai).generate_learning_content(transcript).key_points
    assert len(ai.prompts) == 2


def test_quiz_service_shuffles_options_and_requests_json(transcript, fake_ai):
    questions = [dict(QUESTION, question=f"Q{i}") for i in range(6)]
    ai = fake_ai(json.dumps(questions))
    result = QuizService(ai, rng=random.Random(1)).generate_quiz(transcript, num_questions=5, difficulty="Hard")
    assert len(result) == 5
    assert all(q.correct_answer in q.options for q in result)
    assert ai.prompts[0][1]["json_mode"] is True
    assert "Hard" in ai.prompts[0][0]


def test_flashcard_service(transcript, fake_ai):
    cards = [{"front": f"F{i}", "back": "B", "topic": "T"} for i in range(4)]
    ai = fake_ai("garbage", json.dumps(cards))
    result = FlashcardService(ai).generate_flashcards(transcript, num_cards=3)
    assert [c.front for c in result] == ["F0", "F1", "F2"]


def test_chat_service_builds_grounded_prompt(transcript, fake_ai):
    ai = fake_ai("Lists are mutable [00:35]")
    history = [ChatMessage("user", "hi"), ChatMessage("assistant", "hello " * 400)]
    answer = "".join(ChatService(ai).stream_answer(transcript, history, "What is a list?", mode="eli5"))
    assert "[00:35]" in answer.replace(" ", "")
    prompt, kwargs = ai.prompts[0]
    assert "Student: What is a list?" in prompt and "10-year-old" in prompt
    assert "…" in prompt  # long history message truncated
    assert "Python Basics" in kwargs["system_instruction"] and "[00:35]" in kwargs["system_instruction"]


def test_suggest_questions(transcript, fake_ai):
    ai = fake_ai('{"questions": ["Why lists?", "What is a tuple?", ""]}')
    assert ChatService(ai).suggest_questions(transcript) == ["Why lists?", "What is a tuple?"]


def test_transcribe_with_gemini(fake_ai):
    words = " ".join(["word"] * 25)
    ai = fake_ai(f"LANGUAGE: English (en)\n[00:00] {words}\n[00:30] {words}")
    t = transcribe_with_gemini(ai, "https://youtu.be/dQw4w9WgXcQ")
    assert t.source == "gemini" and t.video_id == "dQw4w9WgXcQ" and len(t.segments) == 2
