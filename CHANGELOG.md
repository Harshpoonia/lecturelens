# Changelog

## v3.0.0 — 2026-10-17

### Renamed
- The product is now **LectureLens — AI Video Learning Platform** (was "YouTube AI Learning Assistant").

### Fixed (from the code audit)
- **Every Gemini call failed**: the default model `gemini-2.0-flash` was retired on 2026-06-01 (and `gemini-2.5-flash` on 2026-10-16). Default is now `gemini-3.5-flash`, with a model picker and a clear "model not available" error.
- **App crashed at import without a key** (`config.py` raised). It now starts and asks for a key; Streamlit Cloud secrets are supported.
- **Non-English videos failed**: captions were requested in English only. Any language now works, ranked by preference.
- **Error classification bugs**: `unauthenticated` was never produced, empty responses got the wrong code, case-sensitive matching missed `RESOURCE_EXHAUSTED`, no retries at all.
- **Unescaped model output** was injected into flashcard HTML.
- **Brittle URL regex** matched the wrong segment for some URLs; shorts/live/embed links weren't supported.
- **Quiz widget state leaked** between videos (same radio keys); answer was usually in the same option slot (options are now shuffled).
- **Three sequential AI calls on every analysis** (slow and quota-hungry). Notes generate automatically; quiz and flashcards generate on demand; everything is cached.
- **`test_api.py`** missing `import os`; **`test_quiz.py`** used an outdated `TranscriptData` signature and a non-existent `q.answer`.
- **README claims not matched by the UI** (character count, reading time, analytics dashboard, transcript viewer) — all now implemented.
- `gemini-*` temperature: Gemini 3 models are tuned for the default; the app no longer forces 0.5/0.7.

### Removed
- Legacy v1 files: `StreamlitApp.py`, `YouTubeAPIModule.py`, `summarization.py` (needed `transformers`, not in requirements), `text-to-speech.py`, `test_api.py`, `test_quiz.py`.
- Empty placeholders: `utils/helper.py`, `models/response_models.py`, `modules/pdf_export.py`, `modules/tts.py`; unused `prompts/summary_prompt.txt`.
- Duplicate copies of the project at the repository root.
- `google-api-python-client` (only used by the legacy app).

### Added
- Chat with the video (streaming, timestamps, tutor modes, suggested questions)
- Video chapters and timestamp navigation throughout
- Output language selection
- Quiz difficulty, mistake review, retry missed
- Flashcard mastery tracking and review mode, Anki export
- Transcript analytics, searchable transcript, TXT/SRT download
- Study pack export (PDF/HTML/Markdown), quiz report, chat export
- Text-to-speech
- Gemini video transcription fallback and paste-transcript mode
- Bring-your-own-key, per-session request cap, caching, retries
- Dockerfile, render.yaml, Streamlit config, CI, test suite
