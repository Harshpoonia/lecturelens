"""
ui/styles.py

LectureLens "Night Study Desk" look, layered on Streamlit's dark theme
(.streamlit/config.toml sets the base colours).

- Ink-black ground, charcoal surfaces, one coral accent
- Space Grotesk headings, IBM Plex Sans body, JetBrains Mono for numbers and timestamps
- Inline SVG line icons instead of emoji (ICONS / icon())

Streamlit's DOM is targeted through its stable data-testid attributes.
"""

from __future__ import annotations

import streamlit as st

ACCENT = "#FF6B57"

# Lucide-style stroke icons (24×24 viewBox), rendered with icon().
ICONS: dict[str, str] = {
    "lens": '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m20 20-4.8-4.8"/><path d="M9 8v5l4-2.5Z" fill="currentColor"/>',
    "notes": '<path d="M4 19.5V5a2 2 0 0 1 2-2h12v16H6a2 2 0 0 0-2 2Z"/><path d="M8 7h6"/><path d="M8 11h8"/>',
    "chat": '<path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12Z"/>',
    "quiz": '<path d="M9 11l3 3 8-8"/><path d="M20 12v7a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h9"/>',
    "cards": '<rect x="3" y="6" width="14" height="14" rx="2"/><path d="M7 2h12a2 2 0 0 1 2 2v12"/>',
    "audio": '<path d="M3 14h3l4 4V6L6 10H3Z"/><path d="M15 9a4 4 0 0 1 0 6"/><path d="M18 6a8 8 0 0 1 0 12"/>',
    "export": '<path d="M12 3v12"/><path d="m7 10 5 5 5-5"/><path d="M5 21h14"/>',
}

# (icon, tile background, stroke colour) per feature
FEATURE_TONES = {
    "notes": ("#2A1A17", "#FF8A7A"),
    "chat": ("#17202A", "#7DB7FF"),
    "quiz": ("#1A2420", "#6FE0AA"),
    "cards": ("#262016", "#F5C26B"),
    "audio": ("#221A2A", "#C9A2FF"),
    "export": ("#1E2228", "#C9CDD6"),
}


def icon(name: str, size: int = 22, color: str = "currentColor", width: float = 1.9) -> str:
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" '
        f'stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        f"{ICONS[name]}</svg>"
    )


def brand_html(title: str = "LectureLens", subtitle: str = "AI video learning platform") -> str:
    """Logo tile + wordmark ('Lecture' + accent 'Lens') for the sidebar."""
    from ui.home import _split_title  # local import avoids a cycle

    first, accent = _split_title(title)
    return (
        '<div class="ll-brand">'
        f'<div class="ll-brand-mark">{icon("lens", 20, "#1A0D0A", 2.2)}</div>'
        f'<div><div class="ll-brand-name">{first}<span>{accent}</span></div>'
        f'<div class="ll-brand-sub">{subtitle}</div></div></div>'
    )


_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=JetBrains+Mono:wght@400;500&family=Space+Grotesk:wght@500;600;700&display=swap');

:root {
  --ll-bg: #0D0E12; --ll-surface: #15171D; --ll-surface-2: #1A1C23; --ll-sunken: #0F1015;
  --ll-line: #23262F; --ll-line-2: #2E323D; --ll-text: #EDEEF1; --ll-muted: #A3A9B6; --ll-dim: #8C93A1;
  --ll-accent: #FF6B57; --ll-accent-ink: #1A0D0A; --ll-accent-soft: #2A1A17; --ll-accent-text: #FFB3A8;
  --ll-good: #3FCF8E; --ll-good-soft: #13241B;
}

