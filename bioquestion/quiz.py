"""Step 2: Generate quiz questions from knowledge points."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from bioquestion.llm import LLMClient
from bioquestion.prompts import QUIZ_SYSTEM
from bioquestion.schemas import (
    KnowledgeExtractionResult,
    MultipleChoiceQuestion,
    QuizResult,
    ShortAnswerQuestion,
)


class _QuizLLMResponse(BaseModel):
    questions: list[MultipleChoiceQuestion | ShortAnswerQuestion] = Field(
        default_factory=list
    )


def generate_quiz(
    knowledge: KnowledgeExtractionResult,
    llm: LLMClient | None = None,
) -> QuizResult:
    if not knowledge.has_substantive_content or not knowledge.knowledge_points:
        raise ValueError("Knowledge points are empty or lack substantive content; cannot generate quiz.")

    client = llm or LLMClient()
    payload = {
        "entities": knowledge.entities,
        "knowledge_points": [kp.model_dump(mode="json") for kp in knowledge.knowledge_points],
        "summary": knowledge.summary,
    }
    response = client.complete_json(
        QUIZ_SYSTEM,
        f"Generate questions based on the following knowledge points:\n\n{json.dumps(payload, ensure_ascii=False, indent=2)}",
        _QuizLLMResponse,
    )

    mc_count = sum(1 for q in response.questions if q.type == "multiple_choice")
    sa_count = sum(1 for q in response.questions if q.type == "short_answer")
    if mc_count != 3 or sa_count != 2:
        raise ValueError(
            f"Invalid question count: multi-select {mc_count}/3, short-answer {sa_count}/2."
        )

    return QuizResult(
        knowledge_source=knowledge.source_text_preview,
        questions=response.questions,
    )


def save_quiz(result: QuizResult, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_quiz(path: Path) -> QuizResult:
    data = json.loads(path.read_text(encoding="utf-8"))
    return QuizResult.model_validate(data)
