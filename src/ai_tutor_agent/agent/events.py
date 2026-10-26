"""Events emitted while a chat turn is streamed.

Nodes write them through LangGraph's custom stream writer (a no-op when the graph is not
streamed), and the HTTP API sends each one as a server-sent event named after its ``type``.
A turn always ends with ``done`` (or ``error``):

``route`` -> ``hint`` -> ``token``... (``reset`` -> ``token``...) -> ``grade`` -> ``done``
"""

from __future__ import annotations

from typing import Literal, TypeAlias

from langgraph.config import get_stream_writer
from pydantic import BaseModel, Field

from ai_tutor_agent.schemas import GradeResult, Route


class RouteEvent(BaseModel):
    """The router's decision for this turn."""

    type: Literal["route"] = "route"
    route: Route
    reason: str
    new_problem: bool


class HintEvent(BaseModel):
    """The hint-ladder rung used for this reply (0 outside the ladder)."""

    type: Literal["hint"] = "hint"
    hint_level: int
    max_hint_level: int


class TokenEvent(BaseModel):
    """A chunk of reply text that has passed the answer-leak guard."""

    type: Literal["token"] = "token"
    text: str


class ResetEvent(BaseModel):
    """Discard the reply text received so far: the guard rejected the draft and a new one
    follows."""

    type: Literal["reset"] = "reset"
    reason: Literal["answer_leak"] = "answer_leak"


class GradeEvent(BaseModel):
    """Structured grading result for a submitted answer."""

    type: Literal["grade"] = "grade"
    grade: GradeResult


class DoneEvent(BaseModel):
    """The turn is complete and saved. Same fields as the non-streaming chat response."""

    type: Literal["done"] = "done"
    session_id: str
    route: Route
    reply: str
    hint_level: int
    grade: GradeResult | None = None


class ErrorEvent(BaseModel):
    """The turn failed after the stream started; ``status`` is the equivalent HTTP status."""

    type: Literal["error"] = "error"
    status: int = Field(examples=[502])
    detail: str


TurnEvent: TypeAlias = (
    RouteEvent | HintEvent | TokenEvent | ResetEvent | GradeEvent | DoneEvent | ErrorEvent
)


def emit(event: TurnEvent) -> None:
    """Send ``event`` to the current graph stream (ignored when nobody is streaming)."""
    get_stream_writer()(event)
