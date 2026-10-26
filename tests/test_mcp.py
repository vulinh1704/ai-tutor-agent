"""The MCP server, called in-process through the official SDK client (no subprocess, no port)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import pytest
from mcp import Client, MCPError
from mcp.types import CallToolResult, TextContent, TextResourceContents

from ai_tutor_agent.config import Settings
from ai_tutor_agent.llm.fake import FakeChatModel
from ai_tutor_agent.mcp_server import build_mcp_server

RUBRIC: dict[str, Any] = {
    "criteria": [
        {
            "id": "method",
            "description": "Subtracts 5 from both sides, then divides both sides by 3",
            "max_points": 3,
        },
        {"id": "answer", "description": "States the solution x = 5", "max_points": 2},
    ]
}


@asynccontextmanager
async def connect(settings: Settings) -> AsyncIterator[Client]:
    # A context manager rather than an async fixture: the client's task group must be entered
    # and exited in the same task.
    async with Client(build_mcp_server(settings, llm=FakeChatModel()), raise_exceptions=True) as c:
        yield c


async def _call(client: Client, tool: str, **arguments: Any) -> dict[str, Any]:
    result = await client.call_tool(tool, arguments)
    assert not result.is_error, result.content
    assert result.structured_content is not None
    return result.structured_content


def _error_text(result: CallToolResult) -> str:
    assert result.is_error
    content = result.content[0]
    assert isinstance(content, TextContent)
    return content.text


async def test_lists_the_tutor_tools(settings: Settings) -> None:
    async with connect(settings) as client:
        tools = {tool.name: tool for tool in (await client.list_tools()).tools}
        server_info = client.server_info
    assert set(tools) == {
        "create_learner",
        "start_session",
        "ask_tutor",
        "submit_answer",
        "grade_answer",
        "get_progress",
    }
    assert tools["grade_answer"].annotations is not None
    assert tools["grade_answer"].annotations.read_only_hint is True
    assert "ctx" not in tools["ask_tutor"].input_schema["properties"]
    assert server_info is not None
    assert server_info.name == "ai-tutor"


async def test_tutoring_flow_with_a_learner(settings: Settings) -> None:
    async with connect(settings) as client:
        learner = await _call(
            client,
            "create_learner",
            display_name="Linh",
            level="grade 8",
            tone="direct",
            scaffolding="more",
        )
        session = await _call(
            client,
            "start_session",
            subject="algebra",
            level="grade 8",
            question="Solve for x: 3x + 5 = 20",
            rubric=RUBRIC,
            reference_answer="x = 5",
            learner_id=learner["learner_id"],
        )
        session_id = session["session_id"]
        hint = await _call(client, "ask_tutor", session_id=session_id, message="How do I start?")
        graded = await _call(
            client,
            "submit_answer",
            session_id=session_id,
            answer="Subtract 5 from both sides, then divide both sides by 3, so x = 5",
        )
        progress = await _call(client, "get_progress", learner_id=learner["learner_id"])
        transcript = await client.read_resource(f"tutor://sessions/{session_id}/transcript")

    assert session["has_rubric"] is True
    assert session["learner_id"] == learner["learner_id"]
    assert (hint["route"], hint["hint_level"]) == ("tutor", 2)  # "more" scaffolding
    assert hint["reply"].startswith("Let's pick a strategy.")  # direct tone: no small talk
    assert graded["route"] == "grader"
    assert graded["grade"]["score"] == graded["grade"]["max_score"] == 5
    assert (progress["sessions"], progress["graded_attempts"]) == (1, 1)
    assert progress["average_score"] == 100.0
    text = transcript.contents[0]
    assert isinstance(text, TextResourceContents)
    assert text.text.startswith("# algebra (grade 8, homework mode)")
    assert "**Student:** How do I start?" in text.text
    assert "**Tutor:** Score: 5/5 (100%)" in text.text


async def test_stateless_grading(settings: Settings) -> None:
    async with connect(settings) as client:
        grade = await _call(
            client,
            "grade_answer",
            question="Solve for x: 3x + 5 = 20",
            answer="I subtracted 5 from both sides, so x = 5",
            rubric=RUBRIC,
        )
    assert [c["criterion_id"] for c in grade["criteria"]] == ["method", "answer"]
    assert grade["max_score"] == 5


async def test_open_session_without_a_question(settings: Settings) -> None:
    async with connect(settings) as client:
        session = await _call(client, "start_session", subject="history", level="grade 9")
        reply = await _call(client, "ask_tutor", session_id=session["session_id"], message="hi")
        transcript = await client.read_resource(
            f"tutor://sessions/{session['session_id']}/transcript"
        )
    assert (session["question"], session["has_rubric"]) == (None, False)
    assert reply["route"] == "clarify"
    text = transcript.contents[0]
    assert isinstance(text, TextResourceContents)
    assert "**Tutor:** I'd love to help with your history work!" in text.text


async def test_expected_failures_are_readable_tool_errors(settings: Settings) -> None:
    duplicate = {"criteria": [RUBRIC["criteria"][0], RUBRIC["criteria"][0]]}
    async with connect(settings) as client:
        unknown = await client.call_tool("ask_tutor", {"session_id": "nope", "message": "hi"})
        learner = await client.call_tool("get_progress", {"learner_id": "nope"})
        bad_rubric = await client.call_tool(
            "start_session",
            {"subject": "math", "level": "8", "question": "Solve it", "rubric": duplicate},
        )
        blank_name = await client.call_tool(
            "create_learner", {"display_name": " ", "level": "grade 8"}
        )
    assert _error_text(unknown) == "Error executing tool ask_tutor: Session 'nope' not found."
    assert _error_text(learner).endswith("Learner 'nope' not found.")
    assert "duplicate criterion ids" in _error_text(bad_rubric)
    assert "Invalid input" in _error_text(blank_name)


async def test_unknown_transcript_is_not_found(settings: Settings) -> None:
    async with connect(settings) as client:
        with pytest.raises(MCPError, match="Session 'nope' not found"):
            await client.read_resource("tutor://sessions/nope/transcript")
