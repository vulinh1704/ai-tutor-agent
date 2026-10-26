"""Command line entry point: ``ai-tutor serve | mcp | demo | graph``."""

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


def _mcp(transport: str, host: str, port: int) -> int:
    from ai_tutor_agent.config import get_settings
    from ai_tutor_agent.llm.factory import ConfigurationError

    settings = get_settings()
    # stdout carries the protocol over stdio: logs go to stderr (logging's default stream).
    logging.basicConfig(
        level=settings.log_level.upper(), format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    try:
        from ai_tutor_agent.mcp_server import build_mcp_server
    except ImportError as exc:
        print(
            f"MCP mode needs the 'mcp' extra ({exc.name} is missing): "
            "pip install 'ai-tutor-agent[mcp]' (or uv sync --extra mcp).",
            file=sys.stderr,
        )
        return 2
    try:
        server = build_mcp_server(settings)
    except ConfigurationError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    if transport == "stdio":
        server.run("stdio")
    else:
        server.run("streamable-http", host=host, port=port)
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

    mcp = commands.add_parser(
        "mcp", help="run the tutor as a Model Context Protocol server (needs the 'mcp' extra)"
    )
    mcp.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default="stdio",
        help="stdio for desktop hosts (default) or streamable-http at http://HOST:PORT/mcp",
    )
    mcp.add_argument("--host", default="127.0.0.1")
    mcp.add_argument("--port", type=int, default=8001)

    commands.add_parser("demo", help="run a scripted offline session (no API key needed)")
    commands.add_parser("graph", help="print the agent graph as a Mermaid diagram")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "serve":
        return _serve(args.host, args.port, args.reload)
    if args.command == "mcp":
        return _mcp(args.transport, args.host, args.port)
    if args.command == "graph":
        return _graph()
    return _demo()
