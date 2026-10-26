from pathlib import Path

import pytest
from pydantic import ValidationError

from ai_tutor_agent.config import CheckpointerBackend, LLMProvider, Settings


def _settings() -> Settings:
    return Settings(_env_file=None)


def test_defaults() -> None:
    settings = _settings()
    assert settings.llm_provider is LLMProvider.OPENAI
    assert settings.resolved_model == "gpt-5.4-mini"
    assert settings.checkpointer is CheckpointerBackend.MEMORY
    assert settings.llm_temperature is None
    assert settings.max_hint_level == 3


@pytest.mark.parametrize(
    ("provider", "model"),
    [("openai", "gpt-5.4-mini"), ("anthropic", "claude-opus-5-5"), ("fake", "fake-tutor")],
)
def test_default_model_per_provider(
    monkeypatch: pytest.MonkeyPatch, provider: str, model: str
) -> None:
    monkeypatch.setenv("LLM_PROVIDER", provider)
    assert _settings().resolved_model == model


def test_reads_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("LLM_MODEL", "claude-sonnet-5-5")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("ANTHROPIC_EFFORT", "low")
    monkeypatch.setenv("CHECKPOINTER", "sqlite")
    monkeypatch.setenv("SQLITE_PATH", "/tmp/tutor.sqlite")

    settings = _settings()

    assert settings.llm_provider is LLMProvider.ANTHROPIC
    assert settings.resolved_model == "claude-sonnet-5-5"
    assert settings.anthropic_effort == "low"
    assert settings.checkpointer is CheckpointerBackend.SQLITE
    assert settings.sqlite_path == Path("/tmp/tutor.sqlite")


def test_api_keys_are_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-secret")
    settings = _settings()
    assert settings.openai_api_key is not None
    assert settings.openai_api_key.get_secret_value() == "sk-test-secret"
    assert "sk-test-secret" not in repr(settings)


def test_rejects_unknown_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "unknown")
    with pytest.raises(ValidationError):
        _settings()
