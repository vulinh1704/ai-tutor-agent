"""Deterministic, offline chat model for tests and the offline demo (``LLM_PROVIDER=fake``).

It works in two layers:

1. **Scripted** outputs queued by tests (``replies=[...]``, ``structured=[...]``) are returned
   first, in order. Queue an ``Exception`` instance to simulate a provider failure.
2. Otherwise **heuristics** derive a plausible answer from the prompt itself: keyword-based
   routing, a reply generator that follows the ``<hint_level>`` ladder, and a keyword-coverage
   grader that reads the ``<rubric>`` and ``<student_answer>`` tags.
"""

from __future__ import annotations

import json
import re
from collections import deque
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Literal, TypeVar, cast

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from pydantic import BaseModel

from ai_tutor_agent.llm.base import LLMOutputError
from ai_tutor_agent.prompts import extract_tag
from ai_tutor_agent.schemas import CriterionAssessment, GraderOutput, RouteDecision

T = TypeVar("T", bound=BaseModel)


@dataclass(frozen=True)
class FakeCall:
    """A recorded call, so tests can assert on the prompts the agent sent."""

    kind: Literal["complete", "structured"]
    messages: list[BaseMessage]
    schema: type[BaseModel] | None = None

    @property
    def system_prompt(self) -> str:
        return _system_text(self.messages)


class FakeChatModel:
    """A :class:`~ai_tutor_agent.llm.base.ChatModel` that never touches the network."""

    def __init__(
        self,
        *,
        replies: Iterable[str | Exception] = (),
        structured: Iterable[BaseModel | Exception] = (),
        model_name: str = "fake-tutor",
    ) -> None:
        self._replies: deque[str | Exception] = deque(replies)
        self._structured: deque[BaseModel | Exception] = deque(structured)
        self._model_name = model_name
        self.calls: list[FakeCall] = []

    @property
    def provider(self) -> str:
        return "fake"

    @property
    def model_name(self) -> str:
        return self._model_name

    def queue_reply(self, *replies: str | Exception) -> None:
        self._replies.extend(replies)

    def queue_structured(self, *outputs: BaseModel | Exception) -> None:
        self._structured.extend(outputs)

    async def complete(self, messages: Sequence[BaseMessage]) -> str:
        self.calls.append(FakeCall("complete", list(messages)))
        if self._replies:
            reply = self._replies.popleft()
            if isinstance(reply, Exception):
                raise reply
            return reply
        return heuristic_tutor_reply(messages)

    async def structured(self, messages: Sequence[BaseMessage], schema: type[T]) -> T:
        self.calls.append(FakeCall("structured", list(messages), schema))
        if self._structured:
            head = self._structured[0]
            if isinstance(head, Exception):
                self._structured.popleft()
                raise head
            if isinstance(head, schema):
                self._structured.popleft()
                return head
        if issubclass(schema, RouteDecision):
            return cast(T, heuristic_route(messages))
        if issubclass(schema, GraderOutput):
            return cast(T, heuristic_grade(messages))
        raise LLMOutputError(f"FakeChatModel has no heuristic for {schema.__name__}")


# --------------------------------------------------------------------------- heuristics

_VAGUE = re.compile(
    r"^(help( me)?|hi|hello|hey|idk|i don'?t know|i'?m (so )?(stuck|lost|confused)|ok(ay)?|\?+)"
    r"[.!?]*$",
    re.IGNORECASE,
)
_SUBMISSION = re.compile(
    r"\b(my (final )?answer|i got|here'?s my|is this (right|correct)|check my|did i get)\b",
    re.IGNORECASE,
)
_NEW_PROBLEM = re.compile(r"\b(new|next|another|different) (question|problem|exercise)\b", re.I)
_MATH_SUBJECTS = ("math", "algebra", "arithmetic", "geometry", "calculus", "statistics")
# Words that describe *what to assess* in a rubric rather than content to look for.
_STOPWORDS = frozenset(
    {
        "about", "also", "answer", "answers", "clear", "clearly", "correct", "correctly",
        "describe", "describes", "does", "each", "explain", "explains", "final", "from",
        "have", "identify", "identifies", "into", "mention", "mentions", "name", "names",
        "result", "show", "shows", "solution", "state", "states", "step", "steps", "student",
        "that", "their", "them", "then", "this", "uses", "using", "value", "what", "when",
        "which", "with", "your",
    }
)  # fmt: skip


