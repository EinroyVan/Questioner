"""Step 3: Grade user answers against quiz standard answers."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from bioquestion.llm import LLMClient
from bioquestion.prompts import GRADE_SYSTEM
from bioquestion.schemas import GradingReport, QuestionGradingResult, QuizResult, UserAnswerSheet


class _GradeLLMResponse(BaseModel):
    total_score: float
    percentage: float
    summary: str = ""
    question_results: list[QuestionGradingResult] = Field(default_factory=list)


def grade_answers(
    quiz: QuizResult,
    answers: UserAnswerSheet,
    llm: LLMClient | None = None,
) -> GradingReport:
    client = llm or LLMClient()
    payload = {
        "quiz": quiz.model_dump(mode="json"),
        "user_answers": answers.model_dump(mode="json"),
    }
    response = client.complete_json(
        GRADE_SYSTEM,
        f"Grade the following submission:\n\n{json.dumps(payload, ensure_ascii=False, indent=2)}",
        _GradeLLMResponse,
    )
    return GradingReport(
        total_score=response.total_score,
        max_score=100.0,
        percentage=response.percentage,
        summary=response.summary,
        question_results=response.question_results,
    )


def save_report(report: GradingReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_answers(path: Path) -> UserAnswerSheet:
    data = json.loads(path.read_text(encoding="utf-8"))
    return UserAnswerSheet.model_validate(data)
