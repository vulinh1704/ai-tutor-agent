"""Checkpointer factory: in-memory by default, SQLite when configured."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver

from ai_tutor_agent.config import CheckpointerBackend, Settings


@asynccontextmanager
async def open_checkpointer(settings: Settings) -> AsyncIterator[BaseCheckpointSaver[Any]]:
    """Yield the configured checkpointer and close it on exit."""
    if settings.checkpointer is CheckpointerBackend.MEMORY:
        yield InMemorySaver()
        return

    try:
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver  # optional extra
    except ImportError as exc:  # pragma: no cover - depends on the installed extras
        raise RuntimeError(
            "CHECKPOINTER=sqlite requires the 'sqlite' extra: "
            "pip install 'ai-tutor-agent[sqlite]' (or uv sync --extra sqlite)."
        ) from exc

    settings.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    async with AsyncSqliteSaver.from_conn_string(str(settings.sqlite_path)) as saver:
        yield saver
