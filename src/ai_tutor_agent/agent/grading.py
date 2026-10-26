"""Rubric-based grading: the model judges each criterion, code validates and does the maths."""

from __future__ import annotations

import logging

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from ai_tutor_agent.agent.hint_policy import HintPolicy
from ai_tutor_agent.llm.base import ChatModel
from ai_tutor_agent.prompts import grader_messages
from ai_tutor_agent.schemas import (
    CriterionAssessment,
    CriterionScore,
    GradeResult,
    GraderOutput,
    Rubric,
)

logger = logging.getLogger(__name__)

SAFE_NEXT_STEP = "Compare your answer with each criterion above. Which one could you strengthen?"


class GradingError(RuntimeError):
    """The model's grading output could not be reconciled with the rubric."""


def build_grade_result(rubric: Rubric, output: GraderOutput) -> GradeResult:
    """Validate raw model output against ``rubric`` and compute the totals."""
    criteria = {c.id: c for c in rubric.criteria}
    assessed: dict[str, CriterionAssessment] = {}
    problems: list[str] = []

    for item in output.assessments:
        criterion = criteria.get(item.criterion_id)
        if criterion is None:
            problems.append(f"unknown criterion id {item.criterion_id!r}")
        elif item.criterion_id in assessed:
            problems.append(f"criterion {item.criterion_id!r} assessed more than once")
        elif not 0 <= item.points <= criterion.max_points:
            problems.append(
                f"points for {item.criterion_id!r} must be between 0 and "
                f"{criterion.max_points}, got {item.points}"
            )
        else:
            assessed[item.criterion_id] = item

    missing = [cid for cid in criteria if cid not in assessed]
    if missing and not problems:
        problems.append(f"missing criteria: {', '.join(missing)}")
    if problems:
        raise GradingError("; ".join(problems))

    scores = [
        CriterionScore(
            criterion_id=c.id,
            points=assessed[c.id].points,
            max_points=c.max_points,
            feedback=assessed[c.id].feedback.strip(),
        )
        for c in rubric.criteria
    ]
    score = sum(s.points for s in scores)
    return GradeResult(
        score=score,
        max_score=rubric.max_score,
        percentage=round(100 * score / rubric.max_score, 1),
        criteria=scores,
        next_step_hint=output.next_step_hint.strip() or SAFE_NEXT_STEP,
    )


async def grade_answer(
    llm: ChatModel,
    *,
    question: str,
    answer: str,
    rubric: Rubric,
    subject: str = "general studies",
    level: str = "general",
    reference_answer: str | None = None,
    policy: HintPolicy | None = None,
    max_attempts: int = 2,
) -> GradeResult:
    """Grade ``answer`` against ``rubric``; re-ask the model once if its output is invalid."""
    messages: list[BaseMessage] = grader_messages(
        question=question,
        answer=answer,
        rubric=rubric,
        subject=subject,
        level=level,
        reference_answer=reference_answer,
    )
    last_error: GradingError | None = None
    for attempt in range(1, max_attempts + 1):
        output = await llm.structured(messages, GraderOutput)
        try:
            grade = build_grade_result(rubric, output)
        except GradingError as exc:
            last_error = exc
            logger.warning("Rejected grader output (attempt %d/%d): %s", attempt, max_attempts, exc)
            messages = [
                *messages,
                AIMessage(output.model_dump_json()),
                HumanMessage(
                    f"That grading is invalid: {exc}. Return one assessment per rubric "
                    "criterion id, with points between 0 and that criterion's max_points."
                ),
            ]
            continue
        # The next-step hint goes straight to the student, so it gets the same leak check.
        if (policy or HintPolicy()).leaks_answer(grade.next_step_hint, reference_answer):
            grade = grade.model_copy(update={"next_step_hint": SAFE_NEXT_STEP})
        return grade
    raise GradingError(f"Grading failed after {max_attempts} attempts: {last_error}")


def format_grade(grade: GradeResult) -> str:
    """Render a grade as a chat message."""
    lines = [f"Score: {grade.score}/{grade.max_score} ({grade.percentage:g}%)"]
    lines += [
        f"- {c.criterion_id} ({c.points}/{c.max_points}): {c.feedback}" for c in grade.criteria
    ]
    lines.append(f"Next step: {grade.next_step_hint}")
    return "\n".join(lines)
