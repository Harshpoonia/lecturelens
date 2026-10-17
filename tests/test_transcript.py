import pytest

from modules.transcript import TranscriptError, extract_video_id, transcript_from_text
from utils.text_cleaning import clean_transcript_text, strip_markdown, truncate_text
from utils.text_statistics import reading_time, speaking_pace, top_terms
from utils.time_utils import find_timestamps, format_timestamp, linkify_timestamps, parse_timestamp

VID = "dQw4w9WgXcQ"


@pytest.mark.parametrize(
    "url",
    [
        f"https://www.youtube.com/watch?v={VID}",
        f"https://youtube.com/watch?feature=share&v={VID}&t=42s",
        f"https://m.youtube.com/watch?v={VID}",
        f"https://youtu.be/{VID}?si=abc",
        f"https://www.youtube.com/shorts/{VID}",
        f"https://www.youtube.com/embed/{VID}",
        f"https://www.youtube.com/live/{VID}?feature=share",
        f"youtube.com/watch?v={VID}",
        VID,
    ],
)
def test_extract_video_id(url):
    assert extract_video_id(url) == VID


@pytest.mark.parametrize("url", ["", "https://vimeo.com/123456", "https://www.youtube.com/channel/abc", "hello"])
def test_extract_video_id_rejects(url):
    with pytest.raises(TranscriptError) as info:
        extract_video_id(url)
    assert info.value.code == "invalid_url"
    assert not info.value.can_use_gemini_fallback


def test_transcript_from_gemini_text_parses_language_and_timestamps():
    words = " ".join(["word"] * 12)
    raw = f"LANGUAGE: Hindi (hi)\n[00:00] namaste {words}\n[00:31] doosra hissa {words}\ncontinued line\n[1:02:03] end {words}"
    t = transcript_from_text(raw, source="gemini", video_id=VID)
    assert t.language == "Hindi" and t.language_code == "hi"
    assert [s.start for s in t.segments] == [0, 31, 3723]
    assert "continued line" in t.segments[1].text
    assert t.segments[0].duration == 31
    assert t.video_url.endswith(VID) and t.is_youtube


def test_transcript_from_pasted_text_without_timestamps():
    t = transcript_from_text("This is a pasted lecture transcript " * 5, source="manual")
    assert not t.has_timestamps and not t.is_youtube
    assert t.video_id.startswith("pasted-")
    assert t.display_title == "Pasted transcript"


def test_transcript_too_short():
    with pytest.raises(TranscriptError):
        transcript_from_text("too short", source="manual")


def test_timestamped_text_markers(transcript):
    text = transcript.timestamped_text(block_seconds=30)
    assert text.startswith("[00:00]")
    assert "[00:35]" in text and "[01:10]" in text
    assert "[00:04]" not in text  # within the first 30s block


def test_transcript_properties(transcript):
    assert transcript.word_count == len(transcript.cleaned_text.split())
    assert transcript.reading_time_minutes == 1
    assert transcript.speaking_wpm == round(transcript.word_count / (75 / 60))
    assert len(transcript.content_hash) == 16


def test_time_utils():
    assert format_timestamp(65) == "01:05"
    assert format_timestamp(3723) == "1:02:03"
    assert parse_timestamp("[05:32]") == 332
    assert parse_timestamp("1:02:03") == 3723
    assert parse_timestamp("5:99") is None
    assert find_timestamps("see [00:35] and [01:10], again [00:35]") == [35, 70]
    linked = linkify_timestamps("at [00:35] and [99:00]", VID, max_seconds=75)
    assert f"[00:35](https://www.youtube.com/watch?v={VID}&t=35s)" in linked
    assert "[99:00]" in linked and "t=5940s" not in linked


def test_text_helpers():
    assert clean_transcript_text("[Music] hello &amp;   world [Applause] [x] ") == "hello & world [x]"
    assert truncate_text("one two three", 9) == "one two"
    plain = strip_markdown("# Title\n\n- **Bold** point [00:12]\n- [link](http://x)")
    assert "#" not in plain and "**" not in plain and "link" in plain and "00:12" not in plain
    assert reading_time("word " * 401) == 3
    assert speaking_pace(300, 120) == 150 and speaking_pace(10, None) is None
    assert top_terms("python python lists lists lists the and")[0] == ("lists", 3)


def test_hero_title_split():
    pytest.importorskip("streamlit")
    from ui.home import _split_title

    assert _split_title("LectureLens") == ("Lecture", "Lens")
    assert _split_title("Study Stream") == ("Study ", "Stream")
    assert _split_title("Lecturely") == ("Lecturely", "")
