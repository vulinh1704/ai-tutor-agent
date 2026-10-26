"""Map domain and provider errors to HTTP responses."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from ai_tutor_agent.agent.grading import GradingError
from ai_tutor_agent.agent.service import SessionNotFoundError
from ai_tutor_agent.llm.base import LLMError, LLMRefusalError

logger = logging.getLogger(__name__)


def _error(status_code: int, detail: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": detail})


async def _session_not_found(_: Request, exc: Exception) -> JSONResponse:
    return _error(status.HTTP_404_NOT_FOUND, f"Session '{exc}' not found.")


async def _llm_refusal(_: Request, exc: Exception) -> JSONResponse:
    logger.info("Model refusal: %s", exc)
    return _error(
        status.HTTP_422_UNPROCESSABLE_CONTENT, "The model declined to respond to this request."
    )


async def _grading_failed(_: Request, exc: Exception) -> JSONResponse:
    logger.warning("Grading failed: %s", exc)
    return _error(status.HTTP_502_BAD_GATEWAY, "The model returned an invalid grading. Retry.")


async def _llm_failed(_: Request, exc: Exception) -> JSONResponse:
    logger.error("LLM provider error: %s", exc)
    return _error(status.HTTP_502_BAD_GATEWAY, "The language model provider failed. Retry.")


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(SessionNotFoundError, _session_not_found)
    app.add_exception_handler(LLMRefusalError, _llm_refusal)
    app.add_exception_handler(GradingError, _grading_failed)
    app.add_exception_handler(LLMError, _llm_failed)
