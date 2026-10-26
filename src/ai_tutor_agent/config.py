"""Application settings loaded from environment variables (and an optional ``.env`` file)."""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any, Final, Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class LLMProvider(StrEnum):
    """Which chat model backs the agent."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    FAKE = "fake"


class CheckpointerBackend(StrEnum):
    """Where LangGraph persists conversation state."""

    MEMORY = "memory"
    SQLITE = "sqlite"


AnthropicEffort = Literal["low", "medium", "high", "xhigh", "max"]
OpenAIReasoningEffort = Literal["none", "minimal", "low", "medium", "high", "xhigh"]

DEFAULT_MODELS: Final[Mapping[LLMProvider, str]] = {
    LLMProvider.OPENAI: "gpt-5.4-mini",
    LLMProvider.ANTHROPIC: "claude-opus-5-5",
    LLMProvider.FAKE: "fake-tutor",
}


class Settings(BaseSettings):
    """Runtime configuration. Every field maps to an upper-case environment variable."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    log_level: str = "INFO"

    # --- LLM ---------------------------------------------------------------
    llm_provider: LLMProvider = LLMProvider.OPENAI
    llm_model: str | None = Field(
        default=None, description="Model name; defaults to a sensible model per provider."
    )
    llm_temperature: float | None = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description=(
            "OpenAI only, and only for models that accept it (gpt-5 reasoning models need "
            "OPENAI_REASONING_EFFORT=none). Claude's current API rejects sampling parameters."
        ),
    )
    llm_max_tokens: int = Field(default=16_000, ge=256)
    llm_timeout_seconds: float = Field(default=60.0, gt=0)
    llm_max_retries: int = Field(default=2, ge=0, le=10)

    openai_api_key: SecretStr | None = None
    openai_base_url: str | None = None
    openai_reasoning_effort: OpenAIReasoningEffort | None = None

    anthropic_api_key: SecretStr | None = None
    anthropic_effort: AnthropicEffort | None = "medium"
    anthropic_server_fallback: bool = Field(
        default=True,
        description="Opt into server-side fallback when a Claude model declines a request.",
    )

    fake_stream_delay_ms: int = Field(
        default=25,
        ge=0,
        le=1000,
        description="Pause between streamed words of the offline model, so replies look typed.",
    )

    # --- Agent -------------------------------------------------------------
    max_hint_level: int = Field(default=3, ge=1, le=5)
    history_window: int = Field(default=20, ge=2, le=200)

    # --- Persistence -------------------------------------------------------
    checkpointer: CheckpointerBackend = CheckpointerBackend.MEMORY
    sqlite_path: Path = Path("data/checkpoints.sqlite")

    # --- HTTP API ----------------------------------------------------------
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        description="Comma-separated browser origins allowed to call the API (the web UI).",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: Any) -> Any:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def resolved_model(self) -> str:
        """The configured model name, or the provider default."""
        return self.llm_model or DEFAULT_MODELS[self.llm_provider]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return process-wide settings (cached)."""
    return Settings()
