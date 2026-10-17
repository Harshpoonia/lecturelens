import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.transcript import TranscriptData, TranscriptSegment  # noqa: E402


class FakeAI:
    """Stands in for AIService: returns queued responses and records prompts."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.prompts = []
        self.model = "fake-model"

    def _next(self):
        value = self.responses.pop(0)
        if isinstance(value, Exception):
            raise value
        return value

    def generate(self, prompt, **kwargs):
        self.prompts.append((prompt, kwargs))
        return self._next()

    def generate_stream(self, prompt, **kwargs):
        self.prompts.append((prompt, kwargs))
        yield from self._next().split(" ")

    def transcribe_youtube_video(self, url, prompt):
        self.prompts.append((url, prompt))
        return self._next()


@pytest.fixture
def transcript():
    segments = [
        TranscriptSegment("Python is an interpreted programming language.", 0.0, 4.0),
        TranscriptSegment("It is widely used in AI and data science.", 4.0, 4.0),
        TranscriptSegment("Lists store ordered items and are mutable.", 35.0, 5.0),
        TranscriptSegment("Tuples are like lists but immutable.", 70.0, 5.0),
    ]
    text = " ".join(s.text for s in segments)
    return TranscriptData(
        video_id="dQw4w9WgXcQ",
        video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        raw_text=text,
        cleaned_text=text,
        language="English",
        language_code="en",
        source="youtube_manual",
        segments=segments,
        duration_seconds=75.0,
        title="Python Basics",
    )


@pytest.fixture
def fake_ai():
    return FakeAI
