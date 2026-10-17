# ☁️ Deployment Guide

Before anything else: **never commit `.env` or `.streamlit/secrets.toml`.** Both are in `.gitignore`. If a key was ever committed or shared, revoke it in Google AI Studio and create a new one.

---

## Option 1 — Streamlit Community Cloud (recommended, free)

1. Push the project to a **public or private GitHub repo** (the repo root must contain `app.py` and `requirements.txt`).
2. Go to [share.streamlit.io](https://share.streamlit.io) → **Create app** → pick the repo, branch `main`, main file `app.py`.
3. Open **Advanced settings**:
   - Python version: **3.12**
   - Secrets: paste the contents of `.streamlit/secrets.toml.example` with your real values, at minimum:
     ```toml
     GEMINI_API_KEY = "your-key"
     SESSION_AI_CALL_LIMIT = "40"
     ALLOW_USER_API_KEY = "true"
     ```
4. **Deploy.** `packages.txt` installs DejaVu fonts for the PDF export automatically.

Updating: every push to `main` redeploys.

---

## Option 2 — Render (Docker, free tier)

1. Push to GitHub.
2. In [Render](https://render.com): **New → Blueprint** → select the repo. `render.yaml` creates the service.
3. Set `GEMINI_API_KEY` in the service's **Environment** tab.
4. Render builds the `Dockerfile` and serves the app on its URL. Health check: `/_stcore/health`.

Free instances sleep after inactivity; the first request after a sleep takes ~30–60 s.

---

## Option 3 — Any Docker host (Hugging Face Spaces, Railway, Cloud Run, a VPS)

```bash
docker build -t yt-learning .
docker run -p 8501:8501 -e GEMINI_API_KEY=your-key yt-learning
# open http://localhost:8501
```

The container listens on `$PORT` (default 8501), which Railway, Cloud Run and Hugging Face set for you.

- **Hugging Face Spaces:** create a Space with SDK = *Docker*, push the repo, set `PORT=7860` and `GEMINI_API_KEY` as Space secrets.
- **Google Cloud Run:** `gcloud run deploy --source . --set-env-vars GEMINI_API_KEY=...` (store the key in Secret Manager for production).

---

## YouTube blocks cloud servers — what the app does

YouTube refuses caption requests from most data-centre IPs (AWS, GCP, Azure, Streamlit Cloud, Render…). Locally everything works; in the cloud you'll often see *"YouTube is blocking caption downloads from this server"*. The app gives users two ways forward automatically:

1. **Transcribe with Gemini** — Gemini watches the public video directly (works from any server; uses more tokens: a 10-minute video is roughly 60k tokens at low resolution).
2. **Paste a transcript** — copy it from YouTube's *…more → Show transcript* panel.

For fully automatic captions in production, add a **rotating residential proxy**:

```toml
# Webshare (natively supported by youtube-transcript-api)
WEBSHARE_PROXY_USERNAME = "..."
WEBSHARE_PROXY_PASSWORD = "..."

# or any HTTP(S) proxy
TRANSCRIPT_PROXY_URL = "http://user:pass@host:port"
```

---

## Protecting your Gemini quota on a public app

- `SESSION_AI_CALL_LIMIT` caps requests per browser session when your key is used (default 40).
- `ALLOW_USER_API_KEY=true` lets heavy users paste their own free key, which bypasses the cap.
- Results are cached for `CACHE_TTL_SECONDS`, so popular videos are only generated once.
- To require every visitor to bring a key, simply don't set `GEMINI_API_KEY`.

---

## Pre-launch checklist

- [ ] Old key revoked, new key stored only in platform secrets
- [ ] `pytest -q` and `ruff check .` pass (CI does this on every push)
- [ ] Tested one English and one non-English video on the deployed URL
- [ ] Tested the "Transcribe with Gemini" fallback on the deployed URL
- [ ] Live demo link added to the README
