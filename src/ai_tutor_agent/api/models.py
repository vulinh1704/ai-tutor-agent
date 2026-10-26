"""HTTP request and response models."""

from __future__ import annotations

from typing import Literal

from langchain_core.messages import HumanMessage
from pydantic import BaseModel, ConfigDict, Field
from pydantic.config import JsonDict

from ai_tutor_agent.agent.learners import LearnerRecord
from ai_tutor_agent.agent.service import SessionSnapshot, TurnResult
from ai_tutor_agent.schemas import (
    GradeResult,
    Intent,
    LearnerProfile,
    Route,
    Rubric,
    SessionProfile,
    TutorMode,
)

_RUBRIC_EXAMPLE: JsonDict = {
    "criteria": [
        {
            "id": "method",
            "description": "Subtracts 5 from both sides, then divides both sides by 3",
            "max_points": 3,
        },
        {"id": "answer", "description": "States the solution x = 5", "max_points": 2},
    ]
}


class CreateSessionRequest(SessionProfile):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "subject": "algebra",
                    "level": "grade 8",
                    "mode": "homework",
                    "assignment": {
                        "question": "Solve for x: 3x + 5 = 20",
                        "reference_answer": "x = 5",
                        "rubric": _RUBRIC_EXAMPLE,
                        "skills": ["linear-equations"],
                    },
                }
            ]
        }
    )


class AssignmentView(BaseModel):
    """Public view of an assignment: the reference answer is never returned."""

    question: str
    rubric: Rubric | None
    has_reference_answer: bool
    skills: list[str] = []


class MessageView(BaseModel):
    role: Literal["student", "tutor"]
    content: str


class SessionResponse(BaseModel):
    session_id: str
    subject: str
    level: str
    mode: TutorMode
    learner_id: str | None = None
    assignment: AssignmentView | None
    hint_level: int
    max_hint_level: int = Field(description="Highest rung of this session's hint ladder.")
    created_at: str | None
    messages: list[MessageView]
    last_grade: GradeResult | None = None

    @classmethod
    def from_snapshot(cls, snapshot: SessionSnapshot) -> SessionResponse:
        profile = snapshot.profile
        assignment = profile.assignment
        return cls(
            session_id=snapshot.session_id,
            subject=profile.subject,
            level=profile.level,
            mode=profile.mode,
            learner_id=profile.learner_id,
            assignment=AssignmentView(
                question=assignment.question,
                rubric=assignment.rubric,
                has_reference_answer=bool(assignment.reference_answer),
                skills=list(assignment.skills),
            )
            if assignment
            else None,
            hint_level=snapshot.hint_level,
            max_hint_level=snapshot.max_hint_level,
            created_at=snapshot.created_at,
            messages=[
                MessageView(
                    role="student" if isinstance(m, HumanMessage) else "tutor", content=m.text
                )
                for m in snapshot.messages
            ],
            last_grade=snapshot.last_grade,
        )


class MessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000, examples=["How do I start this one?"])
    intent: Intent = Field(
        default="auto",
        description=(
            "auto: the router decides. submit: grade this message against the session rubric."
        ),
    )


class ChatResponse(BaseModel):
    session_id: str
    route: Route
    reply: str
    hint_level: int
    grade: GradeResult | None = None

    @classmethod
    def from_turn(cls, turn: TurnResult) -> ChatResponse:
        return cls(
            session_id=turn.session_id,
            route=turn.route,
            reply=turn.reply,
            hint_level=turn.hint_level,
            grade=turn.grade,
        )


class GradeRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "question": "Solve for x: 3x + 5 = 20",
                    "answer": "I subtracted 5 from both sides to get 3x = 15, so x = 5.",
                    "rubric": _RUBRIC_EXAMPLE,
                    "subject": "algebra",
                    "level": "grade 8",
                }
            ]
        }
    )

    question: str = Field(min_length=3, max_length=4000)
    answer: str = Field(min_length=1, max_length=8000)
    rubric: Rubric
    subject: str = Field(default="general studies", min_length=1, max_length=80)
    level: str = Field(default="general", min_length=1, max_length=80)
    reference_answer: str | None = Field(default=None, max_length=4000)


class LearnerRequest(LearnerProfile):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "display_name": "Linh",
                    "level": "grade 8",
                    "subjects": ["math", "physics"],
                    "goal": "Feel confident solving equations",
                    "preferences": {"language": "vi", "tone": "gentle", "scaffolding": "more"},
                    "appearance": {"avatar": "owl", "accent": "teal", "font_scale": "large"},
                    "timezone": "Asia/Ho_Chi_Minh",
                }
            ]
        }
    )


class LearnerResponse(LearnerProfile):
    learner_id: str
    created_at: str
    updated_at: str

    @classmethod
    def from_record(cls, record: LearnerRecord) -> LearnerResponse:
        return cls(
            learner_id=record.learner_id,
            created_at=record.created_at,
            updated_at=record.updated_at,
            **record.profile.model_dump(),
        )


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    version: str
    llm_provider: str
    llm_model: str
    checkpointer: str
