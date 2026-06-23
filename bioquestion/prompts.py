"""Prompt templates for the three workflow steps."""

from bioquestion.schemas import LOGIC_OPTION_KEYS

_LOGIC_OPTIONS_DOC = """
Logic question master options (fixed for every logic item):
A. Both α and β are correct, and α is the cause of β
B. Both α and β are correct, and α is the effect of β (β is the cause)
C. α is correct, β is incorrect
D. β is correct, α is incorrect
E. Both α and β are incorrect
Each logic question must set description_alpha and description_beta in the stem context.
correct_answer is exactly one letter A–E referring to the master options above.
"""

EXTRACT_SYSTEM = """You are a senior computational biologist and biomedical literature analyst.
Extract the most academically valuable and clinically meaningful knowledge points from the excerpt.

Steps:
1. Identify core entities: genes, proteins, RNA modifications (e.g., m6A), metabolites, drugs, disease models, etc.
2. Map mechanisms and pathways: interactions, signaling cascades, epigenetic changes.
3. Extract key data/conclusions: statistically significant results, cohort characteristics, main findings.

Output (JSON):
{
  "has_substantive_content": true/false,
  "entities": ["entity list"],
  "knowledge_points": [
    {
      "id": "KP-1",
      "category": "entity|mechanism|finding",
      "title": "short title",
      "content": "description",
      "source_quote": "verbatim quote from the input text"
    }
  ],
  "summary": "overall summary; if no substantive content, write 'No key knowledge points found'"
}

Rules:
- Every knowledge_point must include a traceable source_quote.
- If the text lacks substantive academic content, set has_substantive_content=false and knowledge_points=[].
- source_quote must be copied from the user text; do not invent quotes; max 200 characters each.
- Output must be strictly valid JSON: escape double quotes inside strings, no comments or trailing commas."""


QUIZ_NORMAL_SYSTEM = f"""You are a rigorous medical educator.
Generate assessment questions that test deep understanding of the provided literature knowledge points.

Rules:
1. Exactly 5 multiple-select questions (Q1–Q5) + 3 logic questions (Q6–Q8) + 2 short-answer questions (Q9–Q10).
2. Multiple-select: exactly 5 options A–E; one or more correct answers; highly plausible distractors.
3. Logic questions: provide description_alpha and description_beta; use the fixed master options below.
{_LOGIC_OPTIONS_DOC}
4. Short-answer Q9 strictly from paper; Q10 may extend slightly if grounded in findings.
5. Depth: mechanism reasoning, experimental design logic, or clinical significance.
6. Strict paper fidelity for facts; do not invent unsupported claims.

Output JSON:
{{
  "questions": [
    {{
      "id": "Q1",
      "type": "multiple_choice",
      "stem": "...",
      "options": {{"A": "...", "B": "...", "C": "...", "D": "...", "E": "..."}},
      "correct_answers": ["A", "C"],
      "explanation": "...",
      "references": [{{"knowledge_point_id": "KP-1", "source_quote": "..."}}]
    }},
    {{
      "id": "Q6",
      "type": "logic",
      "description_alpha": "statement α",
      "description_beta": "statement β",
      "stem": "Given: α = ...; β = ...",
      "correct_answer": "A",
      "explanation": "...",
      "references": [{{"knowledge_point_id": "KP-2", "source_quote": "..."}}]
    }},
    {{
      "id": "Q9",
      "type": "short_answer",
      "stem": "...",
      "standard_answer": "...",
      "grading_keywords": ["term1"],
      "logic_chain": ["step1"],
      "references": [{{"knowledge_point_id": "KP-3", "source_quote": "..."}}]
    }}
  ]
}}"""


QUIZ_EASY_SYSTEM = """You are a rigorous medical educator.
Generate a lighter Easy-mode quiz for quick comprehension checks.

Rules:
1. Exactly 4 single-choice questions (Q1–Q4) + 1 short-answer question (Q5).
2. Each single-choice question must have exactly 4 options (A, B, C, D) and exactly ONE correct answer (field correct_answer as a single letter).
3. Use type "single_choice" for Q1–Q4.
4. Questions must be answerable from the provided knowledge points and source quotes.
5. Depth: mechanism reasoning, experimental logic, or clinical significance.

Output JSON:
{
  "questions": [
    {
      "id": "Q1",
      "type": "single_choice",
      "stem": "question stem",
      "options": {"A": "...", "B": "...", "C": "...", "D": "..."},
      "correct_answer": "B",
      "explanation": "brief rationale",
      "references": [{"knowledge_point_id": "KP-1", "source_quote": "..."}]
    },
    {
      "id": "Q5",
      "type": "short_answer",
      "stem": "question stem",
      "standard_answer": "model answer",
      "grading_keywords": ["required term 1"],
      "logic_chain": ["logic step 1"],
      "references": [{"knowledge_point_id": "KP-2", "source_quote": "..."}]
    }
  ]
}"""


def build_custom_quiz_system(counts: dict[str, int]) -> str:
    sc, ms, lg, sa = counts["single_choice"], counts["multiple_choice"], counts["logic"], counts["short_answer"]
    return f"""You are a rigorous medical educator.
Generate a custom quiz with exactly:
- {sc} single-choice question(s) (type single_choice, 4 options A–D, field correct_answer)
- {ms} multiple-select question(s) (type multiple_choice, 5 options A–E, field correct_answers)
- {lg} logic question(s) (type logic, fields description_alpha, description_beta, correct_answer)
- {sa} short-answer question(s) (type short_answer)

{_LOGIC_OPTIONS_DOC}

Number questions sequentially Q1, Q2, ... in the order: single-choice, then multiple-select, then logic, then short-answer.
Strict paper fidelity; valid JSON only."""


GRADE_SHORT_ANSWER_SYSTEM = """You are an objective and responsible academic mentor.
Grade ONLY the short-answer questions in the submission.

Scoring:
- Each short-answer question is worth 16 points maximum.
- Use the max_score provided for each question in the input payload.
- Evaluate logical completeness and key terms—not literal string matching only.
- Partial credit is allowed when appropriate.

Output JSON:
{
  "question_results": [
    {
      "question_id": "Q9",
      "question_type": "short_answer",
      "score": 0-16,
      "max_score": 16,
      "is_correct": true/false,
      "short_answer_detail": {
        "matched_keywords": [],
        "missing_keywords": [],
        "logic_complete": false,
        "feedback": "specific feedback"
      },
      "explanation": "detailed explanation",
      "references": [{"knowledge_point_id": "KP-1", "source_quote": "..."}]
    }
  ],
  "summary": "brief overall comment on short-answer performance only"
}"""


GRADE_EASY_SHORT_ANSWER_SYSTEM = """You are an objective academic mentor.
Provide qualitative feedback ONLY for Easy-mode short-answer responses. Do NOT assign numeric scores.

Output JSON with score 0 and max_score 0 for each short-answer item."""


LOGIC_OPTION_LABELS: dict[str, str] = {
    "A": "Both α and β are correct; α is the cause of β",
    "B": "Both α and β are correct; α is the effect of β (β is the cause)",
    "C": "α is correct, β is incorrect",
    "D": "β is correct, α is incorrect",
    "E": "Both α and β are incorrect",
}