/* ---------- base ---------- */
html, body, [data-testid="stAppViewContainer"], [data-testid="stSidebar"], .stMarkdown, p, li, label, input, textarea, button {
  font-family: 'IBM Plex Sans', system-ui, sans-serif;
}
h1, h2, h3, h4, h5 { font-family: 'Space Grotesk', sans-serif !important; letter-spacing: -0.02em; }
code, pre, [data-testid="stMetricValue"] { font-family: 'JetBrains Mono', monospace !important; }
[data-testid="stAppViewContainer"] { background: var(--ll-bg); }
[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 2.2rem; padding-bottom: 5rem; max-width: 1240px; }
a { color: #FF8A7A; } a:hover { color: var(--ll-accent-text); }
hr { border-color: var(--ll-line) !important; }

/* ---------- sidebar ---------- */
[data-testid="stSidebar"] { background: #121318; border-right: 1px solid var(--ll-line); }
[data-testid="stSidebar"] .block-container, [data-testid="stSidebarContent"] { padding-top: 1.2rem; }
.ll-brand { display: flex; align-items: center; gap: 12px; margin: 4px 0 18px; }
.ll-brand-mark { width: 38px; height: 38px; border-radius: 11px; background: var(--ll-accent);
  display: flex; align-items: center; justify-content: center; flex: 0 0 auto; }
.ll-brand-name { font-family: 'Space Grotesk', sans-serif; font-weight: 700; font-size: 17px; letter-spacing: -0.01em; color: var(--ll-text); }
.ll-brand-name span { color: var(--ll-accent); }
.ll-brand-sub { font-size: 12px; color: var(--ll-muted); }
.ll-eyebrow { font-size: 11px; letter-spacing: .14em; text-transform: uppercase; color: var(--ll-dim); font-weight: 600; margin: 6px 0 8px; }
.ll-status { display: flex; align-items: center; gap: 10px; background: #172119; border: 1px solid #23402C;
  border-radius: 12px; padding: 10px 13px; font-size: 13px; color: #BDEFD3; font-weight: 500; margin-bottom: 6px; }
.ll-status.warn { background: #241C14; border-color: #4A3820; color: #F5D9A0; }
.ll-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--ll-good); flex: 0 0 auto; }
.ll-status.warn .ll-dot { background: #F5C26B; }
.ll-meter-row { display: flex; justify-content: space-between; font-size: 12px; color: var(--ll-muted); margin-bottom: 6px; }
.ll-meter-row span:last-child { font-family: 'JetBrains Mono', monospace; }
.ll-meter { height: 6px; border-radius: 999px; background: #22252E; overflow: hidden; margin-bottom: 10px; }
.ll-meter > div { height: 6px; background: var(--ll-accent); border-radius: 999px; }

/* ---------- inputs ---------- */
[data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea {
  background: var(--ll-sunken) !important; border-radius: 12px !important; color: var(--ll-text) !important;
}
[data-testid="stTextInput"] > div > div, [data-testid="stTextArea"] > div > div { border-radius: 12px !important; border-color: var(--ll-line-2) !important; }
[data-baseweb="select"] > div { border-radius: 10px !important; background: var(--ll-surface-2) !important; border-color: var(--ll-line-2) !important; }
[data-baseweb="tag"] { background: var(--ll-accent-soft) !important; border: 1px solid #4A2A24; border-radius: 999px !important; }
[data-baseweb="tag"] span { color: var(--ll-accent-text) !important; }

/* ---------- buttons ---------- */
.stButton > button, .stDownloadButton > button, [data-testid="stFormSubmitButton"] > button {
  border-radius: 12px; min-height: 44px; font-weight: 500; border: 1px solid var(--ll-line-2);
  background: var(--ll-surface); color: var(--ll-text); transition: border-color .15s, background .15s;
}
.stButton > button:hover, .stDownloadButton > button:hover { border-color: #4A4F5C; background: var(--ll-surface-2); color: var(--ll-text); }
[data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primaryFormSubmit"] {
  background: var(--ll-accent) !important; border-color: var(--ll-accent) !important; color: var(--ll-accent-ink) !important;
  font-family: 'Space Grotesk', sans-serif !important; font-weight: 600 !important;
}
[data-testid="stBaseButton-primary"] p, [data-testid="stBaseButton-primaryFormSubmit"] p { color: var(--ll-accent-ink) !important; font-weight: 600; }
[data-testid="stBaseButton-primary"]:hover, [data-testid="stBaseButton-primaryFormSubmit"]:hover { filter: brightness(1.07); }

/* ---------- tabs as pills ---------- */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
  gap: 4px; background: #121318; border: 1px solid var(--ll-line); border-radius: 16px; padding: 6px; flex-wrap: wrap;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
  height: auto; padding: 9px 16px; border-radius: 11px; background: transparent; color: var(--ll-muted);
}
[data-testid="stTabs"] [data-baseweb="tab"] p { font-size: 14px; font-weight: 500; }
[data-testid="stTabs"] [aria-selected="true"] { background: #262934; color: var(--ll-text); }
[data-testid="stTabs"] [aria-selected="true"] p { font-weight: 600; }
[data-testid="stTabs"] [data-baseweb="tab-highlight"], [data-testid="stTabs"] [data-baseweb="tab-border"] { display: none; }
[data-testid="stTabs"] [data-baseweb="tab-panel"] { padding-top: 22px; }
/* tabs nested inside a tab (notes sections) stay as quiet underline tabs */
[data-baseweb="tab-panel"] [data-testid="stTabs"] [data-baseweb="tab-list"] { background: transparent; border: none; border-bottom: 1px solid var(--ll-line); border-radius: 0; padding: 0; gap: 22px; }
[data-baseweb="tab-panel"] [data-testid="stTabs"] [data-baseweb="tab"] { padding: 0 0 12px; border-radius: 0; }
[data-baseweb="tab-panel"] [data-testid="stTabs"] [aria-selected="true"] { background: transparent; box-shadow: inset 0 -2px 0 var(--ll-accent); }

/* ---------- cards, containers, metrics ---------- */
[data-testid="stVerticalBlockBorderWrapper"] { border-radius: 20px; border-color: var(--ll-line) !important; background: var(--ll-surface); }
[data-testid="stExpander"] details { border-radius: 14px; border-color: var(--ll-line) !important; background: var(--ll-surface); }
[data-testid="stMetric"] { background: var(--ll-sunken); border: 1px solid var(--ll-line); border-radius: 14px; padding: 12px 14px; }
[data-testid="stMetricLabel"] p { color: var(--ll-muted); font-size: 12px; }
[data-testid="stMetricValue"] { font-size: 1.3rem; font-weight: 500; }
[data-testid="stAlert"] { border-radius: 14px; }
[data-testid="stProgress"] > div > div > div { background: #22252E; }
[data-testid="stProgress"] > div > div > div > div { background: var(--ll-accent); }
[data-testid="stDataFrame"] { border-radius: 14px; overflow: hidden; border: 1px solid var(--ll-line); }

/* ---------- chat ---------- */
[data-testid="stChatMessage"] { background: #181A21; border: 1px solid #262A34; border-radius: 6px 18px 18px 18px; padding: 14px 18px; }
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]), [data-testid="stChatMessage"]:has([aria-label="Chat message from user"]) {
  background: var(--ll-accent-soft); border-color: #4A2A24; border-radius: 18px 18px 6px 18px;
}
[data-testid="stChatInput"] { border-radius: 16px; }
[data-testid="stChatInput"] textarea { font-family: 'IBM Plex Sans', sans-serif; }

/* ---------- landing ---------- */
.hero { padding: 1.6rem 0 1.2rem; max-width: 860px; }
.hero-pill { display: inline-flex; align-items: center; gap: 8px; font-size: 13px; padding: 7px 14px; border-radius: 999px;
  background: var(--ll-surface-2); border: 1px solid var(--ll-line-2); color: #C9CDD6; margin-bottom: 22px; }
.hero-pill i { width: 6px; height: 6px; border-radius: 50%; background: var(--ll-accent); display: inline-block; }
.hero h1 { font-size: clamp(2.4rem, 5.2vw, 4.1rem); line-height: 1.03; letter-spacing: -0.035em; font-weight: 600; margin: 0 0 18px; padding: 0; }
.hero h1 .accent { color: var(--ll-accent); }
.hero p { font-size: 1.15rem; line-height: 1.6; color: var(--ll-muted); margin: 0; max-width: 640px; }
.ll-hint { display: flex; gap: 14px; flex-wrap: wrap; font-size: 13px; color: var(--ll-dim); margin: 2px 2px 8px; }
.ll-steps { display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 14px; margin: 30px 0 44px; }
.ll-step { display: flex; gap: 14px; padding: 20px; border-radius: 18px; background: #121318; border: 1px solid #1F222A; }
.ll-step b { font-family: 'JetBrains Mono', monospace; font-weight: 500; font-size: 13px; color: var(--ll-accent); padding-top: 3px; }
.ll-step strong { display: block; font-family: 'Space Grotesk', sans-serif; font-weight: 600; font-size: 16px; color: var(--ll-text); margin-bottom: 4px; }
.ll-step span { font-size: 14px; line-height: 1.55; color: var(--ll-muted); }
.ll-section-head { display: flex; justify-content: space-between; align-items: flex-end; flex-wrap: wrap; gap: 10px; margin-bottom: 16px; }
.ll-section-head h2 { margin: 0; padding: 0; font-size: 1.75rem; font-weight: 600; }
.ll-section-head span { font-size: 14px; color: var(--ll-dim); }
.ll-features { display: grid; grid-template-columns: repeat(auto-fit, minmax(270px, 1fr)); gap: 16px; }
.feature-card { padding: 24px; border-radius: 20px; background: var(--ll-surface); border: 1px solid var(--ll-line); display: flex; flex-direction: column; gap: 12px; }
.feature-card .icon { width: 44px; height: 44px; border-radius: 12px; display: flex; align-items: center; justify-content: center; }
.feature-card h4 { margin: 0; padding: 0; font-size: 18px; font-weight: 600; color: var(--ll-text); }
.feature-card p { margin: 0; color: var(--ll-muted); font-size: 14px; line-height: 1.6; }

/* ---------- video workspace ---------- */
.video-title { font-family: 'Space Grotesk', sans-serif; font-size: 1.7rem; font-weight: 600; line-height: 1.15; letter-spacing: -0.02em; margin: 6px 0 4px; color: var(--ll-text); }
.video-sub { color: var(--ll-muted); margin-bottom: 14px; font-size: 14px; }
.badge { display: inline-block; padding: 4px 11px; border-radius: 999px; font-size: 12px; font-weight: 600;
  background: var(--ll-accent-soft); color: var(--ll-accent-text); margin-right: 6px; }
.badge.neutral { background: #1E2129; color: #C9CDD6; }
.ll-stats { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; margin: 18px 0 6px; }
.ll-stat { background: var(--ll-sunken); border: 1px solid var(--ll-line); border-radius: 14px; padding: 13px 14px; }
.ll-stat small { display: block; font-size: 12px; color: var(--ll-muted); margin-bottom: 3px; }
.ll-stat b { font-family: 'JetBrains Mono', monospace; font-size: 19px; font-weight: 500; color: var(--ll-text); }
[data-testid="stVideo"], iframe[title="st.video"] { border-radius: 20px; overflow: hidden; border: 1px solid var(--ll-line); }

/* ---------- flashcards ---------- */
.ll-deck { position: relative; padding-top: 16px; }
.ll-deck::before, .ll-deck::after { content: ""; position: absolute; height: 40px; border-radius: 22px; border: 1px solid var(--ll-line); }
.ll-deck::before { left: 28px; right: 28px; top: 0; background: var(--ll-surface); }
.ll-deck::after { left: 14px; right: 14px; top: 8px; background: #181A21; }
.flashcard { position: relative; z-index: 1; min-height: 260px; border-radius: 24px; background: #181A21; border: 1px solid var(--ll-line-2);
  padding: 30px 36px; display: flex; flex-direction: column; justify-content: center; gap: 14px; box-shadow: 0 24px 60px rgba(0,0,0,.45); }
.flashcard.back { background: #1E1718; border-color: #4A2A24; }
.flashcard .face-label { font-size: 12px; letter-spacing: .16em; text-transform: uppercase; font-weight: 600; color: var(--ll-dim); }
.flashcard.back .face-label { color: var(--ll-accent-text); }
.flashcard .face-text { font-family: 'Space Grotesk', sans-serif; font-size: 1.55rem; line-height: 1.4; font-weight: 500; color: var(--ll-text); }
.flashcard.back .face-text { color: #FFF1EE; }

.chapter-time { font-family: 'JetBrains Mono', monospace; }
.small-muted { font-size: .85rem; color: var(--ll-dim); }
</style>
"""


def inject_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)
