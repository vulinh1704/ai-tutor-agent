import pytest
from pydantic import ValidationError

from ai_tutor_agent.schemas import (
    Criterion,
    CriterionScore,
    GradeResult,
    Rubric,
    SessionProfile,
)


def test_rubric_max_score_sums_criteria(rubric: Rubric) -> None:
    assert rubric.max_score == 5


def test_rubric_rejects_duplicate_ids() -> None:
    with pytest.raises(ValidationError, match="duplicate criterion ids: a"):
        Rubric(
            criteria=[
                Criterion(id="a", description="first", max_points=1),
                Criterion(id="a", description="second", max_points=1),
            ]
        )


def test_rubric_needs_at_least_one_criterion() -> None:
    with pytest.raises(ValidationError):
        Rubric(criteria=[])


@pytest.mark.parametrize("bad_id", ["", "Has Space", "UPPER", "-leading-dash", "x" * 41])
def test_criterion_id_must_be_a_slug(bad_id: str) -> None:
    with pytest.raises(ValidationError):
        Criterion(id=bad_id, description="something", max_points=1)


@pytest.mark.parametrize("points", [0, 101])
def test_criterion_max_points_bounds(points: int) -> None:
    with pytest.raises(ValidationError):
        Criterion(id="a", description="something", max_points=points)


def _score(points: int, max_points: int = 2) -> CriterionScore:
    return CriterionScore(criterion_id="a", points=points, max_points=max_points, feedback="ok")


def test_grade_result_accepts_consistent_totals() -> None:
    grade = GradeResult(
        score=1, max_score=2, percentage=50.0, criteria=[_score(1)], next_step_hint="hint"
    )
    assert grade.score == 1


def test_grade_result_rejects_wrong_total() -> None:
    with pytest.raises(ValidationError, match="score must equal"):
        GradeResult(
            score=2, max_score=2, percentage=100.0, criteria=[_score(1)], next_step_hint="h"
        )


def test_grade_result_rejects_points_above_max() -> None:
    with pytest.raises(ValidationError, match="cannot exceed"):
        GradeResult(
            score=3, max_score=2, percentage=100.0, criteria=[_score(3)], next_step_hint="h"
        )


def test_profile_rubric_shortcut(profile: SessionProfile) -> None:
    assert profile.rubric is not None
    assert SessionProfile(subject="history", level="university").rubric is None


def test_profile_defaults_to_homework_mode() -> None:
    assert SessionProfile(subject="physics", level="grade 10").mode == "homework"
