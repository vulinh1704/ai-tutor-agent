"""Graph behaviour, driven through the session service with the deterministic fake model."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from ai_tutor_agent.agent.checkpointer import open_checkpointer
from ai_tutor_agent.agent.graph import build_graph
from ai_tutor_agent.agent.hint_policy import HintPolicy
from ai_tutor_agent.agent.service import SessionNotFoundError, TutorService
from ai_tutor_agent.config import Settings
from ai_tutor_agent.llm.base import LLMOutputError
from ai_tutor_agent.llm.fake import FakeChatModel
from ai_tutor_agent.prompts import LEAK_RETRY_NOTE
from ai_tutor_agent.schemas import Route, RouteDecision, SessionProfile


def _route(route: Route, *, new_problem: bool = False) -> RouteDecision:
    return RouteDecision(route=route, new_problem=new_problem, reason="test")


async def test_mermaid_diagram_contains_every_node() -> None:
    mermaid = build_graph(FakeChatModel()).get_graph().draw_mermaid()
    for node in ("router", "tutor", "grader", "clarify"):
        assert node in mermaid


async def test_create_and_get_session(service: TutorService, profile: SessionProfile) -> None:
    created = await service.create_session(profile)
    loaded = await service.get_session(created.session_id)
    assert loaded.profile == profile
    assert loaded.messages == []
    assert loaded.created_at == created.created_at


async def test_unknown_session_raises(service: TutorService) -> None:
    with pytest.raises(SessionNotFoundError):
        await service.get_session("missing")
    with pytest.raises(SessionNotFoundError):
        await service.send_message("missing", "hello")


async def test_vague_message_gets_a_clarifying_question(
    service: TutorService, fake_llm: FakeChatModel, profile: SessionProfile
) -> None:
    session = await service.create_session(profile)
    turn = await service.send_message(session.session_id, "help")
    assert turn.route == "clarify"
    assert "Which part are you stuck on" in turn.reply
    assert [c.kind for c in fake_llm.calls] == ["structured"]  # router only, no text call


async def test_hint_level_climbs_on_consecutive_tutor_turns(
    service: TutorService, fake_llm: FakeChatModel, profile: SessionProfile
) -> None:
    session = await service.create_session(profile)
    levels = []
    for text in ("How do I start?", "Still confused about it", "What next?", "Hmm, and then?"):
        levels.append((await service.send_message(session.session_id, text)).hint_level)

    assert levels == [1, 2, 3, 3]
    tutor_prompts = [c.system_prompt for c in fake_llm.calls if c.kind == "stream"]
    assert "<hint_level>\n1\n</hint_level>" in tutor_prompts[0]
    assert "<hint_level>\n3\n</hint_level>" in tutor_prompts[-1]
    assert "Never state the final answer" in tutor_prompts[0]


async def test_new_problem_restarts_hints(
    service: TutorService, fake_llm: FakeChatModel, profile: SessionProfile
) -> None:
    session = await service.create_session(profile)
    await service.send_message(session.session_id, "How do I start?")
    await service.send_message(session.session_id, "And then?")
    fake_llm.queue_structured(_route("tutor", new_problem=True))
    turn = await service.send_message(session.session_id, "OK, a different one: 2x = 8")
    assert turn.hint_level == 1


async def test_leaked_answer_is_regenerated(
    service: TutorService, fake_llm: FakeChatModel, profile: SessionProfile
) -> None:
    fake_llm.queue_reply("Easy: x = 5.", "Try undoing the + 5 first. What do you get?")
    session = await service.create_session(profile)

    turn = await service.send_message(session.session_id, "Just tell me x please")

    assert turn.reply == "Try undoing the + 5 first. What do you get?"
    tutor_calls = [c for c in fake_llm.calls if c.kind == "stream"]
    assert len(tutor_calls) == 2
    assert LEAK_RETRY_NOTE in tutor_calls[1].system_prompt


async def test_persistent_leak_falls_back_to_a_safe_hint(
    service: TutorService, fake_llm: FakeChatModel, profile: SessionProfile
) -> None:
    fake_llm.queue_reply("x = 5", "The answer is 5")
    session = await service.create_session(profile)

    turn = await service.send_message(session.session_id, "Just tell me x please")

    assert turn.reply == HintPolicy().fallback_reply(1)
    snapshot = await service.get_session(session.session_id)
    assert snapshot.messages[-1].text == turn.reply  # the leaked drafts were never stored


async def test_explain_mode_skips_the_hint_ladder(
    service: TutorService, fake_llm: FakeChatModel, profile: SessionProfile
) -> None:
    fake_llm.queue_reply("Subtract 5, then divide by 3, so x = 5. Why does that work?")
    session = await service.create_session(profile.model_copy(update={"mode": "explain"}))

    turn = await service.send_message(session.session_id, "Can you explain the steps?")

    assert turn.reply.startswith("Subtract 5")  # full explanations are allowed
    assert turn.hint_level == 0
    assert "Mode: explain" in fake_llm.calls[-1].system_prompt


async def test_answer_submission_is_graded_against_the_session_rubric(
    service: TutorService, profile: SessionProfile
) -> None:
    session = await service.create_session(profile)
    await service.send_message(session.session_id, "How do I start?")

    turn = await service.send_message(
        session.session_id,
        "My answer: subtract 5 from both sides, then divide both sides by 3, so x = 5",
    )

    assert turn.route == "grader"
    assert turn.grade is not None
    assert (turn.grade.score, turn.grade.max_score) == (5, 5)
    assert turn.reply.startswith("Score: 5/5")
    assert turn.hint_level == 0  # a graded attempt restarts the hint ladder


async def test_grader_route_without_rubric_falls_back_to_tutor(
    service: TutorService, fake_llm: FakeChatModel
) -> None:
    session = await service.create_session(SessionProfile(subject="history", level="grade 9"))
    fake_llm.queue_structured(_route("grader"))

    turn = await service.send_message(session.session_id, "My answer is 1066")

    assert turn.route == "tutor"
    assert turn.grade is None


async def test_router_failure_defaults_to_tutor(
    service: TutorService, fake_llm: FakeChatModel, profile: SessionProfile
) -> None:
    fake_llm.queue_structured(LLMOutputError("not json"))
    session = await service.create_session(profile)
    turn = await service.send_message(session.session_id, "help")
    assert turn.route == "tutor"


async def test_prompts_only_include_the_recent_history_window(profile: SessionProfile) -> None:
    llm = FakeChatModel()
    graph = build_graph(llm, checkpointer=InMemorySaver(), history_window=4)
    service = TutorService(graph, llm, HintPolicy())
    session = await service.create_session(profile)
    for i in range(4):
        await service.send_message(session.session_id, f"Question number {i}?")

    last_router_call = next(c for c in reversed(llm.calls) if c.kind == "structured")
    assert len(last_router_call.messages) <= 1 + 4  # system prompt + window
    assert len((await service.get_session(session.session_id)).messages) == 8


async def test_concurrent_turns_on_one_session_are_serialised(
    service: TutorService, profile: SessionProfile
) -> None:
    session = await service.create_session(profile)
    await asyncio.gather(
        service.send_message(session.session_id, "First question?"),
        service.send_message(session.session_id, "Second question?"),
    )
    messages = (await service.get_session(session.session_id)).messages
    assert [m.type for m in messages] == ["human", "ai", "human", "ai"]


async def test_sqlite_checkpointer_persists_sessions(
    tmp_path: Path, profile: SessionProfile
) -> None:
    settings = Settings(
        _env_file=None,
        llm_provider="fake",
        checkpointer="sqlite",
        sqlite_path=tmp_path / "nested" / "checkpoints.sqlite",
    )
    llm = FakeChatModel()

    async with open_checkpointer(settings) as saver:
        service = TutorService(build_graph(llm, checkpointer=saver), llm, HintPolicy())
        session = await service.create_session(profile)
        await service.send_message(session.session_id, "How do I start?")

    async with open_checkpointer(settings) as saver:  # a fresh process would do the same
        service = TutorService(build_graph(llm, checkpointer=saver), llm, HintPolicy())
        restored = await service.get_session(session.session_id)

    assert restored.profile == profile
    assert [m.type for m in restored.messages] == ["human", "ai"]
    assert restored.hint_level == 1
