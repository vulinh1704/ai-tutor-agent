"""HTTP routes. Handlers stay thin: validation in models, behaviour in the service."""

from __future__ import annotations

from typing import Annotated, cast

from fastapi import APIRouter, Depends, Request, status

from ai_tutor_agent import __version__
from ai_tutor_agent.agent.service import TutorService
from ai_tutor_agent.api.models import (
    ChatResponse,
    CreateSessionRequest,
    GradeRequest,
    HealthResponse,
    MessageRequest,
    SessionResponse,
)
from ai_tutor_agent.config import Settings
from ai_tutor_agent.schemas import GradeResult, SessionProfile

router = APIRouter()


def get_service(request: Request) -> TutorService:
    return cast(TutorService, request.app.state.service)


def get_settings_from_app(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


ServiceDep = Annotated[TutorService, Depends(get_service)]
SettingsDep = Annotated[Settings, Depends(get_settings_from_app)]


@router.get("/health", tags=["system"])
async def health(service: ServiceDep, settings: SettingsDep) -> HealthResponse:
    return HealthResponse(
        version=__version__,
        llm_provider=service.llm.provider,
        llm_model=service.llm.model_name,
        checkpointer=settings.checkpointer.value,
    )


@router.post("/sessions", status_code=status.HTTP_201_CREATED, tags=["sessions"])
async def create_session(body: CreateSessionRequest, service: ServiceDep) -> SessionResponse:
    """Start a tutoring session for a subject and level, optionally tied to an assignment."""
    profile = SessionProfile.model_validate(body.model_dump())
    snapshot = await service.create_session(profile)
    return SessionResponse.from_snapshot(snapshot)


@router.get("/sessions/{session_id}", tags=["sessions"])
async def get_session(session_id: str, service: ServiceDep) -> SessionResponse:
    """Session profile and full message history."""
    return SessionResponse.from_snapshot(await service.get_session(session_id))


@router.post("/sessions/{session_id}/messages", tags=["sessions"])
async def send_message(session_id: str, body: MessageRequest, service: ServiceDep) -> ChatResponse:
    """Send a student message. The router picks the tutor, the grader or a clarifying question."""
    return ChatResponse.from_turn(await service.send_message(session_id, body.content))


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
