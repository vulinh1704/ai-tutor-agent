"""Application service: sessions, learners and chat turns on top of the compiled graph.

A session *is* a LangGraph thread. Its profile and message history live in the checkpointer,
so there is a single source of truth and swapping the checkpointer swaps all persistence.
Learner profiles and progress live in a LangGraph store (see :mod:`.learners`).
"""

from __future__ import annotations

import asyncio
import uuid
import weakref
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, cast

from langchain_core.messages import AnyMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.store.memory import InMemoryStore

from ai_tutor_agent.agent.checkpointer import open_checkpointer, open_store
from ai_tutor_agent.agent.events import DoneEvent, TurnEvent
from ai_tutor_agent.agent.grading import grade_answer
from ai_tutor_agent.agent.graph import TutorGraph, build_graph
from ai_tutor_agent.agent.hint_policy import HintPolicy
from ai_tutor_agent.agent.learners import LearnerStore
from ai_tutor_agent.agent.state import TutorInput
from ai_tutor_agent.config import Settings
from ai_tutor_agent.llm.base import ChatModel
from ai_tutor_agent.schemas import (
    GradeResult,
    Intent,
    LearnerContext,
    Route,
    Rubric,
    SessionProfile,
)


class SessionNotFoundError(LookupError):
    """No session exists with the given id."""


