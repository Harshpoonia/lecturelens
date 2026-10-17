"""
ui/tabs/quiz.py

Interactive quiz: choose size and difficulty, answer one question at a
time with instant feedback, review mistakes and retry only those.
"""

from __future__ import annotations

import streamlit as st

from models.quiz import QuizAnswer, QuizQuestion
from models.transcript import TranscriptData
from modules.ai_service import AIServiceError
from modules.quiz_service import DIFFICULTY_LEVELS
from ui import services
from ui.components import ai_error_card, jump_buttons
from ui.services import AIConfig
from utils.time_utils import format_timestamp


def render_quiz_tab(cfg: AIConfig, t: TranscriptData) -> None:
    questions: list[QuizQuestion] | None = st.session_state.quiz
    if not questions:
        _render_setup(cfg, t)
        return

    order: list[int] = st.session_state.quiz_order
    pos: int = st.session_state.quiz_pos
    if pos >= len(order):
        _render_results(t, questions)
        return

    q_index = order[pos]
    question = questions[q_index]
    round_label = " · Retry round" if st.session_state.quiz_round else ""
    st.progress(pos / len(order), text=f"Question {pos + 1} of {len(order)}{round_label}")

    meta = " · ".join(x for x in (question.difficulty,) if x)
    if meta:
        st.caption(meta)
    st.markdown(f"#### {question.question}")

    submitted = st.session_state.quiz_submitted
    selected = st.radio(
        "Choose an answer",
        question.options,
        index=None,
        key=f"quiz_{st.session_state.run_id}_{st.session_state.quiz_nonce}_{st.session_state.quiz_round}_{pos}",
        disabled=submitted,
        label_visibility="collapsed",
    )

    if not submitted:
        if st.button("Check answer", type="primary", disabled=selected is None, key=f"quiz_check_{pos}"):
            correct = question.is_correct(selected)
            st.session_state.quiz_answers.append(QuizAnswer(q_index, selected, correct))
            st.session_state.quiz_submitted = True
            st.session_state.quiz_selected = selected
            st.rerun()
        return

    if question.is_correct(st.session_state.quiz_selected):
        st.success("Correct! 🎉")
    else:
        st.error(f"Not quite. The correct answer is **{question.correct_answer}**.")
    if question.explanation:
        st.info(question.explanation, icon="💡")
    if question.timestamp_seconds is not None and t.is_youtube:
        st.caption(f"Explained in the video around {format_timestamp(question.timestamp_seconds)}:")
        jump_buttons([question.timestamp_seconds], f"quizjump_{pos}", t.duration_seconds)

    last = pos == len(order) - 1
    if st.button("See results →" if last else "Next question →", type="primary", key=f"quiz_next_{pos}"):
        st.session_state.quiz_pos += 1
        st.session_state.quiz_submitted = False
        st.session_state.quiz_selected = None
        st.rerun()


def _render_setup(cfg: AIConfig, t: TranscriptData) -> None:
    st.markdown("Test yourself on this video. Questions are spread across the whole video and come with explanations.")
    col_n, col_d = st.columns(2)
    n = col_n.slider("Number of questions", 3, 15, 5, key="quiz_n")
    difficulty = col_d.selectbox("Difficulty", DIFFICULTY_LEVELS, key="quiz_difficulty")
    if st.button("📝 Generate quiz", type="primary", key="quiz_generate"):
        try:
            with st.spinner("Writing questions…"):
                questions = services.quiz(cfg, t, n, difficulty, st.session_state.quiz_nonce)
        except AIServiceError as exc:
            ai_error_card(exc)
            return
        except ValueError as exc:
            st.error(f"The quiz came back in an unexpected format. Please try again. ({exc})")
            return
        _start_round(questions, list(range(len(questions))))
        st.session_state.quiz = questions
        st.rerun()


def _start_round(questions: list[QuizQuestion], order: list[int], retry: bool = False) -> None:
    st.session_state.quiz_order = order
    st.session_state.quiz_pos = 0
    st.session_state.quiz_answers = []
    st.session_state.quiz_submitted = False
    st.session_state.quiz_selected = None
    st.session_state.quiz_round = st.session_state.quiz_round + 1 if retry else 0


def _render_results(t: TranscriptData, questions: list[QuizQuestion]) -> None:
    answers: list[QuizAnswer] = st.session_state.quiz_answers
    if st.session_state.quiz_round == 0:
        st.session_state.quiz_report = list(answers)
    total = len(answers)
    correct = sum(a.is_correct for a in answers)
    percent = round(100 * correct / total) if total else 0

    if percent == 100:
        st.balloons()
    headline = "Perfect score! 🏆" if percent == 100 else "Great work! 💪" if percent >= 70 else "Keep going — review and retry 📚"
    st.markdown(f"### {headline}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Score", f"{correct} / {total}")
    c2.metric("Accuracy", f"{percent}%")
    c3.metric("To review", total - correct)

    wrong = [a for a in answers if not a.is_correct]
    if wrong:
        st.markdown("#### Review what you missed")
        for a in wrong:
            q = questions[a.question_index]
            with st.expander(f"❌ {q.question}"):
                st.markdown(f"- Your answer: {a.selected_option}\n- Correct: **{q.correct_answer}**")
                if q.explanation:
                    st.markdown(f"- Why: {q.explanation}")
                if q.timestamp_seconds is not None and t.is_youtube:
                    jump_buttons([q.timestamp_seconds], f"reviewjump_{a.question_index}", t.duration_seconds)

    col_a, col_b, col_c = st.columns(3)
    if wrong and col_a.button("🔁 Retry missed questions", type="primary", width="stretch"):
        _start_round(questions, [a.question_index for a in wrong], retry=True)
        st.rerun()
    if col_b.button("↺ Restart quiz", width="stretch"):
        _start_round(questions, list(range(len(questions))))
        st.rerun()
    if col_c.button("✨ New quiz", width="stretch"):
        st.session_state.quiz = None
        st.session_state.quiz_nonce += 1
        st.rerun()
