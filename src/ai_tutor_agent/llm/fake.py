"""Deterministic, offline chat model for tests and the offline demo (``LLM_PROVIDER=fake``).

It works in two layers:

1. **Scripted** outputs queued by tests (``replies=[...]``, ``structured=[...]``) are returned
   first, in order. Queue an ``Exception`` instance to simulate a provider failure.
2. Otherwise **heuristics** derive a plausible answer from the prompt itself: keyword-based
   routing, a reply generator that follows the ``<hint_level>`` ladder and the ``<learner>``
   preferences (language, tone, scaffolding), and a keyword-coverage grader that reads the
   ``<rubric>`` and ``<student_answer>`` tags.

:meth:`FakeChatModel.stream` yields the same replies word by word, optionally with a small
delay so the offline web UI shows replies being typed.
"""

from __future__ import annotations

import asyncio
import json
import re
from collections import deque
from collections.abc import AsyncIterator, Iterable, Sequence
from dataclasses import dataclass
from typing import Final, Literal, TypeVar, cast, get_args

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from pydantic import BaseModel

from ai_tutor_agent.llm.base import LLMOutputError
from ai_tutor_agent.prompts import extract_tag
from ai_tutor_agent.schemas import (
    CriterionAssessment,
    GraderOutput,
    Language,
    RouteDecision,
    Scaffolding,
    Tone,
)

T = TypeVar("T", bound=BaseModel)


@dataclass(frozen=True)
class FakeCall:
    """A recorded call, so tests can assert on the prompts the agent sent."""

    kind: Literal["complete", "stream", "structured"]
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
        stream_delay: float = 0.0,
    ) -> None:
        self._replies: deque[str | Exception] = deque(replies)
        self._structured: deque[BaseModel | Exception] = deque(structured)
        self._model_name = model_name
        self.stream_delay = stream_delay
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
        return self._next_reply(messages)

    async def stream(self, messages: Sequence[BaseMessage]) -> AsyncIterator[str]:
        self.calls.append(FakeCall("stream", list(messages)))
        for chunk in split_into_chunks(self._next_reply(messages)):
            if self.stream_delay:
                await asyncio.sleep(self.stream_delay)
            yield chunk

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

    def _next_reply(self, messages: Sequence[BaseMessage]) -> str:
        if self._replies:
            reply = self._replies.popleft()
            if isinstance(reply, Exception):
                raise reply
            return reply
        return heuristic_tutor_reply(messages)


def split_into_chunks(text: str) -> list[str]:
    """Split text into word-sized chunks (each keeps its trailing whitespace)."""
    return re.findall(r"\s*\S+\s*", text) or [text]


# --------------------------------------------------------------------------- heuristics

_VAGUE = re.compile(
    r"^(help( me)?|hi|hello|hey|idk|i don'?t know|i'?m (so )?(stuck|lost|confused)|ok(ay)?|\?+"
    r"|(xin )?chào|giúp (em|mình|tôi)( với)?|(em |mình |tôi )?(không biết|bí quá|bí rồi)"
    r"|(em |mình |tôi )?không hiểu)"
    r"[.!?]*$",
    re.IGNORECASE,
)
_SUBMISSION = re.compile(
    r"\b(my (final )?answer|i got|here'?s my|is this (right|correct)|check my|did i get)\b"
    r"|(bài làm|đáp án|kết quả) của (em|mình|tôi)|(em|mình|tôi) (làm|tính|giải) (ra|được)"
    r"|kiểm tra (giúp|hộ)|đúng (chưa|không)",
    re.IGNORECASE,
)
_NEW_PROBLEM = re.compile(
    r"\b(new|next|another|different) (question|problem|exercise)\b"
    r"|\b(bài|câu) (khác|mới|tiếp theo)",
    re.IGNORECASE,
)
_MATH_SUBJECTS = (
    "math", "algebra", "arithmetic", "geometry", "calculus", "statistics",
    "toán", "đại số", "hình học", "giải tích", "số học", "thống kê",
)  # fmt: skip
# Words that describe *what to assess* in a rubric rather than content to look for.
_STOPWORDS = frozenset(
    {
        "about", "also", "answer", "answers", "clear", "clearly", "correct", "correctly",
        "describe", "describes", "does", "each", "explain", "explains", "final", "from",
        "have", "identify", "identifies", "into", "mention", "mentions", "name", "names",
        "result", "show", "shows", "solution", "state", "states", "step", "steps", "student",
        "that", "their", "them", "then", "this", "uses", "using", "value", "what", "when",
        "which", "with", "your",
        # Vietnamese
        "bài", "các", "của", "có", "cả", "để", "được", "đáp", "đúng", "giải", "kết", "làm",
        "là", "một", "những", "nêu", "nghiệm", "phần", "quả", "rồi", "số", "và", "với", "ở",
    }
)  # fmt: skip

