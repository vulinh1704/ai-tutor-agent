"""Application service: session lifecycle and chat turns on top of the compiled graph.

A session *is* a LangGraph thread. Its profile and message history live in the checkpointer,
so there is a single source of truth and swapping the checkpointer swaps all persistence.
"""

from __future__ import annotations

import asyncio
import uuid
import weakref
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from langchain_core.messages import AnyMessage, HumanMessage
from langchain_core.runnables import RunnableConfig

from ai_tutor_agent.agent.grading import grade_answer
from ai_tutor_agent.agent.graph import TutorGraph
from ai_tutor_agent.agent.hint_policy import HintPolicy
from ai_tutor_agent.agent.state import TutorInput
from ai_tutor_agent.llm.base import ChatModel
from ai_tutor_agent.schemas import GradeResult, Route, Rubric, SessionProfile


class SessionNotFoundError(LookupError):
    """No session exists with the given id."""


@dataclass(frozen=True)
class SessionSnapshot:
    session_id: str
    profile: SessionProfile
    messages: list[AnyMessage]
    hint_level: int
    created_at: str | None


@dataclass(frozen=True)
class TurnResult:
    session_id: str
    route: Route
    reply: str
    hint_level: int
    grade: GradeResult | None


def _thread(session_id: str) -> RunnableConfig:
    return {"configurable": {"thread_id": session_id}}


class TutorService:
    """Session lifecycle, chat turns and grading. Used by the HTTP API and the CLI demo."""

    def __init__(self, graph: TutorGraph, llm: ChatModel, policy: HintPolicy) -> None:
        self.graph = graph
        self.llm = llm
        self.policy = policy
        # One lock per active session: turns on the same session are applied in order.
        self._locks: weakref.WeakValueDictionary[str, asyncio.Lock] = weakref.WeakValueDictionary()

    async def create_session(self, profile: SessionProfile) -> SessionSnapshot:
        session_id = uuid.uuid4().hex
        created_at = datetime.now(UTC).isoformat()
        seed: TutorInput = {"profile": profile.model_dump(mode="json"), "created_at": created_at}
        # On a fresh thread the update is applied as graph input (see TutorInput).
        await self.graph.aupdate_state(_thread(session_id), seed)
        return SessionSnapshot(session_id, profile, [], 0, created_at)

    async def get_session(self, session_id: str) -> SessionSnapshot:
        snapshot = await self.graph.aget_state(_thread(session_id))
        values: dict[str, Any] = snapshot.values
        if "profile" not in values:
            raise SessionNotFoundError(session_id)
        return SessionSnapshot(
            session_id=session_id,
            profile=SessionProfile.model_validate(values["profile"]),
            messages=list(values.get("messages", [])),
            hint_level=values.get("hint_level", 0),
            created_at=values.get("created_at"),
        )

    async def send_message(self, session_id: str, content: str) -> TurnResult:
        lock = self._locks.get(session_id)
        if lock is None:
            lock = self._locks[session_id] = asyncio.Lock()
        async with lock:
            await self.get_session(session_id)  # 404 before spending tokens
            state = await self.graph.ainvoke(
                {"messages": [HumanMessage(content)]}, _thread(session_id)
            )

        route: Route = state["route"]
        last_grade = state.get("last_grade")
        return TurnResult(
            session_id=session_id,
            route=route,
            reply=state["messages"][-1].text,
            hint_level=state.get("hint_level", 0),
            grade=GradeResult.model_validate(last_grade)
            if route == "grader" and last_grade
            else None,
        )

    async def grade(
        self,
        *,
        question: str,
        answer: str,
        rubric: Rubric,
        subject: str,
        level: str,
        reference_answer: str | None = None,
    ) -> GradeResult:
        """Stateless grading, shared with the graph's grader node."""
        return await grade_answer(
            self.llm,
            question=question,
            answer=answer,
            rubric=rubric,
            subject=subject,
            level=level,
            reference_answer=reference_answer,
            policy=self.policy,
        )
