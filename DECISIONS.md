# 🧭 Decision Log — v3.0

This file records **every significant change made in the v2.2 → v3.0 upgrade and the reasoning behind it**. Each entry follows the same shape:

- **Context** — what the situation or problem was
- **Decision** — what was done
- **Alternatives considered** — what else was possible and why it wasn't chosen
- **Consequences** — trade-offs, follow-ups, things to watch

Decisions are grouped by area. IDs (`D-01`…) are stable so they can be referenced in commits and issues.

**Date:** 2026-10-17 · **Version:** 3.0.0

---

## Index

| ID | Area | Decision |
|---|---|---|
| D-01 | Security | Treat the uploaded API key as compromised; keep secrets out of Git |
| D-02 | AI model | Default to `gemini-3.5-flash`; make the model selectable |
| D-03 | AI model | Stop forcing a temperature |
| D-04 | Config | App must start without a key; read Streamlit secrets too |
| D-05 | Config | Bring-your-own-key + per-session request cap |
| D-06 | AI service | Retries with backoff; stable error codes |
| D-07 | AI service | Lazy SDK import + injectable client for testing |
| D-08 | AI service | JSON mode for quiz / flashcards, plus tolerant parsers |
| D-09 | Transcripts | Accept captions in any language |
| D-10 | Transcripts | Rewrite video-ID extraction with `urllib.parse` |
| D-11 | Transcripts | Keep timestamped segments |
| D-12 | Transcripts | Gemini video transcription fallback |
| D-13 | Transcripts | Paste-a-transcript mode |
| D-14 | Transcripts | Optional proxy support |
| D-15 | Generation | Generate notes automatically, quiz/flashcards on demand |
| D-16 | Generation | Cache transcripts and every AI result |
| D-17 | Generation | Video chapters inside the notes prompt |
| D-18 | Generation | Output-language selection |
| D-19 | Generation | Shuffle quiz options client-side |
| D-20 | Generation | One automatic retry on malformed output |
| D-21 | Feature | Chat with the video (v2.3) |
| D-22 | Feature | Timestamp navigation everywhere |
| D-23 | Feature | Quiz: difficulty, review, retry missed |
| D-24 | Feature | Flashcards: mastery tracking, review mode |
| D-25 | Feature | Transcript analytics + searchable viewer |
| D-26 | Feature | Export formats: Markdown, HTML, PDF, Anki, SRT |
| D-27 | Feature | Text-to-speech with gTTS |
| D-28 | Feature | Video metadata via oEmbed |
| D-29 | UI | Split `app.py` into a `ui/` package |
| D-30 | UI | Central session-state schema |
| D-31 | UI | Escape model output inserted as HTML |
| D-32 | UI | Theme + small CSS layer |
| D-33 | Cleanup | Remove legacy, empty and duplicate files |
| D-34 | Deploy | Three deployment targets |
| D-35 | Deploy | Docker image design |
| D-36 | Quality | Test strategy and CI |
| D-37 | Docs | Rewrite README, roadmap, add changelog + deployment guide |
| D-38 | Brand | Rename the product to **LectureLens** |

---

## 🔐 Security

### D-01 — Treat the uploaded API key as compromised; keep secrets out of Git

- **Context:** The project upload contained a `.env` with a live `GEMINI_API_KEY`. Anything shared outside your machine (chat uploads, Git history, screenshots) must be assumed exposed. Google also auto-revokes keys it finds in public repos.
- **Decision:** Recommend revoking the key immediately. Ship `.env.example` and `.streamlit/secrets.toml.example` with placeholders only; `.gitignore` excludes `.env`, `.env.*` (except the example) and `.streamlit/secrets.toml`; `.dockerignore` keeps secrets out of images.
- **Alternatives:** Keep using the key — rejected, unsafe.
- **Consequences:** You must create a new key and add it only to platform secret stores (Streamlit Cloud Secrets, Render env vars).

---

## 🤖 AI model & AI service

### D-02 — Default to `gemini-3.5-flash`; make the model selectable

