"""Streamed chat turns: the event sequence, the leak guard and errors."""

from __future__ import annotations

from typing import Any

import pytest

from ai_tutor_agent.agent.events import DoneEvent, TokenEvent, TurnEvent
from ai_tutor_agent.agent.hint_policy import HintPolicy
from ai_tutor_agent.agent.service import SessionNotFoundError, TutorService
from ai_tutor_agent.llm.base import LLMError
from ai_tutor_agent.llm.fake import FakeChatModel
from ai_tutor_agent.schemas import RouteDecision, SessionProfile


async def _turn(
    service: TutorService, session_id: str, text: str, **kwargs: Any
) -> list[TurnEvent]:
    return [event async for event in service.stream_message(session_id, text, **kwargs)]


def _types(events: list[TurnEvent]) -> list[str]:
    """Event types with consecutive tokens collapsed: route, hint, token, done."""
    types: list[str] = []
    for event in events:
        if not (types and types[-1] == event.type == "token"):
            types.append(event.type)
    return types


def _text(events: list[TurnEvent]) -> str:
    return "".join(e.text for e in events if isinstance(e, TokenEvent))


async def test_tutor_turn_event_sequence(service: TutorService, profile: SessionProfile) -> None:
    session = await service.create_session(profile)

    events = await _turn(service, session.session_id, "How do I start?")

    assert _types(events) == ["route", "hint", "token", "done"]
    route, hint, done = events[0], events[1], events[-1]
    assert route.model_dump() == {
        "type": "route",
        "route": "tutor",
        "reason": "The student is asking for help.",
        "new_problem": False,
    }
    assert hint.model_dump() == {"type": "hint", "hint_level": 1, "max_hint_level": 3}
    assert isinstance(done, DoneEvent)
    assert sum(isinstance(e, TokenEvent) for e in events) > 1  # streamed, not one blob
    assert _text(events).strip() == done.reply
    saved = await service.get_session(session.session_id)
    assert saved.messages[-1].text == done.reply
    assert saved.hint_level == done.hint_level == 1


async def test_clarify_turn(service: TutorService, profile: SessionProfile) -> None:
    session = await service.create_session(profile)
    events = await _turn(service, session.session_id, "help")
    assert _types(events) == ["route", "token", "done"]
    assert _text(events).startswith("I'd love to help")


async def test_submitted_answer_skips_the_router(
    service: TutorService, fake_llm: FakeChatModel, profile: SessionProfile
) -> None:
    session = await service.create_session(profile)

    events = await _turn(
        service,
        session.session_id,
        "subtract 5 from both sides, divide both sides by 3, x = 5",
        intent="submit",
    )

    assert _types(events) == ["route", "grade", "hint", "token", "done"]
    grade_event, done = events[1], events[-1]
    assert isinstance(done, DoneEvent)
    assert grade_event.model_dump()["grade"] == done.model_dump()["grade"]
    assert done.grade is not None
    assert done.grade.score == 5
    assert not any(c.schema is RouteDecision for c in fake_llm.calls)


async def test_leaking_draft_is_reset_and_replaced(
    service: TutorService, fake_llm: FakeChatModel, profile: SessionProfile
) -> None:
    fake_llm.queue_reply(
        "Nice effort on this one! Here is the whole thing: the final answer is x = 5, easy.",
        "Try undoing the + 5 first. What do you get?",
    )
    session = await service.create_session(profile)

    events = await _turn(service, session.session_id, "Just tell me x please")

    assert _types(events) == ["route", "hint", "token", "reset", "token", "done"]
    reset_at = next(i for i, e in enumerate(events) if e.type == "reset")
    before, after = _text(events[:reset_at]), _text(events[reset_at:])
    assert before.startswith("Nice effort")
    assert "answer" not in before  # the leaking words were held back, never shown
    assert after == "Try undoing the + 5 first. What do you get?"
    assert events[-1].model_dump()["reply"] == after


async def test_persistent_leak_streams_the_fallback(
    service: TutorService, fake_llm: FakeChatModel, profile: SessionProfile
) -> None:
    fake_llm.queue_reply("x = 5", "The answer is 5")
    session = await service.create_session(profile)

    events = await _turn(service, session.session_id, "Just tell me x please")

    assert _types(events) == ["route", "hint", "reset", "reset", "token", "done"]
    assert _text(events) == HintPolicy().fallback_reply(1)


async def test_explain_mode_streams_without_the_ladder(
    service: TutorService, fake_llm: FakeChatModel, profile: SessionProfile
) -> None:
    fake_llm.queue_reply("Subtract 5, then divide by 3, so x = 5. Why does that work?")
    session = await service.create_session(profile.model_copy(update={"mode": "explain"}))

    events = await _turn(service, session.session_id, "Explain the steps")

    assert _types(events) == ["route", "hint", "token", "done"]
    assert events[1].model_dump()["hint_level"] == 0
    assert _text(events) == "Subtract 5, then divide by 3, so x = 5. Why does that work?"


async def test_provider_failure_mid_stream_raises(
    service: TutorService, fake_llm: FakeChatModel, profile: SessionProfile
) -> None:
    fake_llm.queue_reply(LLMError("upstream timeout"))
    session = await service.create_session(profile)
    seen: list[str] = []

    async def listen() -> None:
        async for event in service.stream_message(session.session_id, "How do I start?"):
            seen.append(event.type)

    with pytest.raises(LLMError, match="upstream timeout"):
        await listen()
    assert seen == ["route", "hint"]
    # A failed turn is not half-saved as a reply.
    assert all(m.type == "human" for m in (await service.get_session(session.session_id)).messages)


async def test_unknown_session_fails_before_streaming(service: TutorService) -> None:
    with pytest.raises(SessionNotFoundError):
        await _turn(service, "missing", "hello")


async def test_turn_completes_when_the_listener_leaves(
    service: TutorService, profile: SessionProfile
) -> None:
    session = await service.create_session(profile)
    stream = service.stream_message(session.session_id, "How do I start?")
    first = await anext(stream)
    await stream.aclose()  # e.g. the browser tab was closed
    await service.aclose()

    assert first.type == "route"
    saved = await service.get_session(session.session_id)
    assert [m.type for m in saved.messages] == ["human", "ai"]
