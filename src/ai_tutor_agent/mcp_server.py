"""Model Context Protocol server: the tutor as tools for Claude Desktop, Claude Code, Cursor ...

``ai-tutor mcp`` serves it over stdio, which is what desktop hosts launch;
``ai-tutor mcp --transport streamable-http`` serves it at ``http://HOST:PORT/mcp`` instead.
Requires the ``mcp`` extra (``pip install 'ai-tutor-agent[mcp]'``).

The tools share the HTTP API's :class:`~ai_tutor_agent.agent.service.TutorService`, so the
hint ladder, the answer-leak guard, rubric validation and learner profiles behave the same.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass
from typing import Annotated

from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from mcp.server.mcpserver.exceptions import ResourceNotFoundError, ToolError
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field, ValidationError

from ai_tutor_agent import __version__
from ai_tutor_agent.agent.grading import GradingError
from ai_tutor_agent.agent.learners import LearnerNotFoundError, ProgressSummary
from ai_tutor_agent.agent.service import (
    SessionNotFoundError,
    SessionSnapshot,
    TurnResult,
    TutorService,
    open_service,
)
from ai_tutor_agent.api.errors import describe_error
from ai_tutor_agent.config import Settings, get_settings
from ai_tutor_agent.llm.base import ChatModel, LLMError
from ai_tutor_agent.llm.factory import build_chat_model
from ai_tutor_agent.schemas import (
    Assignment,
    GradeResult,
    Language,
    LearnerProfile,
    Rubric,
    Scaffolding,
    SessionProfile,
    Tone,
    TutorMode,
    TutorPreferences,
)

INSTRUCTIONS = """\
AI Tutor Agent is a Socratic tutor with rubric-based grading and learner profiles.
Typical flow: create_learner (once, optional) -> start_session -> ask_tutor for each student \
message -> submit_answer when the student wants an attempt graded. get_progress summarises a \
learner's practice.
In homework mode the tutor deliberately answers with hints, not solutions. Relay its replies to \
the student as they are and do not solve the problem yourself."""


@dataclass
class TutorContext:
    service: TutorService


TutorCtx = Context[TutorContext]


class LearnerInfo(BaseModel):
    learner_id: str
    display_name: str
    level: str
    preferences: TutorPreferences


class SessionInfo(BaseModel):
    session_id: str
    subject: str
    level: str
    mode: TutorMode
    question: str | None
    has_rubric: bool
    max_hint_level: int
    learner_id: str | None

    @classmethod
    def from_snapshot(cls, snapshot: SessionSnapshot) -> SessionInfo:
        profile = snapshot.profile
        return cls(
            session_id=snapshot.session_id,
            subject=profile.subject,
            level=profile.level,
            mode=profile.mode,
            question=profile.assignment.question if profile.assignment else None,
            has_rubric=profile.rubric is not None,
            max_hint_level=snapshot.max_hint_level,
            learner_id=profile.learner_id,
        )


class TutorReply(BaseModel):
    session_id: str
    route: str = Field(description="tutor (a hint), grader (a graded attempt) or clarify.")
    reply: str = Field(description="What to show the student.")
    hint_level: int
    grade: GradeResult | None = None

    @classmethod
    def from_turn(cls, turn: TurnResult) -> TutorReply:
        return cls(
            session_id=turn.session_id,
            route=turn.route,
            reply=turn.reply,
            hint_level=turn.hint_level,
            grade=turn.grade,
        )


@contextmanager
def _tool_errors() -> Iterator[None]:
    """Turn expected failures into tool errors the calling model can read and act on."""
    try:
        yield
    except (SessionNotFoundError, LearnerNotFoundError, LLMError, GradingError) as exc:
        raise ToolError(describe_error(exc)[1]) from exc
    except ValidationError as exc:
        raise ToolError(f"Invalid input: {exc.errors(include_url=False)}") from exc


def render_transcript(snapshot: SessionSnapshot) -> str:
    """A session as Markdown: header, assignment and the conversation."""
    profile = snapshot.profile
    lines = [f"# {profile.subject} ({profile.level}, {profile.mode} mode)", ""]
    if profile.assignment:
        lines += [f"**Assignment:** {profile.assignment.question}", ""]
    for message in snapshot.messages:
        speaker = "Student" if message.type == "human" else "Tutor"
        lines += [f"**{speaker}:** {message.text}", ""]
    if not snapshot.messages:
        lines.append("_No messages yet._")
    return "\n".join(lines).rstrip() + "\n"


def build_mcp_server(
    settings: Settings | None = None, *, llm: ChatModel | None = None
) -> MCPServer[TutorContext]:
    """Build the MCP server. ``llm`` overrides the configured provider (handy in tests)."""
    settings = settings or get_settings()
    chat_model = llm or build_chat_model(settings)  # fail fast on bad configuration

    @asynccontextmanager
    async def lifespan(_: MCPServer[TutorContext]) -> AsyncIterator[TutorContext]:
        async with open_service(settings, chat_model) as service:
            yield TutorContext(service)

    server: MCPServer[TutorContext] = MCPServer(
        "ai-tutor",
        title="AI Tutor Agent",
        instructions=INSTRUCTIONS,
        website_url="https://github.com/vulinh1704/ai-tutor-agent",
        version=__version__,
        lifespan=lifespan,
    )
    writes = ToolAnnotations(
        read_only_hint=False, destructive_hint=False, idempotent_hint=False, open_world_hint=False
    )
    reads = ToolAnnotations(read_only_hint=True, open_world_hint=False)

    def service_of(ctx: TutorCtx) -> TutorService:
        return ctx.request_context.lifespan_context.service

    @server.tool(title="Create a learner profile", annotations=writes)
    async def create_learner(
        ctx: TutorCtx,
        display_name: Annotated[str, Field(description="What the tutor calls the student.")],
        level: Annotated[str, Field(description='School level, e.g. "grade 8".')],
        language: Annotated[Language, Field(description="Reply language.")] = "en",
        tone: Annotated[Tone, Field(description="gentle or direct.")] = "gentle",
        scaffolding: Annotated[
            Scaffolding, Field(description="How much step-by-step support hints give.")
        ] = "standard",
        goal: Annotated[str | None, Field(description="The student's learning goal.")] = None,
        subjects: list[str] | None = None,
    ) -> LearnerInfo:
        """Create a learner profile so sessions adapt to the student and progress is tracked."""
        with _tool_errors():
            profile = LearnerProfile(
                display_name=display_name,
                level=level,
                subjects=subjects or [],
                goal=goal,
                preferences=TutorPreferences(language=language, tone=tone, scaffolding=scaffolding),
            )
            record = await service_of(ctx).learners.create(profile)
        return LearnerInfo(
            learner_id=record.learner_id,
            display_name=profile.display_name,
            level=profile.level,
            preferences=profile.preferences,
        )

    @server.tool(title="Start a tutoring session", annotations=writes)
    async def start_session(
        ctx: TutorCtx,
        subject: Annotated[str, Field(description='e.g. "algebra", "physics".')],
        level: Annotated[str, Field(description='e.g. "grade 8".')],
        question: Annotated[
            str | None, Field(description="The problem the student is working on.")
        ] = None,
        rubric: Annotated[
            Rubric | None, Field(description="Criteria for grading attempts at the question.")
        ] = None,
        reference_answer: Annotated[
            str | None,
            Field(description="Hidden from the student; used for grading and leak checks."),
        ] = None,
        mode: Annotated[
            TutorMode, Field(description="homework: hints only; explain: full walkthroughs.")
        ] = "homework",
        learner_id: Annotated[
            str | None, Field(description="Personalise with this learner's profile.")
        ] = None,
    ) -> SessionInfo:
        """Start a tutoring session, optionally about a specific question with a rubric."""
        with _tool_errors():
            assignment = (
                Assignment(question=question, rubric=rubric, reference_answer=reference_answer)
                if question
                else None
            )
            profile = SessionProfile(
                subject=subject,
                level=level,
                mode=mode,
                assignment=assignment,
                learner_id=learner_id,
            )
            snapshot = await service_of(ctx).create_session(profile)
        return SessionInfo.from_snapshot(snapshot)

    @server.tool(title="Ask the tutor", annotations=writes)
    async def ask_tutor(
        ctx: TutorCtx,
        session_id: str,
        message: Annotated[str, Field(min_length=1, max_length=4000)],
    ) -> TutorReply:
        """Send the student's message; the tutor answers with a hint at the next ladder level."""
        with _tool_errors():
            turn = await service_of(ctx).send_message(session_id, message)
        return TutorReply.from_turn(turn)

    @server.tool(title="Submit an answer for grading", annotations=writes)
    async def submit_answer(
        ctx: TutorCtx,
        session_id: str,
        answer: Annotated[str, Field(min_length=1, max_length=4000)],
    ) -> TutorReply:
        """Grade the student's attempt against the session rubric (per-criterion scores)."""
        with _tool_errors():
            turn = await service_of(ctx).send_message(session_id, answer, intent="submit")
        return TutorReply.from_turn(turn)

    @server.tool(title="Grade an answer against a rubric", annotations=reads)
    async def grade_answer(
        ctx: TutorCtx,
        question: Annotated[str, Field(min_length=3, max_length=4000)],
        answer: Annotated[str, Field(min_length=1, max_length=8000)],
        rubric: Rubric,
        subject: str = "general studies",
        level: str = "general",
        reference_answer: str | None = None,
    ) -> GradeResult:
        """Grade a short answer against a rubric without a session. Totals are computed in code."""
        with _tool_errors():
            return await service_of(ctx).grade(
                question=question,
                answer=answer,
                rubric=rubric,
                subject=subject,
                level=level,
                reference_answer=reference_answer,
            )

    @server.tool(title="Learner progress", annotations=reads)
    async def get_progress(ctx: TutorCtx, learner_id: str) -> ProgressSummary:
        """Sessions practised, average rubric score and practice streaks for a learner."""
        with _tool_errors():
            return await service_of(ctx).learners.progress(learner_id)

    @server.resource(
        "tutor://sessions/{session_id}/transcript",
        title="Session transcript",
        mime_type="text/markdown",
    )
    async def session_transcript(session_id: str, ctx: TutorCtx) -> str:
        """The conversation of a tutoring session, as Markdown."""
        try:
            snapshot = await service_of(ctx).get_session(session_id)
        except SessionNotFoundError as exc:
            raise ResourceNotFoundError(f"Session '{session_id}' not found.") from exc
        return render_transcript(snapshot)

    return server
