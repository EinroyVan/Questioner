"""Streamlit web UI for the biomedical literature learning workflow."""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import json
import os
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv

_ENV_FILE = _PROJECT_ROOT / ".env"
load_dotenv(_ENV_FILE, override=False)

from bioquestion.extract import extract_knowledge, save_knowledge
from bioquestion.pdf_reader import load_uploaded_document
from bioquestion.grade import grade_answers, save_report
from bioquestion.llm import LLMClient
from bioquestion.quiz import generate_quiz, save_quiz
from bioquestion.schemas import (
    GradingReport,
    KnowledgeExtractionResult,
    MultipleChoiceQuestion,
    QuizResult,
    ShortAnswerQuestion,
    UserAnswer,
    UserAnswerSheet,
)

STEPS = [
    "Literature Input",
    "Knowledge Points",
    "Quiz",
    "Grading",
]

CATEGORY_LABELS = {
    "entity": "Entity",
    "mechanism": "Mechanism",
    "finding": "Finding",
}

OUTPUT_DIR = Path("output")


def _init_session() -> None:
    defaults = {
        "step": 0,
        "source_text": "",
        "pdf_meta": None,
        "knowledge": None,
        "quiz": None,
        "report": None,
        "answers_submitted": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _go_to_step(step: int) -> None:
    st.session_state.step = step
    st.rerun()


def _get_llm(model: str) -> LLMClient:
    return LLMClient(model=model or None)


def _persist_outputs(
    knowledge: KnowledgeExtractionResult | None,
    quiz: QuizResult | None,
    report: GradingReport | None,
) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if knowledge:
        save_knowledge(knowledge, OUTPUT_DIR / "knowledge.json")
    if quiz:
        save_quiz(quiz, OUTPUT_DIR / "quiz.json")
    if report:
        save_report(report, OUTPUT_DIR / "grading.json")


def _render_sidebar() -> str:
    st.sidebar.title("BioQuestion")
    st.sidebar.caption("Extract → Quiz → Grade")

    default_model = os.getenv("GOOGLE_MODEL", "gemini-3.5-flash")
    model = st.sidebar.text_input("Model", value=default_model)
    if os.getenv("GOOGLE_API_KEY"):
        st.sidebar.success("Google API configured")
    else:
        st.sidebar.error("GOOGLE_API_KEY not detected")
        st.sidebar.caption(f"Set it in `{_ENV_FILE}` (copy from `.env.example`).")

    st.sidebar.divider()
    st.sidebar.caption("Workflow")
    selected = st.sidebar.radio(
        "Workflow step",
        options=list(range(len(STEPS))),
        format_func=lambda i: f"{i + 1}. {STEPS[i]}",
        index=st.session_state.step,
        label_visibility="collapsed",
    )
    if selected != st.session_state.step:
        st.session_state.step = selected
        st.rerun()

    return model


def _step_input(model: str) -> None:
    st.header(f"Step 1 · {STEPS[0]}")
    st.write(
        "Upload a `.txt` or `.pdf` file, or paste a biomedical literature excerpt. "
        "Scanned PDFs are processed with OCR automatically."
    )

    uploaded = st.file_uploader("Upload document", type=["txt", "pdf"])
    use_ocr = st.checkbox("Enable OCR for scanned PDFs (recommended)", value=True)
    pasted = st.text_area(
        "Or paste text",
        value=st.session_state.source_text,
        height=280,
        placeholder="Paste abstract, results, or discussion sections…",
    )

    if uploaded is not None:
        if uploaded.type == "application/pdf" or uploaded.name.lower().endswith(".pdf"):
            progress = st.progress(0.0, text="Parsing PDF…")
            status = st.empty()

            def on_progress(current: int, total: int, mode: str) -> None:
                label = "OCR" if mode == "ocr" else "Text extraction"
                progress.progress(current / total, text=f"{label}: page {current}/{total}")
                status.caption(f"Processing page {current} ({label})")

            try:
                text, pdf_meta = load_uploaded_document(
                    uploaded.name,
                    uploaded.getvalue(),
                    use_ocr=use_ocr,
                    on_progress=on_progress,
                )
            except Exception as exc:
                progress.empty()
                status.empty()
                st.error(f"PDF parsing failed: {exc}")
                return

            progress.progress(1.0, text="PDF parsing complete")
            status.empty()
            st.session_state.pdf_meta = pdf_meta
            pasted = text
            st.success(pdf_meta.summary if pdf_meta else "PDF parsing complete")
            with st.expander("Preview extracted text", expanded=False):
                preview = text[:3000] + ("…" if len(text) > 3000 else "")
                st.text(preview)
        else:
            st.session_state.pdf_meta = None
            pasted = uploaded.read().decode("utf-8", errors="replace")

    col1, col2 = st.columns(2)
    with col1:
        extract_btn = st.button("Extract Knowledge Points", type="primary", use_container_width=True)
    with col2:
        reset_btn = st.button("Reset Session", use_container_width=True)

    if reset_btn:
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    if extract_btn:
        text = pasted.strip()
        if not text:
            st.warning("Please enter or upload literature content first.")
            return
        with st.spinner("Extracting knowledge points with Gemini…"):
            try:
                knowledge = extract_knowledge(text, _get_llm(model))
            except Exception as exc:
                st.error(f"Extraction failed: {exc}")
                return

        st.session_state.source_text = text
        st.session_state.knowledge = knowledge
        st.session_state.quiz = None
        st.session_state.report = None
        st.session_state.answers_submitted = False
        _persist_outputs(knowledge, None, None)

        if not knowledge.has_substantive_content:
            st.warning("No key knowledge points found.")
            return

        st.session_state.step = 1
        st.rerun()


def _step_knowledge(model: str) -> None:
    st.header(f"Step 2 · {STEPS[1]}")
    knowledge: KnowledgeExtractionResult | None = st.session_state.knowledge
    if not knowledge:
        st.info("Extract knowledge points on the Literature Input step first.")
        if st.button("← Back to Literature Input"):
            _go_to_step(0)
        return

    if not knowledge.has_substantive_content:
        st.warning("No key knowledge points found")
        if knowledge.summary:
            st.write(knowledge.summary)
        return

    st.subheader("Summary")
    st.info(knowledge.summary)

    if knowledge.entities:
        st.subheader("Core Entities")
        st.write(", ".join(knowledge.entities))

    st.subheader("Knowledge Points")
    for kp in knowledge.knowledge_points:
        label = CATEGORY_LABELS.get(kp.category.value, kp.category.value)
        with st.expander(f"**{kp.id}** · {label} · {kp.title}", expanded=False):
            st.markdown(kp.content)
            st.caption(f"Source quote: {kp.source_quote}")

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("← Back"):
            _go_to_step(0)
    with col2:
        generate_btn = st.button("Generate Quiz", type="primary", use_container_width=True)

    if generate_btn:
        with st.spinner("Generating 3 multi-select + 2 short-answer questions…"):
            try:
                quiz = generate_quiz(knowledge, _get_llm(model))
            except Exception as exc:
                st.error(f"Quiz generation failed: {exc}")
                return
        st.session_state.quiz = quiz
        st.session_state.report = None
        st.session_state.answers_submitted = False
        _persist_outputs(knowledge, quiz, None)
        st.session_state.step = 2
        st.rerun()


def _step_quiz(model: str) -> None:
    st.header(f"Step 3 · {STEPS[2]}")
    quiz: QuizResult | None = st.session_state.quiz
    if not quiz:
        st.info("Generate a quiz on the Knowledge Points step first.")
        if st.button("← Back to Knowledge Points"):
            _go_to_step(1)
        return

    st.caption("Multi-select questions allow multiple options. Use full sentences for short answers.")
    answers: list[UserAnswer] = []

    for q in quiz.questions:
        st.markdown(f"### {q.id}")
        if isinstance(q, MultipleChoiceQuestion):
            st.markdown(q.stem)
            option_labels = [f"{k}. {q.options[k]}" for k in sorted(q.options)]
            label_to_key = {f"{k}. {q.options[k]}": k for k in sorted(q.options)}
            selected_labels = st.multiselect(
                "Select answer(s)",
                options=option_labels,
                key=f"mc_{q.id}",
                label_visibility="collapsed",
            )
            selected = sorted(label_to_key[label] for label in selected_labels)
            answers.append(UserAnswer(question_id=q.id, answer=selected))
        elif isinstance(q, ShortAnswerQuestion):
            st.markdown(q.stem)
            text = st.text_area(
                "Your answer",
                key=f"sa_{q.id}",
                height=120,
                label_visibility="collapsed",
                placeholder="Address mechanism, experimental logic, or clinical significance…",
            )
            answers.append(UserAnswer(question_id=q.id, answer=text))

        st.divider()

    col1, col2 = st.columns(2)
    with col1:
        if st.button("← Back"):
            _go_to_step(1)
    with col2:
        submit_btn = st.button("Submit & Grade", type="primary", use_container_width=True)

    if submit_btn:
        empty_mc = [
            a.question_id
            for a in answers
            if isinstance(a.answer, list) and len(a.answer) == 0
        ]
        empty_sa = [
            a.question_id
            for a in answers
            if isinstance(a.answer, str) and not a.answer.strip()
        ]
        if empty_mc or empty_sa:
            st.warning(f"Please answer all questions. Unanswered: {', '.join(empty_mc + empty_sa)}")
            return

        sheet = UserAnswerSheet(answers=answers)
        with st.spinner("Grading…"):
            try:
                report = grade_answers(quiz, sheet, _get_llm(model))
            except Exception as exc:
                st.error(f"Grading failed: {exc}")
                return

        st.session_state.report = report
        st.session_state.answers_submitted = True
        answers_path = OUTPUT_DIR / "answers.json"
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        answers_path.write_text(
            json.dumps(sheet.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        _persist_outputs(st.session_state.knowledge, quiz, report)
        st.session_state.step = 3
        st.rerun()


def _step_grading() -> None:
    st.header(f"Step 4 · {STEPS[3]}")
    report: GradingReport | None = st.session_state.report
    quiz: QuizResult | None = st.session_state.quiz

    if not report:
        st.info("Submit your answers on the Quiz step first.")
        if st.button("← Back to Quiz"):
            _go_to_step(2)
        return

    st.metric("Total Score", f"{report.total_score:.1f} / {report.max_score:.0f}")
    st.progress(report.percentage / 100.0, text=f"Score: {report.percentage:.1f}%")
    st.subheader("Overall Assessment")
    st.write(report.summary)

    st.subheader("Question Details")
    quiz_map = {q.id: q for q in quiz.questions} if quiz else {}

    for item in report.question_results:
        verdict = "✅" if item.is_correct else "❌"
        if item.question_type.value == "short_answer" and item.short_answer_detail:
            if item.short_answer_detail.logic_complete:
                verdict = "✅ Logic complete"
            else:
                verdict = "⚠️ Incomplete"

        with st.expander(
            f"{item.question_id}  {verdict}  ({item.score:.0f}/{item.max_score:.0f} pts)",
            expanded=False,
        ):
            q = quiz_map.get(item.question_id)
            if q:
                st.markdown(f"**Question:** {q.stem}")

            if item.choice_detail:
                d = item.choice_detail
                c1, c2, c3 = st.columns(3)
                c1.write(f"Your answer: {', '.join(d.user_answers) or '(empty)'}")
                c2.write(f"Correct answer: {', '.join(d.correct_answers)}")
                if d.missed:
                    c3.error(f"Missed: {', '.join(d.missed)}")
                if d.extra:
                    c3.warning(f"Extra: {', '.join(d.extra)}")
                if d.wrong:
                    c3.error(f"Wrong: {', '.join(d.wrong)}")

            if item.short_answer_detail:
                d = item.short_answer_detail
                if d.matched_keywords:
                    st.success(f"Matched keywords: {', '.join(d.matched_keywords)}")
                if d.missing_keywords:
                    st.warning(f"Missing keywords: {', '.join(d.missing_keywords)}")
                if d.feedback:
                    st.info(d.feedback)
                if isinstance(q, ShortAnswerQuestion):
                    with st.popover("View model answer"):
                        st.write(q.standard_answer)
                        st.caption("Grading keywords: " + ", ".join(q.grading_keywords))

            st.markdown("**Explanation**")
            st.write(item.explanation)
            if item.references:
                for ref in item.references:
                    st.caption(f"[{ref.knowledge_point_id}] {ref.source_quote}")

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("← Back to Quiz"):
            _go_to_step(2)
    with col2:
        st.download_button(
            "Download Grading Report (JSON)",
            data=json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2),
            file_name=f"grading_{datetime.now():%Y%m%d_%H%M%S}.json",
            mime="application/json",
            use_container_width=True,
        )


def main() -> None:
    st.set_page_config(
        page_title="BioQuestion",
        page_icon="🧬",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _init_session()
    model = _render_sidebar()

    step = st.session_state.step
    if step == 0:
        _step_input(model)
    elif step == 1:
        _step_knowledge(model)
    elif step == 2:
        _step_quiz(model)
    else:
        _step_grading()


if __name__ == "__main__":
    main()
