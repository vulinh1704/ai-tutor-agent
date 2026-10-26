from __future__ import annotations

import pytest

from ai_tutor_agent.config import Settings
from ai_tutor_agent.schemas import Assignment, Criterion, Rubric, SessionProfile


@pytest.fixture(autouse=True)
def _isolated_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the developer's shell configuration out of the tests."""
    for name in Settings.model_fields:
        monkeypatch.delenv(name.upper(), raising=False)


@pytest.fixture
def rubric() -> Rubric:
    return Rubric(
        criteria=[
            Criterion(
                id="method",
                description="Subtracts 5 from both sides, then divides both sides by 3",
                max_points=3,
            ),
            Criterion(id="answer", description="States the solution x = 5", max_points=2),
        ]
    )


@pytest.fixture
def profile(rubric: Rubric) -> SessionProfile:
    return SessionProfile(
        subject="algebra",
        level="grade 8",
        mode="homework",
        assignment=Assignment(
            question="Solve for x: 3x + 5 = 20", rubric=rubric, reference_answer="x = 5"
        ),
    )
