"""Tests for the LangChain adapter, using an in-process stub chat model (no network)."""

from __future__ import annotations

from typing import Any

import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import Runnable, RunnableLambda
from pydantic import Field

from ai_tutor_agent.llm.base import (
    ChatModel,
    LangChainChatModel,
    LLMError,
    LLMOutputError,
    LLMRefusalError,
)
from ai_tutor_agent.schemas import RouteDecision

DECISION = RouteDecision(route="tutor", new_problem=False, reason="asks for help")


class StubChatModel(BaseChatModel):
    replies: list[Any] = Field(default_factory=list)  # AIMessage | Exception
    structured_payload: Any = None
    structured_calls: list[dict[str, Any]] = Field(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "stub"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return ChatResult(generations=[ChatGeneration(message=reply)])

    def with_structured_output(  # type: ignore[override]
        self, schema: Any, *, include_raw: bool = False, **kwargs: Any
    ) -> Runnable[Any, Any]:
        self.structured_calls.append({"schema": schema, "include_raw": include_raw, **kwargs})
        payload = self.structured_payload
        if isinstance(payload, Exception):

            def fail(_: Any) -> Any:
                raise payload

            return RunnableLambda(fail)
        return RunnableLambda(lambda _: payload)


def _adapter(stub: StubChatModel, **kwargs: Any) -> LangChainChatModel:
    return LangChainChatModel(stub, provider="stub", model_name="stub-1", **kwargs)


def test_adapter_satisfies_the_protocol() -> None:
    assert isinstance(_adapter(StubChatModel()), ChatModel)


async def test_complete_returns_text_without_reasoning_blocks() -> None:
    reply = AIMessage(
        content=[{"type": "thinking", "thinking": ""}, {"type": "text", "text": " Try it! "}]
    )
    assert await _adapter(StubChatModel(replies=[reply])).complete([HumanMessage("hi")]) == (
        "Try it!"
    )


@pytest.mark.parametrize(
    "reply",
    [
        AIMessage("", response_metadata={"stop_reason": "refusal"}),  # Anthropic
        AIMessage("", additional_kwargs={"refusal": "I can't help with that."}),  # OpenAI
    ],
)
async def test_complete_raises_on_refusal(reply: AIMessage) -> None:
    with pytest.raises(LLMRefusalError):
        await _adapter(StubChatModel(replies=[reply])).complete([HumanMessage("hi")])


async def test_complete_rejects_empty_reply() -> None:
    with pytest.raises(LLMOutputError, match="empty"):
        await _adapter(StubChatModel(replies=[AIMessage("  ")])).complete([HumanMessage("hi")])


async def test_complete_wraps_provider_errors() -> None:
    stub = StubChatModel(replies=[ConnectionError("boom")])
    with pytest.raises(LLMError, match="stub request failed"):
        await _adapter(stub).complete([HumanMessage("hi")])


async def test_structured_passes_provider_kwargs_and_caches_runnable() -> None:
    stub = StubChatModel(
        structured_payload={"raw": AIMessage("{}"), "parsed": DECISION, "parsing_error": None}
    )
    adapter = _adapter(stub, structured_output_kwargs={"method": "json_schema"})

    assert await adapter.structured([HumanMessage("hi")], RouteDecision) is DECISION
    assert await adapter.structured([HumanMessage("hi")], RouteDecision) is DECISION
    assert stub.structured_calls == [
        {"schema": RouteDecision, "include_raw": True, "method": "json_schema"}
    ]


async def test_structured_validates_dict_payloads() -> None:
    stub = StubChatModel(
        structured_payload={"raw": None, "parsed": DECISION.model_dump(), "parsing_error": None}
    )
    assert await _adapter(stub).structured([HumanMessage("hi")], RouteDecision) == DECISION


@pytest.mark.parametrize(
    ("payload", "error"),
    [
        ({"raw": AIMessage(""), "parsed": None, "parsing_error": ValueError("bad")}, "parse"),
        ({"raw": None, "parsed": {"route": "nowhere"}, "parsing_error": None}, "Invalid"),
        (DECISION, "Unexpected"),
    ],
)
async def test_structured_output_errors(payload: Any, error: str) -> None:
    stub = StubChatModel(structured_payload=payload)
    with pytest.raises(LLMOutputError, match=error):
        await _adapter(stub).structured([HumanMessage("hi")], RouteDecision)


async def test_structured_detects_refusal_in_raw_message() -> None:
    refusal = AIMessage("", response_metadata={"stop_reason": "refusal"})
    stub = StubChatModel(structured_payload={"raw": refusal, "parsed": None, "parsing_error": None})
    with pytest.raises(LLMRefusalError):
        await _adapter(stub).structured([HumanMessage("hi")], RouteDecision)


async def test_structured_wraps_provider_errors() -> None:
    stub = StubChatModel(structured_payload=TimeoutError("slow"))
    with pytest.raises(LLMError, match="slow"):
        await _adapter(stub).structured([HumanMessage("hi")], RouteDecision)
