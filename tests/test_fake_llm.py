import pytest
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from ai_tutor_agent.llm.base import ChatModel, LLMError, LLMOutputError
from ai_tutor_agent.llm.fake import FakeChatModel
from ai_tutor_agent.prompts import grader_messages, router_messages, tutor_messages
from ai_tutor_agent.schemas import GraderOutput, RouteDecision, Rubric, SessionProfile


def test_fake_satisfies_the_protocol() -> None:
    assert isinstance(FakeChatModel(), ChatModel)


@pytest.mark.parametrize(
    ("message", "route", "new_problem"),
    [
        ("hi", "clarify", False),
        ("help", "clarify", False),
        ("I'm stuck", "clarify", False),
        ("How do I factor x^2 + 5x + 6?", "tutor", False),
        ("My answer is 42", "grader", False),
        ("is this right? x = 3", "grader", False),
        ("Let's try the next problem: 2x = 8", "tutor", True),
    ],
)
async def test_route_heuristics(
    profile: SessionProfile, message: str, route: str, new_problem: bool
) -> None:
    decision = await FakeChatModel().structured(
        router_messages(profile, [HumanMessage(message)]), RouteDecision
    )
    assert decision.route == route
    assert decision.new_problem is new_problem


async def test_tutor_reply_follows_hint_level(profile: SessionProfile) -> None:
    llm = FakeChatModel()
    history = [HumanMessage("How do I start?")]
    nudge = await llm.complete(tutor_messages(profile, history, hint_level=1))
    worked = await llm.complete(tutor_messages(profile, history, hint_level=3))
    assert "what do you already know" in nudge.lower()
    assert "simpler example" in worked


async def test_tutor_reply_in_explain_mode(profile: SessionProfile) -> None:
    explain = profile.model_copy(update={"mode": "explain"})
    reply = await FakeChatModel().complete(tutor_messages(explain, [HumanMessage("Why?")], 0))
    assert "step by step" in reply


async def test_heuristic_grader_scores_keyword_coverage(rubric: Rubric) -> None:
    messages = grader_messages(
        question="Solve for x: 3x + 5 = 20",
        answer="I subtracted 5 from both sides and got x = 5",
        rubric=rubric,
        subject="algebra",
        level="grade 8",
    )
    output = await FakeChatModel().structured(messages, GraderOutput)
    points = {a.criterion_id: a.points for a in output.assessments}
    assert points["answer"] == 2  # "x = 5" stated
    assert 0 < points["method"] < 3  # subtraction yes, division no
    assert "Look again" in output.next_step_hint


async def test_scripted_outputs_take_priority() -> None:
    scripted = RouteDecision(route="grader", new_problem=False, reason="scripted")
    llm = FakeChatModel(replies=["scripted reply"], structured=[scripted])
    assert await llm.complete([HumanMessage("hi")]) == "scripted reply"
    assert await llm.structured([HumanMessage("hi")], RouteDecision) is scripted
    # Queues are consumed: the heuristics take over afterwards.
    assert (await llm.structured([HumanMessage("hi")], RouteDecision)).route == "clarify"
    assert [c.kind for c in llm.calls] == ["complete", "structured", "structured"]


async def test_scripted_exceptions_are_raised() -> None:
    llm = FakeChatModel(replies=[LLMError("down")], structured=[LLMOutputError("bad json")])
    with pytest.raises(LLMError, match="down"):
        await llm.complete([HumanMessage("hi")])
    with pytest.raises(LLMOutputError, match="bad json"):
        await llm.structured([HumanMessage("hi")], RouteDecision)


async def test_stream_matches_complete_word_by_word(profile: SessionProfile) -> None:
    messages = tutor_messages(profile, [HumanMessage("How do I start?")], hint_level=1)
    llm = FakeChatModel()
    chunks = [chunk async for chunk in llm.stream(messages)]
    assert len(chunks) > 5
    assert "".join(chunks) == await llm.complete(messages)
    assert [c.kind for c in llm.calls] == ["stream", "complete"]


async def test_stream_uses_scripted_replies_and_errors() -> None:
    llm = FakeChatModel(replies=["Two words", LLMError("down")])
    assert [c async for c in llm.stream([HumanMessage("hi")])] == ["Two ", "words"]
    with pytest.raises(LLMError, match="down"):
        [c async for c in llm.stream([HumanMessage("hi")])]


async def test_stream_delay_paces_the_words(monkeypatch: pytest.MonkeyPatch) -> None:
    pauses: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        pauses.append(seconds)

    monkeypatch.setattr("ai_tutor_agent.llm.fake.asyncio.sleep", fake_sleep)
    llm = FakeChatModel(replies=["one two three"], stream_delay=0.02)
    assert "".join([c async for c in llm.stream([HumanMessage("hi")])]) == "one two three"
    assert pauses == [0.02, 0.02, 0.02]


async def test_unknown_schema_has_no_heuristic() -> None:
    class Unknown(BaseModel):
        value: int

    with pytest.raises(LLMOutputError, match="no heuristic for Unknown"):
        await FakeChatModel().structured([HumanMessage("hi")], Unknown)
