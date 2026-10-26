"""AI tutoring agent starter: FastAPI + LangGraph with Socratic hints and rubric grading."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("ai-tutor-agent")
except PackageNotFoundError:  # pragma: no cover - only when running from a raw checkout
    __version__ = "0.0.0"

__all__ = ["__version__"]
