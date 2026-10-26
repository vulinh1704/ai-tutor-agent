"""Provider selection. Every test runs with sockets disabled to prove no network is touched."""

from __future__ import annotations

import logging
import socket
from typing import Any

import pytest
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from ai_tutor_agent.config import Settings
from ai_tutor_agent.llm.base import LangChainChatModel
from ai_tutor_agent.llm.factory import (
    ANTHROPIC_SERVER_FALLBACK_BETA,
    ConfigurationError,
    build_chat_model,
)
from ai_tutor_agent.llm.fake import FakeChatModel
from ai_tutor_agent.schemas import GraderOutput


@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*_: Any, **__: Any) -> None:
        raise AssertionError("network access attempted")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


def _settings(**values: Any) -> Settings:
    return Settings(_env_file=None, **values)


def test_fake_provider() -> None:
    llm = build_chat_model(_settings(llm_provider="fake"))
    assert isinstance(llm, FakeChatModel)
    assert (llm.provider, llm.model_name) == ("fake", "fake-tutor")


def test_openai_provider_builds_chat_openai() -> None:
    llm = build_chat_model(_settings(llm_provider="openai", openai_api_key="sk-test"))

    assert isinstance(llm, LangChainChatModel)
    assert isinstance(llm.client, ChatOpenAI)
    assert (llm.provider, llm.model_name) == ("openai", "gpt-5.4-mini")
    assert llm.client.model_name == "gpt-5.4-mini"
    assert llm.client.temperature is None
    assert llm.client.max_tokens == 16_000
    assert llm.structured_output_kwargs == {"method": "json_schema", "strict": True}


def test_openai_provider_honours_overrides() -> None:
    llm = build_chat_model(
        _settings(
            llm_provider="openai",
            openai_api_key="sk-test",
            llm_model="gpt-5.5",
            openai_reasoning_effort="none",
            llm_temperature=0.3,
            openai_base_url="https://llm-gateway.example.com/v1",
        )
    )
    assert isinstance(llm, LangChainChatModel)
    assert isinstance(llm.client, ChatOpenAI)
    assert llm.client.model_name == "gpt-5.5"
    assert llm.client.reasoning_effort == "none"
    assert llm.client.temperature == 0.3  # gpt-5 models only accept it with effort "none"
    assert llm.client.openai_api_base == "https://llm-gateway.example.com/v1"


def test_anthropic_provider_builds_chat_anthropic() -> None:
    llm = build_chat_model(_settings(llm_provider="anthropic", anthropic_api_key="sk-ant-test"))

    assert isinstance(llm, LangChainChatModel)
    assert isinstance(llm.client, ChatAnthropic)
    assert (llm.provider, llm.model_name) == ("anthropic", "claude-opus-5-5")
    assert llm.client.model == "claude-opus-5-5"
    assert llm.client.reasoning_effort == "medium"
    assert llm.client.betas == [ANTHROPIC_SERVER_FALLBACK_BETA]
    assert llm.client.model_kwargs == {"fallbacks": "default"}
    # Native structured outputs, not a forced tool call.
    assert llm.structured_output_kwargs == {"method": "json_schema"}


def _anthropic_payload(llm: LangChainChatModel, **kwargs: Any) -> dict[str, Any]:
    assert isinstance(llm.client, ChatAnthropic)
    # Private helper, used to inspect the exact request body without sending it.
    payload: dict[str, Any] = llm.client._get_request_payload([HumanMessage("hi")], **kwargs)
    return payload


def test_anthropic_request_body() -> None:
    llm = build_chat_model(_settings(llm_provider="anthropic", anthropic_api_key="sk-ant-test"))
    assert isinstance(llm, LangChainChatModel)

    payload = _anthropic_payload(llm)

    assert payload["model"] == "claude-opus-5-5"
    assert payload["max_tokens"] == 16_000
    assert payload["output_config"] == {"effort": "medium"}
    assert payload["fallbacks"] == "default"
    assert payload["betas"] == [ANTHROPIC_SERVER_FALLBACK_BETA]
    assert not {"temperature", "top_p", "top_k"} & payload.keys()


def test_anthropic_structured_output_uses_output_config_format() -> None:
    llm = build_chat_model(_settings(llm_provider="anthropic", anthropic_api_key="sk-ant-test"))
    assert isinstance(llm, LangChainChatModel)
    assert isinstance(llm.client, ChatAnthropic)

    runnable = llm.client.with_structured_output(GraderOutput, **llm.structured_output_kwargs)
    payload = _anthropic_payload(llm, **runnable.first.kwargs)  # type: ignore[attr-defined]

    assert payload["output_config"]["format"]["type"] == "json_schema"
    assert payload["output_config"]["effort"] == "medium"
    assert "tool_choice" not in payload


def test_anthropic_without_server_fallback() -> None:
    llm = build_chat_model(
        _settings(
            llm_provider="anthropic",
            anthropic_api_key="sk-ant-test",
            anthropic_server_fallback=False,
            anthropic_effort=None,
            llm_model="claude-haiku-5-5",
        )
    )
    assert isinstance(llm, LangChainChatModel)
    payload = _anthropic_payload(llm)
    assert payload["model"] == "claude-haiku-5-5"
    assert not {"betas", "fallbacks", "output_config"} & payload.keys()


def test_anthropic_ignores_temperature(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        llm = build_chat_model(
            _settings(llm_provider="anthropic", anthropic_api_key="k", llm_temperature=0.2)
        )
    assert isinstance(llm, LangChainChatModel)
    assert "LLM_TEMPERATURE is ignored" in caplog.text
    assert "temperature" not in _anthropic_payload(llm)


@pytest.mark.parametrize(
    ("provider", "env_var"), [("openai", "OPENAI_API_KEY"), ("anthropic", "ANTHROPIC_API_KEY")]
)
@pytest.mark.parametrize("key", [None, "  "])
def test_missing_api_key_is_a_configuration_error(
    provider: str, env_var: str, key: str | None
) -> None:
    settings = _settings(llm_provider=provider, openai_api_key=key, anthropic_api_key=key)
    with pytest.raises(ConfigurationError, match=f"{env_var} is required"):
        build_chat_model(settings)
