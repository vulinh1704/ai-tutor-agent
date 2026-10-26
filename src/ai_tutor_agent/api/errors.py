"""Map domain and provider errors to HTTP responses (and to streamed ``error`` events)."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from ai_tutor_agent.agent.grading import GradingError
from ai_tutor_agent.agent.learners import LearnerNotFoundError
from ai_tutor_agent.agent.service import SessionNotFoundError
from ai_tutor_agent.llm.base import LLMError, LLMRefusalError

logger = logging.getLogger(__name__)


def describe_error(exc: Exception) -> tuple[int, str]:
    """HTTP status and client-safe detail for ``exc``. Unknown errors become a generic 500."""
    if isinstance(exc, SessionNotFoundError):
        return status.HTTP_404_NOT_FOUND, f"Session '{exc}' not found."
    if isinstance(exc, LearnerNotFoundError):
        return status.HTTP_404_NOT_FOUND, f"Learner '{exc}' not found."
    if isinstance(exc, LLMRefusalError):
        logger.info("Model refusal: %s", exc)
        return (
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "The model declined to respond to this request.",
        )
    if isinstance(exc, GradingError):
        logger.warning("Grading failed: %s", exc)
        return status.HTTP_502_BAD_GATEWAY, "The model returned an invalid grading. Retry."
    if isinstance(exc, LLMError):
        logger.error("LLM provider error: %s", exc)
        return status.HTTP_502_BAD_GATEWAY, "The language model provider failed. Retry."
    logger.exception("Unexpected error", exc_info=exc)
    return status.HTTP_500_INTERNAL_SERVER_ERROR, "Internal server error."


async def _handle(_: Request, exc: Exception) -> JSONResponse:
    status_code, detail = describe_error(exc)
    return JSONResponse(status_code=status_code, content={"detail": detail})


def register_exception_handlers(app: FastAPI) -> None:
    for error in (SessionNotFoundError, LearnerNotFoundError, LLMError, GradingError):
        app.add_exception_handler(error, _handle)
