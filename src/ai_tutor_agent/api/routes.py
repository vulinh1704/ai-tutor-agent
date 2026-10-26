"""HTTP routes. Handlers stay thin: validation in models, behaviour in the service."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated, Any, cast

from fastapi import APIRouter, Depends, Request, status
from fastapi.sse import EventSourceResponse, ServerSentEvent

from ai_tutor_agent import __version__
from ai_tutor_agent.agent.events import ErrorEvent
from ai_tutor_agent.agent.learners import ProgressSummary, SessionRecord
from ai_tutor_agent.agent.service import SessionSnapshot, TutorService
from ai_tutor_agent.api.errors import describe_error
from ai_tutor_agent.api.models import (
    ChatResponse,
    CreateSessionRequest,
    GradeRequest,
    HealthResponse,
    LearnerRequest,
    LearnerResponse,
    MessageRequest,
    SessionResponse,
)
from ai_tutor_agent.config import Settings
from ai_tutor_agent.schemas import GradeResult, LearnerProfile, SessionProfile

router = APIRouter()


def get_service(request: Request) -> TutorService:
    return cast(TutorService, request.app.state.service)


def get_settings_from_app(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


ServiceDep = Annotated[TutorService, Depends(get_service)]
SettingsDep = Annotated[Settings, Depends(get_settings_from_app)]


async def existing_session(session_id: str, service: ServiceDep) -> SessionSnapshot:
    """Resolve the session before a stream starts, so an unknown id is a plain 404."""
    return await service.get_session(session_id)


SessionDep = Annotated[SessionSnapshot, Depends(existing_session)]

_STREAM_DESCRIPTION = """\
Server-sent events, one per step of the turn:

- `route`: the router's decision (`tutor`, `grader` or `clarify`)
- `hint`: the hint-ladder rung used for this reply
- `token`: reply text, already checked by the answer-leak guard
- `reset`: discard the text received so far (a leaking draft is being replaced)
- `grade`: per-criterion scores, when an answer was graded
- `done`: the saved turn, same shape as `POST /sessions/{id}/messages`
- `error`: `{status, detail}` if the turn fails after the stream started
"""


@router.get("/health", tags=["system"])
async def health(service: ServiceDep, settings: SettingsDep) -> HealthResponse:
    return HealthResponse(
        version=__version__,
        llm_provider=service.llm.provider,
        llm_model=service.llm.model_name,
        checkpointer=settings.checkpointer.value,
    )


# --------------------------------------------------------------------------- sessions


@router.post("/sessions", status_code=status.HTTP_201_CREATED, tags=["sessions"])
async def create_session(body: CreateSessionRequest, service: ServiceDep) -> SessionResponse:
    """Start a tutoring session for a subject and level, optionally tied to an assignment and
    a learner profile."""
    profile = SessionProfile.model_validate(body.model_dump())
    snapshot = await service.create_session(profile)
    return SessionResponse.from_snapshot(snapshot)


@router.get("/sessions/{session_id}", tags=["sessions"])
async def get_session(session: SessionDep) -> SessionResponse:
    """Session profile, message history and the latest grade."""
    return SessionResponse.from_snapshot(session)


@router.post("/sessions/{session_id}/messages", tags=["sessions"])
async def send_message(session_id: str, body: MessageRequest, service: ServiceDep) -> ChatResponse:
    """Send a student message. The router picks the tutor, the grader or a clarifying question."""
    turn = await service.send_message(session_id, body.content, intent=body.intent)
    return ChatResponse.from_turn(turn)


@router.post(
    "/sessions/{session_id}/messages/stream",
    response_class=EventSourceResponse,
    tags=["sessions"],
    description=_STREAM_DESCRIPTION,
)
async def stream_message(
    session: SessionDep, body: MessageRequest, service: ServiceDep
) -> AsyncIterator[ServerSentEvent]:
    """Send a student message and stream the reply as server-sent events."""
    try:
        async for event in service.stream_message(
            session.session_id, body.content, intent=body.intent
        ):
            yield ServerSentEvent(event=event.type, data=event)
    except Exception as exc:
        status_code, detail = describe_error(exc)
        yield ServerSentEvent(event="error", data=ErrorEvent(status=status_code, detail=detail))


@router.post("/grade", tags=["grading"])
async def grade(body: GradeRequest, service: ServiceDep) -> GradeResult:
    """Grade a short answer against a rubric and return structured feedback."""
    return await service.grade(
        question=body.question,
        answer=body.answer,
        rubric=body.rubric,
        subject=body.subject,
        level=body.level,
        reference_answer=body.reference_answer,
    )


# --------------------------------------------------------------------------- learners


def _profile(body: LearnerRequest) -> LearnerProfile:
    data: dict[str, Any] = body.model_dump()
    return LearnerProfile.model_validate(data)


@router.post("/learners", status_code=status.HTTP_201_CREATED, tags=["learners"])
async def create_learner(body: LearnerRequest, service: ServiceDep) -> LearnerResponse:
    """Create a learner profile. Sessions created with its id are personalised and tracked."""
    return LearnerResponse.from_record(await service.learners.create(_profile(body)))


@router.get("/learners/{learner_id}", tags=["learners"])
async def get_learner(learner_id: str, service: ServiceDep) -> LearnerResponse:
    return LearnerResponse.from_record(await service.learners.get(learner_id))


@router.put("/learners/{learner_id}", tags=["learners"])
async def update_learner(
    learner_id: str, body: LearnerRequest, service: ServiceDep
) -> LearnerResponse:
    """Replace a learner profile. New preferences apply from the next chat turn."""
    return LearnerResponse.from_record(await service.learners.update(learner_id, _profile(body)))


@router.get("/learners/{learner_id}/sessions", tags=["learners"])
async def list_learner_sessions(learner_id: str, service: ServiceDep) -> list[SessionRecord]:
    """The learner's sessions, most recently active first."""
    return await service.learners.list_sessions(learner_id)


@router.get("/learners/{learner_id}/progress", tags=["learners"])
async def learner_progress(learner_id: str, service: ServiceDep) -> ProgressSummary:
    """Sessions practised, average rubric score and practice streaks."""
    return await service.learners.progress(learner_id)
