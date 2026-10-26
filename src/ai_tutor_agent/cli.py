"""Command line entry point: ``ai-tutor serve | demo | graph``."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from collections.abc import Sequence

from ai_tutor_agent import __version__


def _serve(host: str, port: int, reload: bool) -> int:
    import uvicorn

    from ai_tutor_agent.config import get_settings
    from ai_tutor_agent.llm.factory import ConfigurationError, build_chat_model

    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level.upper(), format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    try:
        build_chat_model(settings)  # validate configuration before starting the server
    except ConfigurationError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    uvicorn.run(
        "ai_tutor_agent.api.app:create_app",
        factory=True,
        host=host,
        port=port,
        reload=reload,
        log_level=settings.log_level.lower(),
    )
    return 0


def _graph() -> int:
    from ai_tutor_agent.agent.graph import build_graph
    from ai_tutor_agent.llm.fake import FakeChatModel

    print(build_graph(FakeChatModel()).get_graph().draw_mermaid())
    return 0


def _demo() -> int:
    from ai_tutor_agent.demo import run_demo

    asyncio.run(run_demo())
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ai-tutor", description="AI tutoring agent on FastAPI + LangGraph."
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    serve = commands.add_parser("serve", help="run the HTTP API with uvicorn")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--reload", action="store_true", help="auto-reload on code changes")

    commands.add_parser("demo", help="run a scripted offline session (no API key needed)")
    commands.add_parser("graph", help="print the agent graph as a Mermaid diagram")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "serve":
        return _serve(args.host, args.port, args.reload)
    if args.command == "graph":
        return _graph()
    return _demo()
