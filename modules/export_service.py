"""
modules/export_service.py

Builds downloadable study material:
- Study pack as Markdown, printable HTML, and PDF
- Flashcards as an Anki-importable TSV
- Quiz report, chat transcript, transcript as TXT / SRT

Pure functions over models; no Streamlit, no network.
"""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from models.chat import ChatMessage
from models.flashcard import Flashcard
from models.learning_content import LearningContent
from models.quiz import QuizAnswer, QuizQuestion
from models.transcript import TranscriptData
from utils.time_utils import format_timestamp, youtube_link


@dataclass
class StudyPack:
    transcript: TranscriptData
    learning: LearningContent | None = None
    quiz: list[QuizQuestion] = field(default_factory=list)
    quiz_answers: list[QuizAnswer] = field(default_factory=list)
    flashcards: list[Flashcard] = field(default_factory=list)
    chat: list[ChatMessage] = field(default_factory=list)


def safe_filename(name: str, default: str = "study-pack") -> str:
    slug = re.sub(r"[^\w\s-]", "", name or "").strip().lower()
    slug = re.sub(r"[\s_-]+", "-", slug)[:60].strip("-")
    return slug or default


# --------------------------------------------------------------------------- #
# Markdown
# --------------------------------------------------------------------------- #

def _video_header(t: TranscriptData) -> list[str]:
    lines = [f"# {t.display_title}", ""]
    if t.channel:
        lines.append(f"**Channel:** {t.channel}  ")
    if t.video_url:
        lines.append(f"**Video:** {t.video_url}  ")
    meta = [f"**Language:** {t.language}", f"**Words:** {t.word_count:,}"]
    if t.duration_seconds:
        meta.append(f"**Duration:** {format_timestamp(t.duration_seconds)}")
    lines.append(" · ".join(meta) + "  ")
    lines.append(f"*Generated {datetime.now():%d %b %Y} with LectureLens*")
    lines.append("")
    return lines


def study_pack_markdown(pack: StudyPack, include_quiz: bool = True, include_flashcards: bool = True) -> str:
    t = pack.transcript
    lines = _video_header(t)

    if pack.learning:
        lc = pack.learning
        for title, body in lc.as_dict().items():
            lines += [f"## {title}", "", _demote_headings(body), ""]
        if lc.chapters:
            lines += ["## Video Chapters", ""]
            for chapter in lc.chapters:
                stamp = format_timestamp(chapter.seconds)
                if t.is_youtube:
                    lines.append(f"- [{stamp}]({youtube_link(t.video_id, chapter.seconds)}) {chapter.title}")
                else:
                    lines.append(f"- {stamp} {chapter.title}")
            lines.append("")

    if include_quiz and pack.quiz:
        lines += ["## Practice Quiz", ""]
        for i, q in enumerate(pack.quiz, 1):
            lines.append(f"**{i}. {q.question}**")
            lines.append("")
            for letter, option in zip("ABCD", q.options):
                lines.append(f"- {letter}) {option}")
            lines.append("")
        lines += ["### Answer Key", ""]
        for i, q in enumerate(pack.quiz, 1):
            letter = "ABCD"[q.options.index(q.correct_answer)] if q.correct_answer in q.options else "?"
            lines.append(f"{i}. **{letter}) {q.correct_answer}** — {q.explanation}")
        lines.append("")

    if include_flashcards and pack.flashcards:
        lines += ["## Flashcards", "", "| Front | Back | Topic |", "|---|---|---|"]
        for card in pack.flashcards:
            lines.append(f"| {_cell(card.front)} | {_cell(card.back)} | {_cell(card.topic)} |")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def _demote_headings(markdown: str) -> str:
    """Shift nested headings down one level so they sit under the section's ##."""
    return re.sub(r"^(#{2,5})(\s)", r"#\1\2", markdown, flags=re.M)


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


# --------------------------------------------------------------------------- #
# HTML (printable; "Save as PDF" from the browser gives perfect Unicode output)
# --------------------------------------------------------------------------- #

_HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/marked/12.0.2/marked.min.js"></script>
<style>
  :root {{ --ink:#1f2328; --muted:#59636e; --line:#d8dee4; --accent:#e5484d; }}
  body {{ font: 16px/1.65 -apple-system, "Segoe UI", Roboto, "Noto Sans", "Noto Sans Devanagari", sans-serif;
         color: var(--ink); max-width: 820px; margin: 40px auto; padding: 0 20px; }}
  h1 {{ font-size: 1.9rem; line-height: 1.25; border-bottom: 3px solid var(--accent); padding-bottom: .4rem; }}
  h2 {{ margin-top: 2.2rem; border-bottom: 1px solid var(--line); padding-bottom: .25rem; }}
  table {{ border-collapse: collapse; width: 100%; font-size: .92rem; }}
  th, td {{ border: 1px solid var(--line); padding: 6px 10px; text-align: left; vertical-align: top; }}
  th {{ background: #f6f8fa; }}
  a {{ color: #0969da; }}
  code {{ background:#f6f8fa; padding: 1px 5px; border-radius: 4px; }}
  .print-hint {{ background:#fff8c5; border:1px solid #d4a72c; padding:8px 12px; border-radius:6px; font-size:.9rem; }}
  @media print {{ .print-hint {{ display:none; }} body {{ margin: 0 auto; }} h2 {{ break-after: avoid; }} }}
</style>
</head>
<body>
<p class="print-hint">Tip: press Ctrl/Cmd + P and choose “Save as PDF” to keep a copy.</p>
<div id="content"></div>
<script id="md" type="text/markdown">{markdown}</script>
<noscript><pre>{markdown}</pre></noscript>
<script>
  const src = document.getElementById('md').textContent;
  document.getElementById('content').innerHTML = window.marked ? marked.parse(src) : '<pre>' + src + '</pre>';
</script>
</body>
</html>
"""


def study_pack_html(pack: StudyPack) -> str:
    markdown = study_pack_markdown(pack)
    # Neutralise any closing script tag inside the content.
    safe_markdown = markdown.replace("</script", "<\\/script")
    return _HTML_TEMPLATE.format(title=html.escape(pack.transcript.display_title), markdown=safe_markdown)


# --------------------------------------------------------------------------- #
# PDF (fpdf2)
# --------------------------------------------------------------------------- #

_FONT_CANDIDATES = (
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ("/usr/share/fonts/dejavu/DejaVuSans.ttf", "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"),
    ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
    ("/Library/Fonts/Arial Unicode.ttf", "/Library/Fonts/Arial Unicode.ttf"),
)


def study_pack_pdf(pack: StudyPack) -> bytes | None:
    """
    Render the study pack as PDF. Returns None if fpdf2 is not installed.

    Uses DejaVu Sans when present (installed via packages.txt / Dockerfile)
    for wide Unicode coverage; otherwise falls back to Helvetica with
    non-Latin-1 characters replaced. For scripts like Devanagari, the HTML
    export printed from a browser gives the best result.
    """
    try:
        from fpdf import FPDF
    except ImportError:
        return None

    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.set_margins(18, 18, 18)
    pdf.set_title(pack.transcript.display_title[:120])
    pdf.set_creator("LectureLens")

    family, unicode_ok = "Helvetica", False
    for regular, bold in _FONT_CANDIDATES:
        if Path(regular).exists() and Path(bold).exists():
            pdf.add_font("Body", "", regular)
            pdf.add_font("Body", "B", bold)
            family, unicode_ok = "Body", True
            break

    def clean(text: str) -> str:
        text = text.replace("--", "–")
        if not unicode_ok:
            text = text.replace("•", "-").replace("–", "-").replace("—", "-").replace("’", "'")
            text = text.replace("“", '"').replace("”", '"')
            text = text.encode("latin-1", "replace").decode("latin-1")
        return text

    def write(text: str, size: float = 11, height: float = 6, bold: bool = False, indent: float = 0) -> None:
        pdf.set_font(family, "B" if bold else "", size)
        pdf.set_x(pdf.l_margin + indent)
        width = pdf.w - pdf.r_margin - pdf.l_margin - indent
        try:
            pdf.multi_cell(width, height, clean(text), markdown=True, new_x="LMARGIN", new_y="NEXT")
        except Exception:  # noqa: BLE001 - e.g. an unbreakable long URL
            pdf.set_x(pdf.l_margin + indent)
            pdf.multi_cell(width, height, clean(re.sub(r"\*\*", "", text)), wrapmode="CHAR",
                           new_x="LMARGIN", new_y="NEXT")

    pdf.add_page()
    bullet = "•" if unicode_ok else "-"
    for line in study_pack_markdown(pack).splitlines():
        stripped = line.strip()
        if not stripped:
            pdf.ln(2.5)
            continue
        if stripped.startswith("|---"):
            continue
        heading = re.match(r"^(#{1,6})\s+(.*)", stripped)
        if heading:
            level = len(heading.group(1))
            size = {1: 19, 2: 15, 3: 12.5}.get(level, 11.5)
            pdf.ln(3 if level > 1 else 0)
            write(heading.group(2).replace("**", ""), size=size, height=size * 0.55, bold=True)
            if level <= 2:
                y = pdf.get_y() + 0.5
                pdf.set_draw_color(229, 72, 77) if level == 1 else pdf.set_draw_color(210, 214, 220)
                pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
                pdf.ln(2.5)
            continue
        indent_level = (len(line) - len(line.lstrip(" "))) // 2
        bullet_match = re.match(r"^[-*+]\s+(.*)", stripped)
        if bullet_match:
            write(f"{bullet} {bullet_match.group(1)}", indent=4 + 5 * indent_level)
            continue
        if stripped.startswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            write("  ·  ".join(cells), size=10, height=5.5, indent=2)
            continue
        write(stripped.rstrip("\\").rstrip())

    output = pdf.output()
    return bytes(output)


# --------------------------------------------------------------------------- #
# Smaller exports
# --------------------------------------------------------------------------- #

def flashcards_anki_tsv(cards: list[Flashcard]) -> str:
    """Tab-separated Front/Back/Tags — import into Anki via File → Import."""
    lines = ["#separator:tab", "#html:false", "#columns:Front\tBack\tTags"]
    for card in cards:
        tag = re.sub(r"\s+", "_", card.topic.strip()) or "General"
        lines.append(f"{_tsv(card.front)}\t{_tsv(card.back)}\t{_tsv(tag)}")
    return "\n".join(lines) + "\n"


def _tsv(text: str) -> str:
    return " ".join(text.replace("\t", " ").split())


def flashcards_json(cards: list[Flashcard]) -> str:
    return json.dumps([card.__dict__ for card in cards], ensure_ascii=False, indent=2)


def quiz_report_markdown(transcript: TranscriptData, questions: list[QuizQuestion], answers: list[QuizAnswer]) -> str:
    answered = {a.question_index: a for a in answers}
    correct = sum(1 for a in answers if a.is_correct)
    lines = [
        f"# Quiz Report — {transcript.display_title}",
        "",
        f"**Score:** {correct} / {len(questions)}"
        + (f" ({round(100 * correct / len(questions))}%)" if questions else ""),
        "",
    ]
    for i, q in enumerate(questions):
        answer = answered.get(i)
        status = "✅" if answer and answer.is_correct else ("❌" if answer else "⏭️ not answered")
        lines.append(f"### {i + 1}. {q.question} {status}")
        if answer:
            lines.append(f"- Your answer: {answer.selected_option}")
        lines.append(f"- Correct answer: **{q.correct_answer}**")
        if q.explanation:
            lines.append(f"- Why: {q.explanation}")
        if q.timestamp_seconds is not None and transcript.is_youtube:
            lines.append(f"- Review: [{format_timestamp(q.timestamp_seconds)}]({youtube_link(transcript.video_id, q.timestamp_seconds)})")
        lines.append("")
    return "\n".join(lines)


def chat_markdown(transcript: TranscriptData, messages: list[ChatMessage]) -> str:
    lines = [f"# Chat — {transcript.display_title}", ""]
    for message in messages:
        speaker = "**You**" if message.role == "user" else "**AI Tutor**"
        lines += [speaker, "", message.content, ""]
    return "\n".join(lines)


def transcript_txt(transcript: TranscriptData) -> str:
    if not transcript.segments:
        return transcript.cleaned_text + "\n"
    return "\n".join(f"[{format_timestamp(s.start)}] {s.text}" for s in transcript.segments) + "\n"


def transcript_srt(transcript: TranscriptData) -> str | None:
    if not transcript.segments:
        return None

    def stamp(seconds: float) -> str:
        ms = int(round(seconds * 1000))
        h, rem = divmod(ms, 3_600_000)
        m, rem = divmod(rem, 60_000)
        s, ms = divmod(rem, 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    blocks = []
    for i, seg in enumerate(transcript.segments, 1):
        end = seg.start + (seg.duration or 3.0)
        blocks.append(f"{i}\n{stamp(seg.start)} --> {stamp(end)}\n{seg.text}\n")
    return "\n".join(blocks)
