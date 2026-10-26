"""FastAPI application factory.

Run with ``ai-tutor serve`` or ``uvicorn --factory ai_tutor_agent.api.app:create_app``.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from ai_tutor_agent import __version__
from ai_tutor_agent.agent.checkpointer import open_checkpointer
from ai_tutor_agent.agent.graph import build_graph
from ai_tutor_agent.agent.hint_policy import HintPolicy
from ai_tutor_agent.agent.service import TutorService
from ai_tutor_agent.api.errors import register_exception_handlers
from ai_tutor_agent.api.routes import router
from ai_tutor_agent.config import Settings, get_settings
from ai_tutor_agent.llm.base import ChatModel
from ai_tutor_agent.llm.factory import build_chat_model

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None, *, llm: ChatModel | None = None) -> FastAPI:
    """Build the app. ``llm`` overrides the configured provider (handy in tests)."""
    settings = settings or get_settings()
    chat_model = llm or build_chat_model(settings)  # fail fast on bad configuration
    policy = HintPolicy(max_level=settings.max_hint_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        async with open_checkpointer(settings) as checkpointer:
            graph = build_graph(
                chat_model,
                checkpointer=checkpointer,
                policy=policy,
                history_window=settings.history_window,
            )
            app.state.settings = settings
            app.state.service = TutorService(graph, chat_model, policy)
            logger.info(
                "AI tutor ready: provider=%s model=%s checkpointer=%s",
                chat_model.provider,
                chat_model.model_name,
                settings.checkpointer.value,
            )
            yield

    app = FastAPI(
        title="AI Tutor Agent",
        version=__version__,
        summary="Socratic tutoring and rubric-based grading on FastAPI + LangGraph.",
        lifespan=lifespan,
    )
    app.include_router(router)
    register_exception_handlers(app)
    return app
