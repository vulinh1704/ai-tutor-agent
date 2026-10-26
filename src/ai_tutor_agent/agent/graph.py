"""LangGraph wiring: ``START -> router -> (tutor | grader | clarify) -> END``."""

from __future__ import annotations

from typing import Any, TypeAlias

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from ai_tutor_agent.agent.hint_policy import HintPolicy
from ai_tutor_agent.agent.nodes import TutorNodes, select_route
from ai_tutor_agent.agent.state import TutorInput, TutorState
from ai_tutor_agent.llm.base import ChatModel

TutorGraph: TypeAlias = CompiledStateGraph[TutorState, None, TutorInput, TutorState]


def build_graph(
    llm: ChatModel,
    *,
    checkpointer: BaseCheckpointSaver[Any] | None = None,
    policy: HintPolicy | None = None,
    history_window: int = 20,
) -> TutorGraph:
    """Compile the tutoring graph. Pass a checkpointer to get per-session memory."""
    nodes = TutorNodes(llm, policy or HintPolicy(), history_window=history_window)

    builder = StateGraph(TutorState, input_schema=TutorInput)
    builder.add_node("router", nodes.router)
    builder.add_node("tutor", nodes.tutor)
    builder.add_node("grader", nodes.grader)
    builder.add_node("clarify", nodes.clarify)

    builder.add_edge(START, "router")
    builder.add_conditional_edges(
        "router", select_route, {"tutor": "tutor", "grader": "grader", "clarify": "clarify"}
    )
    for node in ("tutor", "grader", "clarify"):
        builder.add_edge(node, END)

    return builder.compile(checkpointer=checkpointer, name="ai-tutor")
