"""Provider selection. Every test runs with sockets disabled to prove no network is touched."""

from __future__ import annotations

import socket
from typing import Any

import pytest
from langchain_openai import ChatOpenAI

from ai_tutor_agent.config import Settings
from ai_tutor_agent.llm.base import LangChainChatModel
from ai_tutor_agent.llm.factory import ConfigurationError, build_chat_model
from ai_tutor_agent.llm.fake import FakeChatModel


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


@pytest.mark.parametrize(("provider", "env_var"), [("openai", "OPENAI_API_KEY")])
@pytest.mark.parametrize("key", [None, "  "])
def test_missing_api_key_is_a_configuration_error(
    provider: str, env_var: str, key: str | None
) -> None:
    settings = _settings(llm_provider=provider, openai_api_key=key)
    with pytest.raises(ConfigurationError, match=f"{env_var} is required"):
        build_chat_model(settings)