@dataclass(frozen=True)
class SessionSnapshot:
    session_id: str
    profile: SessionProfile
    messages: list[AnyMessage]
    hint_level: int
    created_at: str | None
    max_hint_level: int = 3
    last_grade: GradeResult | None = None


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
    """Sessions, chat turns (whole or streamed), grading and learner progress.

    Used by the HTTP API, the MCP server and the CLI demo.
    """

    def __init__(
        self,
        graph: TutorGraph,
        llm: ChatModel,
        policy: HintPolicy,
        learners: LearnerStore | None = None,
    ) -> None:
        self.graph = graph
        self.llm = llm
        self.policy = policy
        self.learners = learners or LearnerStore(InMemoryStore())
        # One lock per active session: turns on the same session are applied in order.
        self._locks: weakref.WeakValueDictionary[str, asyncio.Lock] = weakref.WeakValueDictionary()
        # Streamed turns run in their own tasks, so a dropped connection never cuts a turn short.
        self._turns: set[asyncio.Task[None]] = set()

    # ------------------------------------------------------------------ sessions

    async def create_session(self, profile: SessionProfile) -> SessionSnapshot:
        learner = await self._learner(profile)  # 404 for an unknown learner
        session_id = uuid.uuid4().hex
        created_at = datetime.now(UTC).isoformat()
        seed: TutorInput = {"profile": profile.model_dump(mode="json"), "created_at": created_at}
        # On a fresh thread the update is applied as graph input (see TutorInput).
        await self.graph.aupdate_state(_thread(session_id), seed)
        if profile.learner_id:
            await self.learners.add_session(profile.learner_id, session_id, profile, created_at)
        return SessionSnapshot(
            session_id, profile, [], 0, created_at, max_hint_level=self._max_level(learner)
        )

    async def get_session(self, session_id: str) -> SessionSnapshot:
        snapshot = await self.graph.aget_state(_thread(session_id))
        values: dict[str, Any] = snapshot.values
        if "profile" not in values:
            raise SessionNotFoundError(session_id)
        profile = SessionProfile.model_validate(values["profile"])
        last_grade = values.get("last_grade")
        return SessionSnapshot(
            session_id=session_id,
            profile=profile,
            messages=list(values.get("messages", [])),
            hint_level=values.get("hint_level", 0),
            created_at=values.get("created_at"),
            max_hint_level=self._max_level(await self._learner(profile)),
            last_grade=GradeResult.model_validate(last_grade) if last_grade else None,
        )

    # ------------------------------------------------------------------ chat turns

    async def send_message(
        self, session_id: str, content: str, *, intent: Intent = "auto"
    ) -> TurnResult:
        async with self._lock(session_id):
            snapshot = await self.get_session(session_id)  # 404 before spending tokens
            turn_input = await self._turn_input(snapshot.profile, content, intent)
            state = await self.graph.ainvoke(turn_input, _thread(session_id))
            turn = _turn_result(session_id, state)
            await self._record(snapshot.profile, turn)
        return turn

    async def stream_message(
        self, session_id: str, content: str, *, intent: Intent = "auto"
    ) -> AsyncIterator[TurnEvent]:
        """Run a chat turn and yield its events as they happen, ending with ``done``.

        The turn runs in its own task: if the consumer stops listening, the turn still
        completes and is saved, exactly like a non-streaming turn.
        """
        await self.get_session(session_id)  # fail fast for unknown sessions
        queue: asyncio.Queue[TurnEvent | Exception | None] = asyncio.Queue()
        task = asyncio.create_task(self._streamed_turn(session_id, content, intent, queue))
        self._turns.add(task)
        task.add_done_callback(self._turns.discard)
        while (item := await queue.get()) is not None:
            if isinstance(item, Exception):
                raise item
            yield item

    async def aclose(self) -> None:
        """Wait for streamed turns that are still running (call before closing storage)."""
        if self._turns:
            await asyncio.gather(*self._turns, return_exceptions=True)

    async def _streamed_turn(
        self,
        session_id: str,
        content: str,
        intent: Intent,
        queue: asyncio.Queue[TurnEvent | Exception | None],
    ) -> None:
        try:
            async with self._lock(session_id):
                snapshot = await self.get_session(session_id)
                turn_input = await self._turn_input(snapshot.profile, content, intent)
                final: dict[str, Any] = {}
                async for mode, chunk in self.graph.astream(
                    turn_input, _thread(session_id), stream_mode=["custom", "values"]
                ):
                    if mode == "custom":
                        queue.put_nowait(cast(TurnEvent, chunk))
                    else:
                        final = cast(dict[str, Any], chunk)
                turn = _turn_result(session_id, final)
                await self._record(snapshot.profile, turn)
            queue.put_nowait(
                DoneEvent(
                    session_id=session_id,
                    route=turn.route,
                    reply=turn.reply,
                    hint_level=turn.hint_level,
                    grade=turn.grade,
                )
            )
        except Exception as exc:
            queue.put_nowait(exc)
        finally:
            queue.put_nowait(None)

    # ------------------------------------------------------------------ grading

    async def grade(
        self,
        *,
        question: str,
        answer: str,
        rubric: Rubric,
        subject: str,
        level: str,
        reference_answer: str | None = None,
        learner: LearnerContext | None = None,
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
            learner=learner,
        )

    # ------------------------------------------------------------------ helpers

    def _lock(self, session_id: str) -> asyncio.Lock:
        lock = self._locks.get(session_id)
        if lock is None:
            lock = self._locks[session_id] = asyncio.Lock()
        return lock

    async def _learner(self, profile: SessionProfile) -> LearnerContext | None:
        if not profile.learner_id:
            return None
        record = await self.learners.get(profile.learner_id)
        return LearnerContext.from_profile(record.profile)

    def _max_level(self, learner: LearnerContext | None) -> int:
        return self.policy.cap(learner.preferences.scaffolding if learner else "standard")

    async def _turn_input(
        self, profile: SessionProfile, content: str, intent: Intent
    ) -> TutorInput:
        learner = await self._learner(profile)  # the latest preferences apply to every turn
        return {
            "messages": [HumanMessage(content)],
            "intent": intent,
            "learner": learner.model_dump(mode="json") if learner else None,
        }

    async def _record(self, profile: SessionProfile, turn: TurnResult) -> None:
        if profile.learner_id:
            await self.learners.record_turn(
                profile.learner_id,
                turn.session_id,
                subject=profile.subject,
                skills=list(profile.assignment.skills) if profile.assignment else [],
                grade=turn.grade,
            )


def _turn_result(session_id: str, state: dict[str, Any]) -> TurnResult:
    route: Route = state["route"]
    last_grade = state.get("last_grade")
    return TurnResult(
        session_id=session_id,
        route=route,
        reply=state["messages"][-1].text,
        hint_level=state.get("hint_level", 0),
        grade=GradeResult.model_validate(last_grade) if route == "grader" and last_grade else None,
    )


@asynccontextmanager
async def open_service(settings: Settings, llm: ChatModel) -> AsyncIterator[TutorService]:
    """Open the configured storage, build the graph and yield a ready :class:`TutorService`."""
    policy = HintPolicy(max_level=settings.max_hint_level)
    async with open_checkpointer(settings) as checkpointer, open_store(settings) as store:
        graph = build_graph(
            llm, checkpointer=checkpointer, policy=policy, history_window=settings.history_window
        )
        service = TutorService(graph, llm, policy, LearnerStore(store))
        try:
            yield service
        finally:
            await service.aclose()
