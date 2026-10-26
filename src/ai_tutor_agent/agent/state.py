"""Graph state, persisted per session (LangGraph thread) by the checkpointer."""

from __future__ import annotations

from typing import Annotated, Any, NotRequired, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages

from ai_tutor_agent.schemas import Route


class TutorInput(TypedDict):
    """What callers may write into the graph.

    A chat turn passes only ``messages``. Creating a session seeds ``profile`` and
    ``created_at`` once, with ``aupdate_state`` on a fresh thread (which is applied as input).
    """

    messages: NotRequired[Annotated[list[AnyMessage], add_messages]]
    profile: NotRequired[dict[str, Any]]
    created_at: NotRequired[str]


class TutorState(TypedDict):
    """State shared by every node.

    Only LangChain messages and JSON-friendly values are stored, so any LangGraph checkpointer
    (memory, SQLite, Postgres) can serialise it without custom types.
    """

    messages: Annotated[list[AnyMessage], add_messages]
    profile: dict[str, Any]
    """``SessionProfile.model_dump(mode="json")``."""
    created_at: NotRequired[str]
    route: NotRequired[Route]
    route_reason: NotRequired[str]
    new_problem: NotRequired[bool]
    hint_level: NotRequired[int]
    last_grade: NotRequired[dict[str, Any] | None]
    """``GradeResult.model_dump(mode="json")`` from the most recent grading turn."""
