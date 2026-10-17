# 🔎 LectureLens

### AI Video Learning Platform

> Turn any YouTube lecture into study notes, a quiz, flashcards and a personal AI tutor — powered by Google Gemini.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue) ![Streamlit](https://img.shields.io/badge/Streamlit-1.58-red) ![Gemini](https://img.shields.io/badge/Google%20Gemini-3.5%20Flash-orange)

**Live demo:** _add your Streamlit Cloud / Render URL here_

Paste a YouTube link and LectureLens fetches the captions (in any language), then generates structured learning material you can read, chat with, test yourself on, listen to and export.

---

## ✨ Features

### 📘 Study notes
- Executive summary, key points, detailed study notes and important concepts
- **Clickable video chapters** — jump the embedded player to any section
- Timestamps inside notes link straight to that moment of the video
- Generate the material **in another language** than the video (Hindi, Spanish, …)

### 💬 Chat with the video (AI tutor)
- Multi-turn chat grounded in the transcript, with **streaming answers**
- Answers cite timestamps like `[04:12]`; one click jumps the player there
- Tutor modes: **Ask · Explain · Explain like I'm 5 · Examples · Compare · Practice questions**
- Suggested questions generated from the video

### 📝 Adaptive quiz
- Choose 3–15 questions and a difficulty (Easy / Medium / Hard / Mixed)
- One question at a time, instant feedback and explanations
- "Explained in the video at…" jump buttons
- Results page with mistakes review and **retry only the questions you missed**

### 🗂️ Flashcards
- Flip, navigate, shuffle
- Mark cards **Known / Still learning** and review only the ones you're still learning
- Export to **Anki**

### 📜 Transcript & analytics
- Word count, characters, reading time, speaking pace, duration, caption source
- Most-frequent-terms chart
- Searchable transcript table — select a row to jump the video there
- Download as `.txt` or `.srt`

### 📤 Export & audio
- Study pack as **PDF**, printable **HTML** and **Markdown**
- Quiz report and chat transcript downloads
- **Text-to-speech** for the summary, notes, concepts or flashcards (MP3)

### 🛡️ Built for real deployment
- Works when YouTube blocks cloud servers: **Gemini can watch the video and transcribe it**, or you can paste a transcript
- **Bring-your-own-key**: visitors can use their own free Gemini key; a per-session request cap protects yours
- Automatic **retries with backoff** for rate limits and overloads, clear error messages for bad keys, retired models and quota
- **Caching** of transcripts and AI output — revisiting a video or switching tabs costs nothing
- Docker image, Render blueprint, GitHub Actions CI and a test suite

---

## 🏛️ Architecture

```text
                       app.py  (wires views together)
                          │
          ┌───────────────┼──────────────────────────┐
          ▼               ▼                          ▼
     ui/sidebar      ui/home  (input + loading)   ui/tabs/*  learn · chat · quiz
          │               │                          │        flashcards · transcript · export
          └───────────────┴─────────┬────────────────┘
                                    ▼
                          ui/services.py  (session wiring + st.cache_*)
                                    │
     ┌──────────────┬───────────────┼───────────────┬──────────────┬──────────────┐
     ▼              ▼               ▼               ▼              ▼              ▼
 transcript   video_transcriber  LearningService  QuizService  FlashcardService  ChatService
 (captions)   (Gemini fallback)        │               │              │              │
     │              └──────────────────┴───────┬───────┴──────────────┴──────────────┘
     ▼                                         ▼
 youtube-transcript-api                 AIService ──► Google Gemini API
                                    (retries, error codes, streaming, video input)

 prompts/*.txt  → all prompt engineering        utils/*  → parsers, text & time helpers
 models/*       → plain dataclasses              modules/export_service, tts_service → downloads & audio
```

**Rules the codebase follows**
- `app.py` and `ui/` only render and manage session state.
- Business logic lives in `modules/`; no Streamlit imports there.
- Prompts live only in `prompts/`; parsing only in `utils/`.
- `config.py` is the only place that reads environment variables / secrets.

---

## 📂 Project structure

```text
youtube-ai-learning-assistant/
├── app.py                     # Streamlit entry point
├── config.py                  # settings from env / Streamlit secrets
├── requirements.txt           # runtime deps   (requirements-dev.txt adds pytest + ruff)
├── packages.txt               # apt packages for Streamlit Cloud (PDF fonts)
├── Dockerfile · render.yaml   # container + one-click Render deploy
├── .streamlit/config.toml     # theme + server settings
├── models/                    # transcript, learning_content, quiz, flashcard, chat
├── modules/                   # ai_service, transcript, video_transcriber, youtube,
│                              # learning/quiz/flashcard/chat services, export, tts
├── prompts/                   # learning, quiz, flashcard, chat, suggestions, transcription
├── ui/                        # sidebar, home, video header, styles, tabs/
├── utils/                     # parsers, json, text cleaning/statistics, time helpers
└── tests/                     # pytest suite (+ Streamlit AppTest smoke test)
```

---

## 🚀 Run locally

```bash
git clone https://github.com/<your-username>/youtube-ai-learning-assistant.git
cd youtube-ai-learning-assistant

python -m venv venv
# Windows: venv\Scripts\activate     macOS/Linux: source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env        # then put your Gemini key in .env
streamlit run app.py
```

Get a free key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey). You can also leave `.env` empty and paste a key into the sidebar.

