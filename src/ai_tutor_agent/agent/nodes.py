"""Graph nodes. Each node is a small async method that returns a partial state update.

Nodes also report progress through :func:`~ai_tutor_agent.agent.events.emit` (route, hint
level, reply text), which turns into server-sent events when the graph is streamed and costs
nothing otherwise.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from ai_tutor_agent.agent.events import (
    GradeEvent,
    HintEvent,
    ResetEvent,
    RouteEvent,
    TokenEvent,
    emit,
)
from ai_tutor_agent.agent.grading import format_grade, grade_answer
from ai_tutor_agent.agent.hint_policy import HintPolicy
from ai_tutor_agent.agent.state import TutorState
from ai_tutor_agent.agent.stream_guard import StreamGuard
from ai_tutor_agent.llm.base import ChatModel, LLMOutputError
from ai_tutor_agent.prompts import (
    LEAK_RETRY_NOTE,
    clarify_reply,
    recent_history,
    router_messages,
    tutor_messages,
)
from ai_tutor_agent.schemas import (
    Language,
    LearnerContext,
    Route,
    RouteDecision,
    SessionProfile,
)

logger = logging.getLogger(__name__)


class TutorNodes:
    """Node implementations bound to their dependencies (model, hint policy, history window)."""

    def __init__(self, llm: ChatModel, policy: HintPolicy, *, history_window: int = 20) -> None:
        self.llm = llm
        self.policy = policy
        self.history_window = history_window

    async def router(self, state: TutorState) -> dict[str, Any]:
        """Ask the model where the latest message should go, then apply guardrails in code."""
        profile = SessionProfile.model_validate(state["profile"])
        learner = _learner(state)
        if state.get("intent") == "submit":
            # The client said this is an answer to grade: no need to ask the model.
            decision = RouteDecision(
                route="grader", new_problem=False, reason="The student submitted an answer."
            )
        else:
            history = recent_history(state["messages"], self.history_window)
            try:
                decision = await self.llm.structured(
                    router_messages(profile, history, learner), RouteDecision
                )
            except LLMOutputError as exc:
                logger.warning("Router output unusable, defaulting to the tutor: %s", exc)
                decision = RouteDecision(
                    route="tutor", new_problem=False, reason="Router fallback after invalid output."
                )

        route, reason = decision.route, decision.reason
        if route == "grader" and profile.rubric is None:
            route, reason = "tutor", "No rubric is attached to this session, so the tutor helps."
        emit(RouteEvent(route=route, reason=reason, new_problem=decision.new_problem))
        return {"route": route, "route_reason": reason, "new_problem": decision.new_problem}

    async def tutor(self, state: TutorState) -> dict[str, Any]:
        """Reply with a hint at the current ladder level (or a full explanation in explain mode)."""
        profile = SessionProfile.model_validate(state["profile"])
        learner = _learner(state)
        history = recent_history(state["messages"], self.history_window)

        if profile.mode == "explain":
            emit(HintEvent(hint_level=0, max_hint_level=0))
            explanation = await self._stream_reply(
                tutor_messages(profile, history, hint_level=0, learner=learner)
            )
            return {"messages": [AIMessage(explanation)], "hint_level": 0}

        scaffolding = learner.preferences.scaffolding if learner else "standard"
        level = self.policy.next_level(
            state.get("hint_level", 0),
            new_problem=state.get("new_problem", False),
            scaffolding=scaffolding,
        )
        emit(HintEvent(hint_level=level, max_hint_level=self.policy.cap(scaffolding)))
        reference = profile.assignment.reference_answer if profile.assignment else None

        reply = await self._guarded_reply(
            tutor_messages(profile, history, level, learner=learner), reference
        )
        if reply is None:
            logger.info("Tutor draft revealed the answer; regenerating once")
            emit(ResetEvent())
            reply = await self._guarded_reply(
                tutor_messages(
                    profile, history, level, retry_note=LEAK_RETRY_NOTE, learner=learner
                ),
                reference,
            )
        if reply is None:
            logger.warning("Tutor still revealed the answer; using the fallback hint")
            emit(ResetEvent())
            reply = self.policy.fallback_reply(level, _language(learner))
            emit(TokenEvent(text=reply))
        return {"messages": [AIMessage(reply)], "hint_level": level}

    async def grader(self, state: TutorState) -> dict[str, Any]:
        """Grade the student's latest message against the session rubric."""
        profile = SessionProfile.model_validate(state["profile"])
        learner = _learner(state)
        assignment = profile.assignment
        if assignment is None or assignment.rubric is None:  # the router guarantees this
            raise RuntimeError("The grader node requires a session rubric.")

        answer = next(
            (m.text for m in reversed(state["messages"]) if isinstance(m, HumanMessage)), ""
        )
        grade = await grade_answer(
            self.llm,
            question=assignment.question,
            answer=answer,
            rubric=assignment.rubric,
            subject=profile.subject,
            level=profile.level,
            reference_answer=assignment.reference_answer,
            policy=self.policy,
            learner=learner,
        )
        scaffolding = learner.preferences.scaffolding if learner else "standard"
        reply = format_grade(grade, _language(learner))
        emit(GradeEvent(grade=grade))
        emit(HintEvent(hint_level=0, max_hint_level=self.policy.cap(scaffolding)))
        emit(TokenEvent(text=reply))
        return {
            "messages": [AIMessage(reply)],
            "last_grade": grade.model_dump(mode="json"),
            "hint_level": 0,  # a fresh attempt restarts the hint ladder
        }

    async def clarify(self, state: TutorState) -> dict[str, Any]:
        """Ask a clarifying question. Deterministic: no model call needed."""
        profile = SessionProfile.model_validate(state["profile"])
        reply = clarify_reply(profile, _language(_learner(state)))
        emit(TokenEvent(text=reply))
        return {"messages": [AIMessage(reply)]}

    # ------------------------------------------------------------------ streaming helpers

    async def _stream_reply(self, messages: Sequence[BaseMessage]) -> str:
        """Stream a reply that needs no leak check (explain mode)."""
        chunks: list[str] = []
        async for chunk in self.llm.stream(messages):
            chunks.append(chunk)
            emit(TokenEvent(text=chunk))
        return "".join(chunks).strip()

    async def _guarded_reply(
        self, messages: Sequence[BaseMessage], reference: str | None
    ) -> str | None:
        """Stream a draft through the leak guard; ``None`` means the draft must be discarded."""
        guard = StreamGuard(self.policy, reference)
        stream = self.llm.stream(messages)
        try:
            async for chunk in stream:
                released = guard.feed(chunk)
                if guard.leaked:
                    return None  # stop generating: this draft will be replaced
                if released:
                    emit(TokenEvent(text=released))
        finally:
            close = getattr(stream, "aclose", None)
            if close is not None:
                await close()
        rest = guard.finish()
        if guard.leaked:
            return None
        if rest:
            emit(TokenEvent(text=rest))
        return guard.draft.strip()


def _learner(state: TutorState) -> LearnerContext | None:
    raw = state.get("learner")
    return LearnerContext.model_validate(raw) if raw else None


def _language(learner: LearnerContext | None) -> Language:
    return learner.preferences.language if learner else "en"


def select_route(state: TutorState) -> Route:
    """Conditional-edge function: read the router's decision from state."""
    return state.get("route", "tutor")
