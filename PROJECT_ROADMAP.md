# 🚀 Project Roadmap — LectureLens

## 🎯 Vision
A production-quality learning platform that turns YouTube videos into material students can **learn, revise, practise and interact with** — not just summaries.

**Current version:** v3.0 · **Status:** 🟢 Deployable · **Architecture:** modular, service-oriented

---

## ✅ v1.0 — Foundation
- [x] YouTube video summarizer, transcript extraction, basic Streamlit UI

## ✅ v2.0 – v2.2 — Learning platform
- [x] Modular service architecture, AI service layer, prompt files, data models
- [x] Executive summary, key points, study notes, important concepts
- [x] Interactive quiz (JSON parser, feedback, explanations, score)
- [x] Flashcards (own service, parser, model, navigation)
- [x] Centralized configuration and error handling

## ✅ v3.0 — Chat, accessibility, production readiness

### Reliability fixes
- [x] Default model moved off retired `gemini-2.0-flash` (shut down 2026-06-01) to `gemini-3.5-flash`
- [x] App no longer crashes on start without a key; reads Streamlit secrets as well as `.env`
- [x] Captions in **any language** (was English-only), with preferred-language ranking
- [x] Robust URL parsing (watch, youtu.be, shorts, embed, live, mobile)
- [x] Gemini retries with backoff; precise error codes (bad key, retired model, daily quota, rate limit, overload, safety block)
- [x] Tolerant parsers (code fences, wrapper objects, "B" as an answer, forgiving headings)
- [x] Flashcard HTML escaped (model output could inject markup)
- [x] Transcript analytics in the README now actually shown in the UI

### Chat with video (was v2.3)
- [x] Ask questions about the video · context-aware, multi-turn · conversation history
- [x] Suggested questions · source-aware answers with clickable timestamps · streaming
- [x] AI tutor modes: Explain · ELI5 · Examples · Compare · Practice questions

### Export & accessibility (was v2.4)
- [x] PDF / HTML / Markdown study pack · quiz report · flashcard export (Anki) · chat export
- [x] Text-to-speech: summary, key points, notes, concepts, flashcards
- [x] Transcript download (.txt / .srt)

### Smarter learning (part of v2.5)
- [x] Quiz difficulty selection · retry missed questions · review mistakes
- [x] Flashcards: known / still learning, review-only-unknown mode
- [x] Video chapters + timestamp navigation
- [x] Output in another language than the video
- [x] Recent videos in the session (instant reload from cache)

### Production readiness (part of v3.0)
- [x] Gemini video transcription fallback when YouTube blocks the server · paste-transcript mode
- [x] Bring-your-own-key + per-session request cap
- [x] Response caching (transcripts + every generation)
- [x] Dockerfile, Render blueprint, Streamlit Cloud config
- [x] Unit + service + export tests, Streamlit AppTest smoke test, GitHub Actions CI
- [x] Logging

---

## 🚧 Next — v3.1 Persistence
- [ ] User accounts (Streamlit OIDC login or Supabase auth)
- [ ] Save learning sessions, bookmarks and flashcard progress to a database (SQLite → Postgres/Supabase)
- [ ] Learning history and "continue where you left off"
- [ ] Spaced-repetition scheduling for flashcards (SM-2)

## 🔭 v3.2 Long videos & RAG
- [ ] Transcript chunking + embeddings (`gemini-embedding-2`) for videos beyond the context budget
- [ ] Semantic transcript search
- [ ] Gemini context caching for long chat sessions (cheaper multi-turn)

## 🔭 v3.3 More sources & richer study
- [ ] Playlists and multi-video study packs
- [ ] PDFs / lecture slides alongside the video
- [ ] Mind-map / concept-graph view of the notes
- [ ] Natural Gemini TTS voices as an alternative to gTTS
- [ ] Learning streaks, achievements, progress analytics dashboard

## 🔧 Engineering backlog
- [ ] Structured JSON schemas (`response_schema`) for quiz/flashcards
- [ ] Background generation of quiz + flashcards while the user reads notes
- [ ] Error monitoring (Sentry) and usage analytics
- [ ] End-to-end browser tests (Playwright)
