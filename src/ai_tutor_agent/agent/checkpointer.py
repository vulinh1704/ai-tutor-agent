"""Persistence factories: in memory by default, SQLite when configured.

The checkpointer holds sessions (LangGraph threads); the store holds what outlives a session
(learner profiles and progress). With SQLite both live in the same database file.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.base import BaseStore
from langgraph.store.memory import InMemoryStore

from ai_tutor_agent.config import CheckpointerBackend, Settings

_SQLITE_EXTRA_HINT = (
    "CHECKPOINTER=sqlite requires the 'sqlite' extra: "
    "pip install 'ai-tutor-agent[sqlite]' (or uv sync --extra sqlite)."
)


@asynccontextmanager
async def open_checkpointer(settings: Settings) -> AsyncIterator[BaseCheckpointSaver[Any]]:
    """Yield the configured checkpointer and close it on exit."""
    if settings.checkpointer is CheckpointerBackend.MEMORY:
        yield InMemorySaver()
        return

    try:
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver  # optional extra
    except ImportError as exc:  # pragma: no cover - depends on the installed extras
        raise RuntimeError(_SQLITE_EXTRA_HINT) from exc

    settings.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    async with AsyncSqliteSaver.from_conn_string(str(settings.sqlite_path)) as saver:
        yield saver


@asynccontextmanager
async def open_store(settings: Settings) -> AsyncIterator[BaseStore]:
    """Yield the configured long-term store (learner profiles and progress)."""
    if settings.checkpointer is CheckpointerBackend.MEMORY:
        yield InMemoryStore()
        return

    try:
        from langgraph.store.sqlite.aio import AsyncSqliteStore  # optional extra
    except ImportError as exc:  # pragma: no cover - depends on the installed extras
        raise RuntimeError(_SQLITE_EXTRA_HINT) from exc

    settings.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    async with AsyncSqliteStore.from_conn_string(str(settings.sqlite_path)) as store:
        await store.setup()
        yield store
