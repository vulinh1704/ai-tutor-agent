"""Provider-agnostic chat model interface used by the agent.

The graph only depends on :class:`ChatModel`: two async methods, one for free text and one
for Pydantic-validated structured output. Real providers are LangChain chat models wrapped by
:class:`LangChainChatModel`; tests and the offline demo use
:class:`~ai_tutor_agent.llm.fake.FakeChatModel`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol, TypeVar, runtime_checkable

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.runnables import Runnable
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


class LLMError(RuntimeError):
    """The model provider failed or returned unusable output."""


class LLMRefusalError(LLMError):
    """The model declined to answer (for example a safety refusal)."""


class LLMOutputError(LLMError):
    """The model's output could not be parsed or validated."""


@runtime_checkable
class ChatModel(Protocol):
    """What the agent needs from a language model."""

    @property
    def provider(self) -> str: ...

    @property
    def model_name(self) -> str: ...

    async def complete(self, messages: Sequence[BaseMessage]) -> str:
        """Return the model's text reply."""
        ...

    async def structured(self, messages: Sequence[BaseMessage], schema: type[T]) -> T:
        """Return the model's reply parsed and validated as ``schema``."""
        ...


def raise_if_refused(message: BaseMessage) -> None:
    """Translate provider-specific refusal signals into :class:`LLMRefusalError`."""
    if message.response_metadata.get("stop_reason") == "refusal":  # Anthropic
        raise LLMRefusalError("The model declined this request.")
    refusal = message.additional_kwargs.get("refusal")  # OpenAI
    if refusal:
        raise LLMRefusalError(str(refusal))


class LangChainChatModel:
    """Adapter exposing any LangChain ``BaseChatModel`` through :class:`ChatModel`."""

    def __init__(
        self,
        client: BaseChatModel,
        *,
        provider: str,
        model_name: str,
        structured_output_kwargs: Mapping[str, Any] | None = None,
    ) -> None:
        self.client = client
        self._provider = provider
        self._model_name = model_name
        self._structured_output_kwargs = dict(structured_output_kwargs or {})
        self._structured_runnables: dict[type[BaseModel], Runnable[Any, Any]] = {}

    @property
    def provider(self) -> str:
        return self._provider

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def structured_output_kwargs(self) -> dict[str, Any]:
        return dict(self._structured_output_kwargs)

    async def complete(self, messages: Sequence[BaseMessage]) -> str:
        try:
            response = await self.client.ainvoke(list(messages))
        except Exception as exc:
            raise LLMError(f"{self.provider} request failed: {exc}") from exc
        raise_if_refused(response)
        text = response.text.strip()  # skips thinking/reasoning blocks
        if not text:
            raise LLMOutputError("The model returned an empty reply.")
        return text

    async def structured(self, messages: Sequence[BaseMessage], schema: type[T]) -> T:
        runnable = self._structured_runnable(schema)
        try:
            result = await runnable.ainvoke(list(messages))
        except Exception as exc:
            raise LLMError(f"{self.provider} request failed: {exc}") from exc
        if not isinstance(result, dict):
            raise LLMOutputError(f"Unexpected structured output payload: {type(result).__name__}")

        raw = result.get("raw")
        if isinstance(raw, BaseMessage):
            raise_if_refused(raw)
        if result.get("parsing_error") is not None:
            raise LLMOutputError(f"Could not parse {schema.__name__}: {result['parsing_error']}")

        parsed = result.get("parsed")
        if isinstance(parsed, schema):
            return parsed
        try:
            return schema.model_validate(parsed)
        except ValidationError as exc:
            raise LLMOutputError(f"Invalid {schema.__name__}: {exc}") from exc

    def _structured_runnable(self, schema: type[BaseModel]) -> Runnable[Any, Any]:
        if schema not in self._structured_runnables:
            self._structured_runnables[schema] = self.client.with_structured_output(
                schema, include_raw=True, **self._structured_output_kwargs
            )
        return self._structured_runnables[schema]
