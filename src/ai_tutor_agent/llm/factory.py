"""Build the configured :class:`~ai_tutor_agent.llm.base.ChatModel` from settings."""

from __future__ import annotations

from pydantic import SecretStr

from ai_tutor_agent.config import LLMProvider, Settings
from ai_tutor_agent.llm.base import ChatModel, LangChainChatModel
from ai_tutor_agent.llm.fake import FakeChatModel


class ConfigurationError(ValueError):
    """The settings cannot produce a working model (for example a missing API key)."""


def build_chat_model(settings: Settings) -> ChatModel:
    """Instantiate the chat model selected by ``LLM_PROVIDER``. Makes no network calls."""
    if settings.llm_provider is LLMProvider.FAKE:
        return FakeChatModel(model_name=settings.resolved_model)
    return _build_openai(settings)


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