_TUTOR_TEXT: Final[dict[Language, dict[str, str]]] = {
    "en": {
        "explain": (
            "Let's work through it step by step. First, list what you are given and what you "
            "are asked to find. Next, pick the {subject} rule that connects them. Then apply it "
            "one step at a time and check the result against the question. Which step would you "
            "like me to expand on?"
        ),
        "nudge": (
            "Before we dive in: what do you already know about this kind of {subject} problem? "
            "What exactly is it asking you to find?"
        ),
        "strategy": (
            "Let's pick a strategy. Which {subject} rule links what you are given to what you "
            "need? Try just the first step with it. What do you get?"
        ),
        "worked": (
            "Here's one step on a simpler example: to solve 2x + 3 = 11, undo the + 3 first by "
            "subtracting 3 from both sides, which gives 2x = 8. Now make the same first move in "
            "your own problem. What equation do you get?"
        ),
        "scaffold": (
            "Let's break it into smaller pieces: (1) what is given, (2) what is unknown, (3) the "
            "one {subject} idea that connects them. Fill in each blank for your problem. Which "
            "piece feels hardest?"
        ),
        "opener": "Good question!",
        "opener_named": "Good question, {name}!",
        "cheer_named": "You're doing well, {name}.",
        "more": "Tip: write each step on its own line so we can check it together.",
    },
    "vi": {
        "explain": (
            "Mình cùng làm từng bước nhé. Đầu tiên, hãy liệt kê những gì đề bài cho và những gì "
            "cần tìm. Tiếp theo, chọn quy tắc {subject} nối hai phần đó với nhau. Sau đó áp dụng "
            "từng bước một và đối chiếu kết quả với đề bài. Bạn muốn mình giải thích kỹ hơn bước "
            "nào?"
        ),
        "nudge": (
            "Trước khi bắt đầu: bạn đã biết gì về dạng bài {subject} này rồi? Đề bài đang yêu "
            "cầu mình tìm gì?"
        ),
        "strategy": (
            "Mình cùng chọn hướng giải nhé. Quy tắc {subject} nào nối những gì đề bài cho với "
            "điều cần tìm? Bạn thử làm bước đầu tiên với quy tắc đó xem. Bạn được kết quả gì?"
        ),
        "worked": (
            "Đây là một bước trên ví dụ đơn giản hơn: để giải 2x + 3 = 11, trước hết ta khử + 3 "
            "bằng cách trừ 3 ở cả hai vế, được 2x = 8. Giờ bạn làm bước đầu tiên tương tự với "
            "bài của mình nhé. Bạn được phương trình nào?"
        ),
        "scaffold": (
            "Mình chia bài thành từng phần nhỏ nhé: (1) đề bài cho gì, (2) cần tìm gì, (3) kiến "
            "thức {subject} nào nối hai phần đó. Bạn điền từng chỗ trống cho bài của mình. Phần "
            "nào khó nhất với bạn?"
        ),
        "opener": "Câu hỏi hay đấy!",
        "opener_named": "Câu hỏi hay đấy, {name}!",
        "cheer_named": "Bạn đang làm tốt lắm, {name}.",
        "more": "Mẹo nhỏ: viết mỗi bước trên một dòng để mình cùng kiểm tra nhé.",
    },
}

_GRADE_TEXT: Final[dict[tuple[Language, Tone], dict[str, str]]] = {
    ("en", "gentle"): {
        "full": "Well done: your answer covers this criterion.",
        "partial": "Partly there: you mention {hits}, but something is missing.",
        "none": "This part is missing from your answer.",
    },
    ("en", "direct"): {
        "full": "Covered.",
        "partial": "Partly covered ({hits}); something is missing.",
        "none": "Missing.",
    },
    ("vi", "gentle"): {
        "full": "Làm tốt lắm: bài làm của bạn đáp ứng tiêu chí này.",
        "partial": "Gần đúng rồi: bạn đã nhắc đến {hits}, nhưng vẫn còn thiếu một chút.",
        "none": "Bài làm của bạn chưa có phần này.",
    },
    ("vi", "direct"): {
        "full": "Đạt.",
        "partial": "Đạt một phần ({hits}); còn thiếu.",
        "none": "Chưa có.",
    },
}