- **Context:** The default `gemini-2.0-flash` was shut down by Google on 2026-06-01, so **every AI request failed**. Its successor `gemini-2.5-flash` was scheduled for shutdown on 2026-10-16. Hardcoding one model ID is what broke the app.
- **Decision:** Default `GEMINI_MODEL=gemini-3.5-flash`. Offer a sidebar picker (`GEMINI_MODEL_CHOICES`, default `gemini-3.5-flash, gemini-3.1-flash-lite`). A retired/unknown model now produces a specific "Model not available — pick another" error instead of a generic failure.
- **Alternatives:** `gemini-2.5-flash` (retiring), a Pro model (slower, lower free limits).
- **Consequences:** When Google retires 3.5 Flash, change one env var — no code change. Watch the Gemini deprecations page.

### D-03 — Stop forcing a temperature

- **Context:** Services sent `temperature=0.5/0.7`. Google's guidance for Gemini 3 models is to keep the default temperature (1.0); lowering it can cause repetition or degraded reasoning.
- **Decision:** `AIService` only sends `temperature` when a caller explicitly passes one. No service does by default.
- **Consequences:** Slightly more varied output; the parsers (D-08) absorb format variation.

### D-06 — Retries with backoff; stable error codes

- **Context:** One 429 or 503 killed the whole pipeline. Error detection had bugs: the UI checked for an `unauthenticated` code that `_classify_error` never produced; empty responses got the generic code; `"resource_exhausted"` was matched case-sensitively against an uppercase message.
- **Decision:**
  - `classify_error()` maps exceptions to one of: `missing_key`, `unauthenticated`, `model_not_found`, `quota_exhausted`, `rate_limited`, `unavailable`, `blocked`, `empty_response`, `api_error`.
  - Daily / zero-limit quota → `quota_exhausted` (no retry; retrying can't help). Per-minute limits → `rate_limited` (retry).
  - Retries `rate_limited` and `unavailable` up to `AI_MAX_RETRIES` (default 3), honouring Google's suggested `retry in Xs`, otherwise exponential backoff (2s, 4s, 8s), capped at 30s.
  - Streaming retries only **before the first chunk**, so users never see a duplicated half-answer.
  - Each code carries a title + help text (`ERROR_HELP`) so the UI shows actionable advice.
- **Alternatives:** `tenacity` library — rejected to avoid a dependency for ~30 lines of logic.
- **Consequences:** A failing request can take up to ~45s before surfacing an error; acceptable for a better success rate.

### D-07 — Lazy SDK import + injectable client

- **Context:** Importing `google.genai` at module top made the whole service layer untestable without the SDK and network.
- **Decision:** `AIService(client=..., sleep=...)` accepts a fake client and fake sleep; the real SDK is imported only when building a real client. Same pattern for `youtube_transcript_api`, `gtts`, `fpdf`.
- **Consequences:** Unit tests run fast and offline, including retry timing.

### D-08 — JSON mode for quiz / flashcards, plus tolerant parsers

- **Context:** Quiz/flashcard parsing failed on harmless deviations: code fences, a sentence before the array, `{"questions": [...]}` wrappers, or `"B"` as the answer instead of the option text.
- **Decision:**
  - Request `response_mime_type="application/json"` for structured outputs.
  - New `utils/json_utils.py` strips fences, finds the outermost array/object, unwraps single-list objects.
  - Quiz parser resolves answers given as text (case-insensitive), letter (`B`, `(B)`, `Option B`), index (`1`) or `"B) text"`; skips individual bad questions instead of failing the whole quiz.
  - Flashcard parser drops empty and duplicate cards; normalises difficulty.
  - Markdown parser accepts `# 2. Key Points:`, `# **Key Points**`, etc.
- **Alternatives:** Full `response_schema` structured output — moved to backlog; JSON mode + tolerant parsing is simpler and robust across models.
- **Consequences:** Far fewer "unexpected format" errors; still strict where it matters (4 unique options, answer must be one of them).

---

## ⚙️ Configuration

### D-04 — App must start without a key; read Streamlit secrets too

- **Context:** `config.py` raised `EnvironmentError` at import when `GEMINI_API_KEY` was missing, crashing the app before any UI rendered. Streamlit Cloud provides secrets via `st.secrets`, which the app ignored.
- **Decision:** Settings load from Streamlit secrets first, then env/`.env`. A missing key is allowed; the UI asks for one. `config.py` remains the only place reading configuration.
- **Consequences:** Same codebase runs locally, on Streamlit Cloud and in Docker with no changes.

### D-05 — Bring-your-own-key + per-session request cap

- **Context:** A public demo using your key can be drained by strangers within hours on the free tier.
- **Decision:**
  - `ALLOW_USER_API_KEY=true`: visitors can paste their own key (password field, session-only, never stored).
  - `SESSION_AI_CALL_LIMIT=40`: cap on AI requests per browser session when **your** key pays; users with their own key are unlimited.
  - Not setting `GEMINI_API_KEY` at all makes the app fully BYOK.
- **Alternatives:** Login + per-user quotas — deferred to v3.1 (needs a database).
- **Consequences:** The counter is per session (a refresh resets it). It deters casual overuse, not determined abuse; caching (D-16) further reduces real spend.

---

## 📺 Transcripts

### D-09 — Accept captions in any language

- **Context:** `fetch(video_id, languages=["en"])` failed for any video without English captions — including most Hindi content.
- **Decision:** List all caption tracks and rank: preferred language (sidebar, default `en, hi`) → creator captions over auto-generated → any language as a last resort. Record the language and whether captions are auto-generated.
- **Consequences:** Non-English videos work; D-18 lets the user still get notes in English.

### D-10 — Rewrite video-ID extraction with `urllib.parse`

- **Context:** The regex `(?:v=|\/)([0-9A-Za-z_-]{11})` could match the wrong path segment and didn't handle `shorts/`, `live/`, `embed/` or `m.youtube.com` reliably.
- **Decision:** Parse the URL properly: host check, `v=` query param, `youtu.be/<id>`, `/shorts|embed|live|v/<id>`, or a bare 11-char ID. Invalid input raises `TranscriptError(code="invalid_url")`.
- **Consequences:** Covered by parametrized tests for 9 valid and 4 invalid formats.

### D-11 — Keep timestamped segments

- **Context:** Snippet timings were discarded after joining text, so nothing could reference moments in the video.
- **Decision:** `TranscriptData` stores `segments` (text, start, duration). `timestamped_text()` builds model input with a `[mm:ss]` marker roughly every 30s.
- **Consequences:** Enables chapters, cited chat answers, quiz "review at" links, SRT export and the clickable transcript (D-17, D-21, D-22). Markers add ~3–5% to prompt size.

### D-12 — Gemini video transcription fallback

- **Context:** YouTube blocks caption requests from most cloud IPs (Streamlit Cloud, Render, AWS…). The app worked locally but would fail for most users once deployed.
- **Decision:** When captions fail (except invalid URL / unavailable video), offer **"Transcribe with Gemini"**: Gemini receives the public YouTube URL as `file_data` and returns a timestamped transcript (with a `LANGUAGE:` header). Uses `MEDIA_RESOLUTION_LOW` to reduce token cost. It's a button, not automatic. Toggle via `ENABLE_GEMINI_VIDEO_FALLBACK`.
- **Alternatives:** Automatic fallback — rejected because it silently spends many tokens; `yt-dlp` audio download + speech-to-text — heavier, also blocked from cloud IPs.
- **Consequences:** Works from any server for public videos. A 10-minute video costs roughly tens of thousands of tokens. Results are cached per video.

### D-13 — Paste-a-transcript mode

- **Context:** A zero-cost, always-available path is needed (private videos, quota exhausted, non-YouTube lectures).
- **Decision:** A second input tab accepts any text; lines starting with `[mm:ss]` keep timestamps; an optional YouTube link enables the player.
- **Consequences:** The app also works for lecture notes or podcasts, not only YouTube.

### D-14 — Optional proxy support

- **Context:** For fully automatic captions in production, a residential proxy is the standard solution.
- **Decision:** Support `WEBSHARE_PROXY_USERNAME/PASSWORD` (native in youtube-transcript-api) or any `TRANSCRIPT_PROXY_URL`.
- **Consequences:** Off by default (costs money); documented in DEPLOYMENT.md.

---

## 🧠 Generation pipeline

### D-15 — Notes automatically, quiz/flashcards on demand

- **Context:** "Analyze" ran three sequential Gemini calls (notes, quiz, flashcards) — slow (~30–60s) and quota-heavy even if the user never opened the quiz.
- **Decision:** Only study notes generate automatically. Quiz and flashcards have their own "Generate" buttons with size/difficulty controls in their tabs.
- **Consequences:** Faster first result, ~⅓ of the API usage for casual visits, and the user chooses quiz size/difficulty at generation time.

### D-16 — Cache transcripts and every AI result

- **Context:** Nothing was cached; re-analyzing a video re-billed everything.
- **Decision:** `st.cache_data` (TTL `CACHE_TTL_SECONDS`, default 6h) keyed by the transcript's **content hash** + model + language + parameters. A `nonce` key enables explicit "Regenerate". The API key is *not* part of the cache key, so all users share results for the same video.
- **Alternatives:** Redis/disk cache — unnecessary at this scale; can be added later.
- **Consequences:** Recent videos reload instantly. Cache resets when the app restarts.

### D-17 — Video chapters inside the notes prompt

- **Context:** "Timestamp navigation" was on the roadmap; a separate chapters call would cost another request.
- **Decision:** Add an optional `# Video Chapters` section (`- [mm:ss] Title`) to the learning prompt when timestamps exist. Parser treats it as optional and ignores chapters beyond the video length.
- **Consequences:** Chapters at zero extra API cost.

### D-18 — Output-language selection

- **Context:** Learners often watch videos in one language but study in another.
- **Decision:** Sidebar "Write study material in" (Same as video, English, Hindi, …) injected into every prompt via `language_instruction()`. Section headings stay in English so parsing still works. Changing it regenerates notes (from cache when possible).
- **Consequences:** Delivers the README's "Multi-language Support" item.

### D-19 — Shuffle quiz options client-side

- **Context:** LLMs tend to put the correct answer in the same position (often B).
- **Decision:** `QuizService` shuffles each question's options after parsing (answers are stored as text, so correctness is unaffected).

### D-20 — One automatic retry on malformed output

- **Context:** Occasionally a response ignores the requested format.
- **Decision:** Each generation service retries once on a parse error before surfacing it.
- **Consequences:** At most one extra request in the rare failure case.

---

## ✨ Features

### D-21 — Chat with the video (roadmap v2.3)

- **Decision:**
  - `ChatService` with the full timestamped transcript as **system instruction** and the last 10 messages (each trimmed to 1,500 chars) as history.
  - **Streaming** answers via `generate_content_stream` + `st.write_stream`.
  - The tutor must cite `[mm:ss]` markers and say clearly when a question goes beyond the video.
  - Tutor modes stored in `prompts/chat_modes.json` (Ask, Explain, ELI5, Examples, Compare, Practice questions) — keeps the "prompts live in prompts/" rule.
  - Starter questions are static (free); "✨ Suggest questions" generates video-specific ones only on request.
- **Alternatives:** RAG with embeddings — unnecessary while transcripts fit in context; planned for long videos (v3.2).
- **Consequences:** Each chat turn resends the transcript (token cost grows with video length). Gemini context caching is in the backlog.

### D-22 — Timestamp navigation everywhere

- **Decision:** One `jump_to(seconds)` helper drives the embedded `st.video` player (with autoplay). Used by chapter buttons, chat citation buttons, quiz "explained at" buttons and transcript row selection. `[mm:ss]` in text also becomes a YouTube link (opens at that time). Timestamps past the video's end are ignored.
- **Consequences:** Transcript row-selection tracks the last handled click so it doesn't re-jump after other navigation.

### D-23 — Quiz: difficulty, review, retry missed

- **Decision:** Difficulty selector (Mixed/Easy/Medium/Hard); results page with score, accuracy, expandable review of mistakes; "Retry missed questions" starts a round with only those; the first full round is kept for the quiz report export. Widget keys include video run ID, quiz nonce and round, fixing stale selections leaking between videos.

### D-24 — Flashcards: mastery tracking, review mode

- **Decision:** After flipping, mark "I knew it" / "Still learning"; progress bar of mastered cards; toggle to review only cards still being learned; shuffle uses an index order instead of mutating the deck.
- **Alternatives:** Full spaced repetition (SM-2) — needs persistence, planned for v3.1.

### D-25 — Transcript analytics + searchable viewer

- **Context:** README advertised character count, reading time and an analytics dashboard the UI didn't show.
- **Decision:** Metrics (words, characters, reading time, speaking pace, duration, source), a most-frequent-terms chart (Latin scripts, stop-words removed), a searchable transcript table with row-click jump, and TXT/SRT downloads.

### D-26 — Export formats

- **Decision:**
  - **Markdown** — canonical study pack; everything else is derived from it.
  - **Printable HTML** — renders the Markdown with marked.js; "Save as PDF" in a browser gives perfect output for any script (Hindi, Japanese…).
  - **PDF** via `fpdf2` (pure Python, no system deps) using DejaVu fonts when available (`packages.txt` / Dockerfile install them), Latin-1 fallback otherwise.
  - **Anki** TSV with Anki header lines; quiz report; chat transcript; SRT.
- **Alternatives:** WeasyPrint / wkhtmltopdf — better rendering but heavy system dependencies that break on Streamlit Cloud.
- **Consequences:** The PDF is clean but simple (no complex tables, limited Devanagari shaping); the HTML route covers that. PDF generation failures never break the page — the button just disables.

### D-27 — Text-to-speech with gTTS

- **Decision:** gTTS (already in requirements) converts Markdown-stripped text to MP3 in memory, in the output or video language; capped at ~6,000 characters per clip; cached.
- **Alternatives:** Gemini TTS (more natural, preview at the time, costs tokens) — in backlog.

### D-28 — Video metadata via oEmbed

- **Decision:** Fetch title/channel from YouTube's public oEmbed endpoint (no API key), replacing the legacy YouTube Data API usage. Failures are silent.
- **Consequences:** `google-api-python-client` removed from requirements.

---

## 🖥️ UI architecture

### D-29 — Split `app.py` into a `ui/` package

- **Context:** One 350-line `app.py` would have grown past 1,000 lines with the new features.
- **Decision:** `app.py` only wires views. `ui/sidebar.py`, `ui/home.py` (input + loading pipeline), `ui/video_header.py`, `ui/tabs/{learn,chat,quiz,flashcards,transcript,export}.py`, `ui/services.py` (caching + session wiring), `ui/components.py`, `ui/styles.py`. `modules/` stays Streamlit-free.

### D-30 — Central session-state schema

- **Decision:** `ui/state.py` declares every key with defaults, split into per-video state (reset on new video) and per-session state (recent videos, AI-call counter). A `run_id` increments per video so widget keys never collide.
- **Consequences:** "Analyze another video" can't leak old quiz answers, chat or flashcard progress.

### D-31 — Escape model output inserted as HTML

- **Context:** Flashcard text from the model was placed into `unsafe_allow_html` markup unescaped.
- **Decision:** `html.escape()` for every model/user string rendered as raw HTML (flashcards, titles, badges). Markdown content goes through `st.markdown` without `unsafe_allow_html`. The HTML export neutralises `</script>` inside content.

### D-32 — Theme + small CSS layer

- **Decision:** `.streamlit/config.toml` sets a red accent theme; `ui/styles.py` adds hero, feature cards, badges and flip-card styles with translucent colours that work in light and dark mode. Landing page shows a feature grid; a loaded video shows player + key metrics above six tabs.

---

## 🧹 Cleanup

### D-33 — Remove legacy, empty and duplicate files

| Removed | Reason |
|---|---|
| `StreamlitApp.py`, `YouTubeAPIModule.py`, `summarization.py`, `text-to-speech.py` | v1 code; needed `transformers` (not in requirements) and a YouTube Data API key; superseded |
| `test_api.py`, `test_quiz.py` | Broken (missing import, outdated classes); replaced by `tests/` |
| `utils/helper.py`, `models/response_models.py`, `modules/pdf_export.py`, `modules/tts.py`, old empty `modules/youtube.py` | Empty placeholders; real implementations now exist |
| `prompts/summary_prompt.txt` | Unused |
| Root-level duplicate copies of the project | Ambiguous which copy was real; one project root now |
| `google-api-python-client` dependency | Only used by legacy code |

Git history keeps everything if it's ever needed.

---

## ☁️ Deployment

### D-34 — Three deployment targets

- **Decision:** Support **Streamlit Community Cloud** (simplest, free; `packages.txt` + secrets), **Render** via `render.yaml` blueprint (Docker), and **any Docker host** (Hugging Face Spaces, Railway, Cloud Run, VPS). Step-by-step guide in `DEPLOYMENT.md`.
- **Alternatives:** Vercel/Netlify — not suitable for a long-running Streamlit server.

### D-35 — Docker image design

- **Decision:** `python:3.12-slim`, DejaVu fonts for PDF, non-root user, `$PORT`-aware start command, health check on `/_stcore/health`, `.dockerignore` excluding secrets/tests.

---

## ✅ Quality

### D-36 — Test strategy and CI

- **Decision:**
  - Pytest suite (63 tests): parsers, JSON extraction, URL parsing, transcript building, time/text utilities, AI retry/backoff and error classification with a fake SDK client, every service with a fake AI, all export formats.
  - Streamlit `AppTest` smoke test for the landing page (skipped where Streamlit isn't installed).
  - GitHub Actions: `ruff check` + `pytest` + Docker build on every push/PR.
  - Lint rules: pyflakes/pycodestyle/bugbear/pyupgrade, ignoring pure-style rules (line length, `zip(strict=)`) that would block CI without improving correctness.
- **Verification done during the upgrade:** all 63 tests passed; ~30 UI flows (load, chapters, full quiz incl. retry, flashcards, chat streaming, audio, downloads, language switch, Gemini fallback, paste mode, quota cap) executed against a Streamlit stand-in because packages couldn't be installed in the build sandbox.
- **Not yet verified:** real Streamlit rendering, the PDF output, and live YouTube/Gemini calls — CI and a first deployed test will cover these.

---

## 📚 Documentation

### D-37 — Rewrite README, roadmap; add changelog and deployment guide

- **Context:** The README described features the UI didn't have and listed file names that didn't exist (`transcript_model.py`, etc.); the roadmap marked v2.3 "in progress" with nothing started.
- **Decision:** README now matches the code exactly (features, architecture, structure, config table). `PROJECT_ROADMAP.md` marks what v3.0 delivered and sets v3.1 (persistence), v3.2 (long videos/RAG), v3.3 (more sources). Added `CHANGELOG.md`, `DEPLOYMENT.md` and this `DECISIONS.md`.

---

## 🏷️ Brand

### D-38 — Rename the product to LectureLens

- **Context:** "YouTube AI Learning Assistant" describes the app but reads like a homework title on a CV, and YouTube's brand rules don't allow "YouTube" as another product's name.
- **Decision:** Product name **LectureLens**, descriptor "AI Video Learning Platform". Used for the app title (`APP_TITLE` default), page title and icon, hero, exports, README, roadmap, Render service and package name. The hero renders it as "Lecture" + accent "Lens". The design mock-ups use a lens-with-play-button mark.
- **Alternatives:** StudyStream AI, VidMentor, Lecturely, EduLens AI — LectureLens was clearest in two seconds and works as a repo name (`lecturelens`).
- **Consequences:** The Git repo and local folder can keep the old name or be renamed on GitHub (old links redirect). "YouTube" still appears in descriptions ("for YouTube lectures"), which is allowed.

---

## 🔮 Open decisions (for later)

| Topic | Options | Leaning |
|---|---|---|
| User accounts & saved progress | Streamlit OIDC login · Supabase auth + Postgres | Supabase (auth + DB in one) |
| Long videos beyond context budget | Chunk + map-reduce · embeddings/RAG | RAG with `gemini-embedding-2` |
| Chat cost on long videos | Gemini context caching · RAG retrieval | Context caching first (simpler) |
| Structured outputs | Keep JSON mode · `response_schema` | `response_schema` once stable across chosen models |
| Natural voices | gTTS · Gemini TTS | Offer Gemini TTS as an option |