### Run the tests

```bash
pip install -r requirements-dev.txt
pytest -q
ruff check .
```

---

## ☁️ Deploy

See **[DEPLOYMENT.md](DEPLOYMENT.md)** for step-by-step guides:

| Platform | Effort | Notes |
|---|---|---|
| Streamlit Community Cloud | ~5 min, free | Easiest. Add secrets in the dashboard. |
| Render (Docker) | ~10 min, free tier | `render.yaml` blueprint included. |
| Hugging Face Spaces / Railway / Cloud Run | ~10 min | Use the Dockerfile. |

> YouTube blocks caption downloads from most cloud IPs. The app handles this by offering **Gemini video transcription** or **paste a transcript**. For fully automatic captions in production, add a residential proxy (see DEPLOYMENT.md).

---

## ⚙️ Configuration

| Variable | Default | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | — | Server-side key (optional if visitors bring their own) |
| `GEMINI_MODEL` | `gemini-3.5-flash` | Default model |
| `GEMINI_MODEL_CHOICES` | `gemini-3.5-flash,gemini-3.1-flash-lite` | Models offered in the sidebar |
| `ALLOW_USER_API_KEY` | `true` | Let visitors paste their own key |
| `SESSION_AI_CALL_LIMIT` | `40` | Max AI requests per visitor session on your key (0 = unlimited) |
| `ENABLE_GEMINI_VIDEO_FALLBACK` | `true` | Offer Gemini transcription when captions fail |
| `TRANSCRIPT_LANGUAGES` | `en,hi` | Preferred caption languages |
| `MAX_TRANSCRIPT_CHARS` | `200000` | Transcript length sent to the model |
| `AI_MAX_RETRIES` | `3` | Retries for rate limits / overloads |
| `CACHE_TTL_SECONDS` | `21600` | How long results stay cached |
| `WEBSHARE_PROXY_USERNAME` / `_PASSWORD` | — | Residential proxy for captions |
| `TRANSCRIPT_PROXY_URL` | — | Any HTTP(S) proxy for captions |
| `GITHUB_URL` | — | Shows a "Source on GitHub" link |

---

## 📈 Project evolution

| Version | Highlights |
|---|---|
| v1.0 | YouTube video summarizer |
| v2.0 | Structured learning content, modular architecture |
| v2.1 | Interactive quiz |
| v2.2 | Flashcards + architecture refactor |
| **v3.0** | Chat with video, chapters & timestamp navigation, multi-language output, adaptive quiz, smarter flashcards, export & audio, Gemini fallback, BYOK, retries, caching, Docker/CI, tests |

See [PROJECT_ROADMAP.md](PROJECT_ROADMAP.md), [CHANGELOG.md](CHANGELOG.md) and [DECISIONS.md](DECISIONS.md) (why each change was made).

---

## 👨‍💻 Author

**Harsh Poonia** — MCA student · AI · Machine Learning · Data Analytics

If this project helped you, consider giving it a ⭐.
