from __future__ import annotations

import runpy
import sys
from collections.abc import Iterator
from typing import Any

import pytest

from ai_tutor_agent import __version__
from ai_tutor_agent.cli import main
from ai_tutor_agent.config import get_settings


@pytest.fixture(autouse=True)
def _fresh_settings() -> Iterator[None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_graph_command_prints_mermaid(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["graph"]) == 0
    out = capsys.readouterr().out
    assert out.lstrip().startswith("---") or "graph TD" in out
    for node in ("router", "tutor", "grader", "clarify"):
        assert node in out


def test_demo_runs_offline(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["demo"]) == 0
    out = capsys.readouterr().out
    assert "[clarify, hint level 0]" in out
    assert "[tutor, hint level 3]" in out
    assert "Score: 5/5 (100%)" in out
    assert '"score": 7' in out


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_python_dash_m_entry_point(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "argv", ["ai-tutor", "--version"])
    with pytest.raises(SystemExit) as exc:
        runpy.run_module("ai_tutor_agent", run_name="__main__")
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_serve_refuses_to_start_without_a_key(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.chdir("/")  # no .env file here
    assert main(["serve"]) == 2
    assert "OPENAI_API_KEY is required" in capsys.readouterr().err


def test_serve_starts_uvicorn(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, Any]] = []
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    monkeypatch.setattr("uvicorn.run", lambda app, **kwargs: calls.append({"app": app, **kwargs}))

    assert main(["serve", "--host", "0.0.0.0", "--port", "9000"]) == 0

    assert calls == [
        {
            "app": "ai_tutor_agent.api.app:create_app",
            "factory": True,
            "host": "0.0.0.0",
            "port": 9000,
            "reload": False,
            "log_level": "info",
        }
    ]
