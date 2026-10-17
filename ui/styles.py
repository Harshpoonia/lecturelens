"""
ui/styles.py

Small CSS layer on top of the Streamlit theme (.streamlit/config.toml).
Colours use translucent values so they read well in light and dark mode.
"""

import streamlit as st

_CSS = """
<style>
.block-container { padding-top: 2rem; padding-bottom: 4rem; max-width: 1200px; }

.hero { padding: 0.25rem 0 0.75rem 0; }
.hero h1 { font-size: 2.35rem; line-height: 1.15; margin: 0 0 .35rem 0; font-weight: 800; letter-spacing: -0.02em; }
.hero h1 .accent { color: #E5484D; }
.hero p { font-size: 1.08rem; opacity: .78; margin: 0; }
.hero .hero-kicker { font-size: .78rem; letter-spacing: .14em; text-transform: uppercase; font-weight: 600; opacity: .6; margin-bottom: .4rem; }

.feature-card { border: 1px solid rgba(128,128,128,.22); border-radius: 14px; padding: 1rem 1.1rem;
                height: 100%; background: rgba(128,128,128,.04); }
.feature-card .icon { font-size: 1.5rem; }
.feature-card h4 { margin: .35rem 0 .2rem 0; font-size: 1rem; }
.feature-card p { margin: 0; opacity: .75; font-size: .9rem; line-height: 1.45; }

.video-title { font-size: 1.35rem; font-weight: 700; line-height: 1.3; margin: 0 0 .15rem 0; }
.video-sub { opacity: .7; margin-bottom: .6rem; }
.badge { display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: .78rem; font-weight: 600;
         background: rgba(229,72,77,.12); color: #E5484D; margin-right: 6px; }
.badge.neutral { background: rgba(128,128,128,.14); color: inherit; }

.flashcard { border: 1px solid rgba(128,128,128,.28); border-radius: 18px; min-height: 220px;
             display: flex; flex-direction: column; justify-content: center; align-items: center;
             padding: 2rem 2.2rem; text-align: center; background: rgba(128,128,128,.05);
             box-shadow: 0 6px 24px rgba(0,0,0,.06); }
.flashcard.back { background: rgba(229,72,77,.06); border-color: rgba(229,72,77,.35); }
.flashcard .face-label { font-size: .72rem; text-transform: uppercase; letter-spacing: .12em; opacity: .55; margin-bottom: .8rem; }
.flashcard .face-text { font-size: 1.3rem; line-height: 1.5; font-weight: 500; }

.chapter-time { font-variant-numeric: tabular-nums; }
div[data-testid="stMetricValue"] { font-size: 1.35rem; }
.small-muted { font-size: .85rem; opacity: .65; }
</style>
"""


def inject_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)