_NEXT_STEP_TEXT: Final[dict[Language, dict[str, str]]] = {
    "en": {
        "done": "Great work! How could you check your answer in a different way?",
        "weakest": 'Look again at this part: "{criterion}". What could you add to cover it?',
    },
    "vi": {
        "done": "Tuyệt vời! Bạn có thể kiểm tra lại kết quả theo một cách khác không?",
        "weakest": 'Xem lại phần này nhé: "{criterion}". Bạn có thể bổ sung gì cho đủ ý?',
    },
}


@dataclass(frozen=True)
class _Style:
    language: Language = "en"
    tone: Tone = "gentle"
    scaffolding: Scaffolding = "standard"
    name: str | None = None


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
    style = _style(system)
    words = _TUTOR_TEXT[style.language]

    if _session_field(session, "mode") == "explain":
        return words["explain"].format(subject=subject)

    level = int(extract_tag(system, "hint_level") or 1)
    if level <= 1:
        body = words["nudge"]
    elif level == 2:
        body = words["strategy"]
    elif level == 3 and subject.lower().startswith(_MATH_SUBJECTS):
        body = words["worked"]
    else:
        body = words["scaffold"]

    parts = [body.format(subject=subject)]
    if style.tone == "gentle":
        if level <= 1:
            opener = words["opener_named" if style.name else "opener"]
            parts.insert(0, opener.format(name=style.name or ""))
        elif style.name:
            parts.insert(0, words["cheer_named"].format(name=style.name))
    if style.scaffolding == "more":
        parts.append(words["more"])
    return " ".join(parts)


def heuristic_grade(messages: Sequence[BaseMessage]) -> GraderOutput:
    prompt = "\n".join(m.text for m in messages)
    criteria = json.loads(extract_tag(prompt, "rubric") or "[]")
    answer_tokens = _tokens(extract_tag(prompt, "student_answer") or "")
    style = _style(prompt)
    feedback_text = _GRADE_TEXT[(style.language, style.tone)]

    assessments: list[CriterionAssessment] = []
    weakest: tuple[float, str] | None = None
    for criterion in criteria:
        keywords = sorted(_keywords(criterion["description"]))
        hits = [k for k in keywords if _mentioned(k, answer_tokens)]
        coverage = len(hits) / len(keywords) if keywords else 0.0
        points = round(criterion["max_points"] * coverage)
        if coverage == 1:
            feedback = feedback_text["full"]
        elif hits:
            feedback = feedback_text["partial"].format(hits=", ".join(hits))
        else:
            feedback = feedback_text["none"]
        assessments.append(
            CriterionAssessment(criterion_id=criterion["id"], points=points, feedback=feedback)
        )
        if coverage < 1 and (weakest is None or coverage < weakest[0]):
            weakest = (coverage, criterion["description"])

    next_step = _NEXT_STEP_TEXT[style.language]
    if weakest is None:
        hint = next_step["done"]
    else:
        hint = next_step["weakest"].format(criterion=weakest[1])
    return GraderOutput(assessments=assessments, next_step_hint=hint)


# --------------------------------------------------------------------------- helpers


def _system_text(messages: Sequence[BaseMessage]) -> str:
    return "\n".join(m.text for m in messages if isinstance(m, SystemMessage))


def _last_student_message(messages: Sequence[BaseMessage]) -> str:
    return next((m.text for m in reversed(messages) if isinstance(m, HumanMessage)), "")


def _session_field(block: str, name: str) -> str | None:
    match = re.search(rf"^{name}:\s*(.+)$", block, flags=re.MULTILINE)
    return match.group(1).strip() if match else None


def _style(prompt: str) -> _Style:
    """Read the learner's preferences from the ``<learner>`` block, if the prompt has one."""
    block = extract_tag(prompt, "learner")
    if block is None:
        return _Style()
    language = _session_field(block, "language")
    tone = _session_field(block, "tone")
    scaffolding = _session_field(block, "scaffolding")
    return _Style(
        language=cast(Language, language) if language in get_args(Language) else "en",
        tone=cast(Tone, tone) if tone in get_args(Tone) else "gentle",
        scaffolding=cast(Scaffolding, scaffolding)
        if scaffolding in get_args(Scaffolding)
        else "standard",
        name=_session_field(block, "name"),
    )


def _tokens(text: str) -> list[str]:
    return re.findall(r"[^\W\d_]+|\d+(?:\.\d+)?", text.lower())


def _keywords(text: str) -> set[str]:
    return {
        t
        for t in _tokens(text)
        if t not in _STOPWORDS
        and (t[0].isdigit() or len(t) >= 4 or (len(t) >= 2 and not t.isascii()))
    }


def _mentioned(keyword: str, answer_tokens: list[str]) -> bool:
    if keyword[0].isdigit():
        return keyword in answer_tokens
    stem = keyword[:5]
    return any(token.startswith(stem) for token in answer_tokens)
