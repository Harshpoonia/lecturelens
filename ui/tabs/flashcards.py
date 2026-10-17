"""
ui/tabs/flashcards.py

Flashcard study mode: flip, navigate, shuffle, and mark cards as
known / still learning, with a "still learning only" review filter.
"""

from __future__ import annotations

import html
import random

import streamlit as st

from models.flashcard import Flashcard
from models.transcript import TranscriptData
from modules.ai_service import AIServiceError
from ui import services
from ui.components import ai_error_card
from ui.services import AIConfig


def render_flashcards_tab(cfg: AIConfig, t: TranscriptData) -> None:
    cards: list[Flashcard] | None = st.session_state.flashcards
    if not cards:
        _render_setup(cfg, t)
        return

    known: set[int] = st.session_state.fc_known
    only_learning = st.toggle("Review only cards I'm still learning", key="fc_only_learning_toggle",
                              value=st.session_state.fc_only_learning)
    if only_learning != st.session_state.fc_only_learning:
        st.session_state.fc_only_learning = only_learning
        st.session_state.fc_pos = 0
        st.session_state.fc_flipped = False

    deck = [i for i in st.session_state.fc_order if not (only_learning and i in known)]
    st.progress(len(known) / len(cards), text=f"Mastered {len(known)} of {len(cards)} cards")

    if not deck:
        st.success("You've mastered every card in this deck!", icon=":material/celebration:")
        if st.button("Reset progress"):
            st.session_state.fc_known = set()
            st.rerun()
        return

    pos = min(st.session_state.fc_pos, len(deck) - 1)
    st.session_state.fc_pos = pos
    card = cards[deck[pos]]
    flipped = st.session_state.fc_flipped

    caption = [f"Card {pos + 1} of {len(deck)}", card.topic]
    if card.difficulty:
        caption.append(card.difficulty)
    if deck[pos] in known:
        caption.append("known")
    st.caption(" · ".join(caption))

    face = html.escape(card.back if flipped else card.front).replace("\n", "<br>")
    st.markdown(
        f'<div class="ll-deck"><div class="flashcard {"back" if flipped else ""}">'
        f'<div class="face-label">{"Answer" if flipped else "Question"}</div>'
        f'<div class="face-text">{face}</div></div></div>',
        unsafe_allow_html=True,
    )
    st.write("")

    c1, c2, c3, c4 = st.columns(4)
    if c1.button("Previous", disabled=pos == 0, width="stretch", icon=":material/arrow_back:"):
        _move(-1)
    if c2.button("Flip", type="primary", width="stretch", icon=":material/flip:"):
        st.session_state.fc_flipped = not flipped
        st.rerun()
    if c3.button("Next", disabled=pos >= len(deck) - 1, width="stretch", icon=":material/arrow_forward:"):
        _move(1)
    if c4.button("Shuffle", width="stretch", icon=":material/shuffle:"):
        random.shuffle(st.session_state.fc_order)
        st.session_state.fc_pos = 0
        st.session_state.fc_flipped = False
        st.rerun()

    if flipped:
        k1, k2 = st.columns(2)
        if k1.button("I knew it", width="stretch", icon=":material/check_circle:"):
            known.add(deck[pos])
            _advance_after_mark(deck, pos, only_learning)
        if k2.button("Still learning", width="stretch", icon=":material/replay:"):
            known.discard(deck[pos])
            _advance_after_mark(deck, pos, only_learning)
    else:
        st.caption("Flip the card, then mark whether you knew it.")

    with st.expander("Deck options"):
        n = st.slider("Cards in a new deck", 5, 30, len(cards), key="fc_n_regen")
        if st.button("Generate a new deck", icon=":material/auto_awesome:"):
            st.session_state.fc_nonce += 1
            _generate(cfg, t, n)


def _move(step: int) -> None:
    st.session_state.fc_pos += step
    st.session_state.fc_flipped = False
    st.rerun()


def _advance_after_mark(deck: list[int], pos: int, only_learning: bool) -> None:
    st.session_state.fc_flipped = False
    # When filtering, the marked card leaves the deck, so the position already points at the next one.
    if not (only_learning and deck[pos] in st.session_state.fc_known):
        st.session_state.fc_pos = min(pos + 1, len(deck) - 1)
    st.rerun()


def _render_setup(cfg: AIConfig, t: TranscriptData) -> None:
    st.markdown("Turn the video into a flashcard deck for spaced revision.")
    n = st.slider("Number of flashcards", 5, 30, 12, key="fc_n")
    if st.button("Generate flashcards", type="primary", icon=":material/style:"):
        _generate(cfg, t, n)


def _generate(cfg: AIConfig, t: TranscriptData, n: int) -> None:
    try:
        with st.spinner("Making flashcards…"):
            cards = services.flashcards(cfg, t, n, st.session_state.fc_nonce)
    except AIServiceError as exc:
        ai_error_card(exc)
        return
    except ValueError as exc:
        st.error(f"The flashcards came back in an unexpected format. Please try again. ({exc})")
        return
    st.session_state.flashcards = cards
    st.session_state.fc_order = list(range(len(cards)))
    st.session_state.fc_pos = 0
    st.session_state.fc_flipped = False
    st.session_state.fc_known = set()
    st.rerun()
