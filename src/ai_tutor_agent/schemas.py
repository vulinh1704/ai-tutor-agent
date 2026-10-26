"""Domain models shared by the agent, the API and the LLM layer."""

from __future__ import annotations

from collections import Counter
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

TutorMode = Literal["homework", "explain"]
"""``homework``: Socratic hints only, never the final answer. ``explain``: full walkthroughs."""

Route = Literal["tutor", "grader", "clarify"]


class Criterion(BaseModel):
    """One line of a grading rubric."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,39}$", examples=["method"])
    description: str = Field(min_length=3, max_length=500)
    max_points: int = Field(ge=1, le=100)


class Rubric(BaseModel):
    """A list of independently scored criteria."""

    criteria: list[Criterion] = Field(min_length=1, max_length=12)

    @model_validator(mode="after")
    def _ids_are_unique(self) -> Rubric:
        counts = Counter(c.id for c in self.criteria)
        duplicates = sorted(cid for cid, n in counts.items() if n > 1)
        if duplicates:
            raise ValueError(f"duplicate criterion ids: {', '.join(duplicates)}")
        return self

    @property
    def max_score(self) -> int:
        return sum(c.max_points for c in self.criteria)


class Assignment(BaseModel):
    """The problem a tutoring session is about."""

    question: str = Field(min_length=3, max_length=4000)
    rubric: Rubric | None = None
    reference_answer: str | None = Field(
        default=None,
        max_length=4000,
        description="Never shown to the student; used for grading and answer-leak detection.",
    )


class SessionProfile(BaseModel):
    """Who the tutor is talking to and how it should behave."""

    subject: str = Field(min_length=1, max_length=80, examples=["algebra"])
    level: str = Field(min_length=1, max_length=80, examples=["grade 8"])
    mode: TutorMode = "homework"
    assignment: Assignment | None = None

    @property
    def rubric(self) -> Rubric | None:
        return self.assignment.rubric if self.assignment else None


class CriterionScore(BaseModel):
    criterion_id: str
    points: int = Field(ge=0)
    max_points: int = Field(ge=1)
    feedback: str


class GradeResult(BaseModel):
    """Validated grading outcome. Totals are always computed in code, never by the model."""

    score: int = Field(ge=0)
    max_score: int = Field(ge=1)
    percentage: float = Field(ge=0, le=100)
    criteria: list[CriterionScore] = Field(min_length=1)
    next_step_hint: str

    @model_validator(mode="after")
    def _totals_are_consistent(self) -> GradeResult:
        if any(c.points > c.max_points for c in self.criteria):
            raise ValueError("criterion points cannot exceed max_points")
        if self.score != sum(c.points for c in self.criteria):
            raise ValueError("score must equal the sum of criterion points")
        if self.max_score != sum(c.max_points for c in self.criteria):
            raise ValueError("max_score must equal the sum of criterion max_points")
        return self


# --------------------------------------------------------------------------------------
# Structured outputs requested from the LLM.
#
# These are deliberately simple (every field required, no numeric constraints) so the same
# schema works with OpenAI strict JSON schema and Claude's ``output_config.format``.
# Semantic checks (e.g. "points within range") live in code, see ``agent.grading``.
# --------------------------------------------------------------------------------------


class RouteDecision(BaseModel):
    """Router output: which node should handle the student's latest message."""

    route: Route = Field(
        description=(
            "tutor: the student asks for help or explanation; "
            "grader: the student submits an answer to be checked; "
            "clarify: the message is too vague to act on."
        )
    )
    new_problem: bool = Field(description="True if the student moved on to a different problem.")
    reason: str = Field(description="One short sentence explaining the choice.")


class CriterionAssessment(BaseModel):
    criterion_id: str = Field(description="Must match a rubric criterion id exactly.")
    points: int = Field(description="Integer between 0 and that criterion's max_points.")
    feedback: str = Field(description="One or two sentences addressed to the student.")


class GraderOutput(BaseModel):
    """Raw grading output from the model, validated against the rubric afterwards."""

    assessments: list[CriterionAssessment] = Field(
        description="Exactly one assessment per rubric criterion."
    )
    next_step_hint: str = Field(
        description="A single Socratic hint for improving the weakest part. Never the answer."
    )