def heuristic_route(messages: Sequence[BaseMessage]) -> RouteDecision:
    text = _last_student_message(messages).strip()
    new_problem = bool(_NEW_PROBLEM.search(text))
    if not text or _VAGUE.match(text):
        return RouteDecision(
            route="clarify", new_problem=False, reason="The message is too vague to act on."
        )
    if _SUBMISSION.search(text):
        return RouteDecision(
            route="grader", new_problem=new_problem, reason="The student submitted an answer."
        )
    return RouteDecision(
        route="tutor", new_problem=new_problem, reason="The student is asking for help."
    )


def heuristic_tutor_reply(messages: Sequence[BaseMessage]) -> str:
    system = _system_text(messages)
    session = extract_tag(system, "session") or ""
    subject = _session_field(session, "subject") or "this topic"

    if _session_field(session, "mode") == "explain":
        return (
            "Let's work through it step by step. First, list what you are given and what you "
            f"are asked to find. Next, pick the {subject} rule that connects them. Then apply it "
            "one step at a time and check the result against the question. Which step would you "
            "like me to expand on?"
        )

    level = int(extract_tag(system, "hint_level") or 1)
    if level <= 1:
        return (
            f"Good question! Before we dive in: what do you already know about this kind of "
            f"{subject} problem? What exactly is it asking you to find?"
        )
    if level == 2:
        return (
            f"Let's pick a strategy. Which {subject} rule links what you are given to what you "
            "need? Try just the first step with it. What do you get?"
        )
    if level == 3 and subject.lower().startswith(_MATH_SUBJECTS):
        return (
            "Here's one step on a simpler example: to solve 2x + 3 = 11, undo the + 3 first by "
            "subtracting 3 from both sides, which gives 2x = 8. Now make the same first move in "
            "your own problem. What equation do you get?"
        )
    return (
        "Let's break it into smaller pieces: (1) what is given, (2) what is unknown, (3) the "
        f"one {subject} idea that connects them. Fill in each blank for your problem. Which "
        "piece feels hardest?"
    )


def heuristic_grade(messages: Sequence[BaseMessage]) -> GraderOutput:
    prompt = "\n".join(m.text for m in messages)
    criteria = json.loads(extract_tag(prompt, "rubric") or "[]")
    answer_tokens = _tokens(extract_tag(prompt, "student_answer") or "")

    assessments: list[CriterionAssessment] = []
    weakest: tuple[float, str] | None = None
    for criterion in criteria:
        keywords = sorted(_keywords(criterion["description"]))
        hits = [k for k in keywords if _mentioned(k, answer_tokens)]
        coverage = len(hits) / len(keywords) if keywords else 0.0
        points = round(criterion["max_points"] * coverage)
        if coverage == 1:
            feedback = "Well done: your answer covers this criterion."
        elif hits:
            feedback = f"Partly there: you mention {', '.join(hits)}, but something is missing."
        else:
            feedback = "This part is missing from your answer."
        assessments.append(
            CriterionAssessment(criterion_id=criterion["id"], points=points, feedback=feedback)
        )
        if coverage < 1 and (weakest is None or coverage < weakest[0]):
            weakest = (coverage, criterion["description"])

    if weakest is None:
        hint = "Great work! How could you check your answer in a different way?"
    else:
        hint = f'Look again at this part: "{weakest[1]}". What could you add to cover it?'
    return GraderOutput(assessments=assessments, next_step_hint=hint)


# --------------------------------------------------------------------------- helpers


def _system_text(messages: Sequence[BaseMessage]) -> str:
    return "\n".join(m.text for m in messages if isinstance(m, SystemMessage))


def _last_student_message(messages: Sequence[BaseMessage]) -> str:
    return next((m.text for m in reversed(messages) if isinstance(m, HumanMessage)), "")


def _session_field(session: str, name: str) -> str | None:
    match = re.search(rf"^{name}:\s*(.+)$", session, flags=re.MULTILINE)
    return match.group(1).strip() if match else None


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z]+|\d+(?:\.\d+)?", text.lower())


def _keywords(text: str) -> set[str]:
    return {t for t in _tokens(text) if t[0].isdigit() or (len(t) >= 4 and t not in _STOPWORDS)}


def _mentioned(keyword: str, answer_tokens: list[str]) -> bool:
    if keyword[0].isdigit():
        return keyword in answer_tokens
    stem = keyword[:5]
    return any(token.startswith(stem) for token in answer_tokens)
