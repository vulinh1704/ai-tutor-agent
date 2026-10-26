import pytest
from langchain_core.messages import AIMessage, HumanMessage

from ai_tutor_agent.agent.grading import (
    SAFE_NEXT_STEP,
    GradingError,
    build_grade_result,
    format_grade,
    grade_answer,
)
from ai_tutor_agent.llm.fake import FakeChatModel
from ai_tutor_agent.schemas import CriterionAssessment, GraderOutput, Rubric


def _output(*items: tuple[str, int], hint: str = "Check the division step.") -> GraderOutput:
    return GraderOutput(
        assessments=[
            CriterionAssessment(criterion_id=cid, points=points, feedback=f"{cid} feedback")
            for cid, points in items
        ],
        next_step_hint=hint,
    )


def test_build_grade_result_computes_totals_in_rubric_order(rubric: Rubric) -> None:
    grade = build_grade_result(rubric, _output(("answer", 2), ("method", 1)))
    assert [c.criterion_id for c in grade.criteria] == ["method", "answer"]
    assert (grade.score, grade.max_score, grade.percentage) == (3, 5, 60.0)
    assert grade.criteria[0].max_points == 3


@pytest.mark.parametrize(
    ("output", "message"),
    [
        (_output(("method", 3), ("answer", 2), ("style", 1)), "unknown criterion id 'style'"),
        (_output(("method", 3), ("method", 1), ("answer", 2)), "assessed more than once"),
        (_output(("method", 4), ("answer", 2)), "must be between 0 and 3, got 4"),
        (_output(("method", -1), ("answer", 2)), "must be between 0 and 3, got -1"),
        (_output(("method", 3)), "missing criteria: answer"),
    ],
)
def test_build_grade_result_rejects_invalid_output(
    rubric: Rubric, output: GraderOutput, message: str
) -> None:
    with pytest.raises(GradingError, match=message):
        build_grade_result(rubric, output)


async def test_grade_answer_retries_with_a_correction(rubric: Rubric) -> None:
    llm = FakeChatModel(structured=[_output(("method", 9)), _output(("method", 3), ("answer", 2))])

    grade = await grade_answer(llm, question="Solve 3x + 5 = 20", answer="x = 5", rubric=rubric)

    assert grade.score == 5
    retry_messages = llm.calls[1].messages
    assert isinstance(retry_messages[-2], AIMessage)
    assert isinstance(retry_messages[-1], HumanMessage)
    assert "invalid" in retry_messages[-1].text


async def test_grade_answer_gives_up_after_max_attempts(rubric: Rubric) -> None:
    llm = FakeChatModel(structured=[_output(("method", 9)), _output(("method", 9))])
    with pytest.raises(GradingError, match="after 2 attempts"):
        await grade_answer(llm, question="Solve 3x + 5 = 20", answer="x = 5", rubric=rubric)


async def test_next_step_hint_that_leaks_the_reference_is_replaced(rubric: Rubric) -> None:
    leaky = _output(("method", 1), ("answer", 0), hint="The answer is x = 5.")
    grade = await grade_answer(
        FakeChatModel(structured=[leaky]),
        question="Solve 3x + 5 = 20",
        answer="x = 3",
        rubric=rubric,
        reference_answer="x = 5",
    )
    assert grade.next_step_hint == SAFE_NEXT_STEP


def test_format_grade(rubric: Rubric) -> None:
    text = format_grade(build_grade_result(rubric, _output(("method", 3), ("answer", 1))))
    assert text.splitlines() == [
        "Score: 4/5 (80%)",
        "- method (3/3): method feedback",
        "- answer (1/2): answer feedback",
        "Next step: Check the division step.",
    ]
