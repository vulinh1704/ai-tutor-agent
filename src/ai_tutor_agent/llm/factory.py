"""Build the configured :class:`~ai_tutor_agent.llm.base.ChatModel` from settings."""

from __future__ import annotations

import logging
from typing import Any, Final

from pydantic import SecretStr

from ai_tutor_agent.config import LLMProvider, Settings
from ai_tutor_agent.llm.base import ChatModel, LangChainChatModel
from ai_tutor_agent.llm.fake import FakeChatModel

logger = logging.getLogger(__name__)

ANTHROPIC_SERVER_FALLBACK_BETA: Final = "server-side-fallback-2026-07-01"


class ConfigurationError(ValueError):
    """The settings cannot produce a working model (for example a missing API key)."""


def build_chat_model(settings: Settings) -> ChatModel:
    """Instantiate the chat model selected by ``LLM_PROVIDER``. Makes no network calls."""
    if settings.llm_provider is LLMProvider.FAKE:
        return FakeChatModel(
            model_name=settings.resolved_model, stream_delay=settings.fake_stream_delay_ms / 1000
        )
    if settings.llm_provider is LLMProvider.OPENAI:
        return _build_openai(settings)
    return _build_anthropic(settings)


def _require_key(key: SecretStr | None, env_var: str, provider: LLMProvider) -> SecretStr:
    if key is None or not key.get_secret_value().strip():
        raise ConfigurationError(
            f"{env_var} is required when LLM_PROVIDER={provider.value}. "
            "Set LLM_PROVIDER=fake to run fully offline."
        )
    return key


def _build_openai(settings: Settings) -> ChatModel:
    from langchain_openai import ChatOpenAI  # lazy: keeps offline startup light

    api_key = _require_key(settings.openai_api_key, "OPENAI_API_KEY", LLMProvider.OPENAI)
    # Field names rather than aliases (model=, api_key=, ...) keep this type-checked.
    client = ChatOpenAI(
        model_name=settings.resolved_model,
        openai_api_key=api_key,
        openai_api_base=settings.openai_base_url,
        temperature=settings.llm_temperature,
        reasoning_effort=settings.openai_reasoning_effort,
        max_tokens=settings.llm_max_tokens,
        request_timeout=settings.llm_timeout_seconds,
        max_retries=settings.llm_max_retries,
    )
    return LangChainChatModel(
        client,
        provider=LLMProvider.OPENAI.value,
        model_name=settings.resolved_model,
        # Native JSON-schema structured output with strict validation on OpenAI's side.
        structured_output_kwargs={"method": "json_schema", "strict": True},
    )


def _build_anthropic(settings: Settings) -> ChatModel:
    from langchain_anthropic import ChatAnthropic  # lazy: keeps offline startup light

    api_key = _require_key(settings.anthropic_api_key, "ANTHROPIC_API_KEY", LLMProvider.ANTHROPIC)
    if settings.llm_temperature is not None:
        logger.warning(
            "LLM_TEMPERATURE is ignored for Anthropic: Claude's current API rejects sampling "
            "parameters. Use ANTHROPIC_EFFORT to trade quality against cost instead."
        )

    betas: list[str] | None = None
    model_kwargs: dict[str, Any] = {}
    if settings.anthropic_server_fallback:
        # If the model declines a request, Anthropic re-runs it server-side on its recommended
        # fallback model. Models without fallback support simply run on their own.
        betas = [ANTHROPIC_SERVER_FALLBACK_BETA]
        model_kwargs["fallbacks"] = "default"

    client = ChatAnthropic(
        model=settings.resolved_model,
        anthropic_api_key=api_key,
        max_tokens=settings.llm_max_tokens,
        default_request_timeout=settings.llm_timeout_seconds,
        max_retries=settings.llm_max_retries,
        reasoning_effort=settings.anthropic_effort,  # sent as output_config.effort
        betas=betas,
        model_kwargs=model_kwargs,
    )
    return LangChainChatModel(
        client,
        provider=LLMProvider.ANTHROPIC.value,
        model_name=settings.resolved_model,
        # Claude's native structured outputs (output_config.format) rather than a forced tool
        # call: current Claude models reject forced tool_choice.
        structured_output_kwargs={"method": "json_schema"},
    )
