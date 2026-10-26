"""Hint policy: how much help the tutor gives, and a guard against leaking the answer.

In homework mode the tutor climbs a *hint ladder* one rung per consecutive tutoring turn on the
same problem (nudge -> strategy -> worked step on a similar example ...), capped at
``max_level``. A learner's scaffolding preference shifts the ladder: ``more`` starts one rung
higher, ``less`` stops one rung lower. Every draft reply is checked by
:meth:`HintPolicy.leaks_answer` before it is sent; the tutor node regenerates once and then
falls back to a safe canned hint.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ai_tutor_agent.i18n import text
from ai_tutor_agent.schemas import Language, Scaffolding

# "The answer is 5", "the correct solution is ...", "Final answer: 5", "final answer = 5",
# and the Vietnamese equivalents ("đáp án là 5", "đáp số: 5", "kết quả cuối cùng là ...").
# Questions such as "What do you think the answer is?" or "đáp án là gì?" do not match.
_GIVEAWAY = re.compile(
    r"\b(?:the\s+(?:final\s+|correct\s+|right\s+)?(?:answer|solution)\s+is"
    r"|final\s+answer\s*(?:is\b|[:=])"
    r"|(?:đáp\s+án|đáp\s+số|lời\s+giải)(?:\s+(?:cuối\s+cùng|đúng))?\s*(?:là\b|[:=])"
    r"|kết\s+quả\s+cuối\s+cùng\s*(?:là\b|[:=]))"
    # Single-word question openers only ("gì", "bao [nhiêu]", "như [thế nào]"): the streaming
    # guard checks text up to a word boundary, and must never see half of a multi-word phrase.
    r"\s*[:=]?\s*(?!(?:gì|bao|mấy|như|sao)\b)[\w$(-]",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class HintPolicy:
    max_level: int = 3

    def __post_init__(self) -> None:
        if not 1 <= self.max_level <= 5:
            raise ValueError("max_level must be between 1 and 5")

    def cap(self, scaffolding: Scaffolding = "standard") -> int:
        """Highest rung for a learner: one lower with ``less`` scaffolding (never below 1)."""
        return max(1, self.max_level - 1) if scaffolding == "less" else self.max_level

    def next_level(
        self,
        current_level: int,
        *,
        new_problem: bool = False,
        scaffolding: Scaffolding = "standard",
    ) -> int:
        """Escalate one rung per consecutive tutoring turn; restart on a new problem."""
        cap = self.cap(scaffolding)
        start = min(2 if scaffolding == "more" else 1, cap)
        if new_problem or current_level <= 0:
            return start
        return min(max(current_level + 1, start), cap)

    def leaks_answer(self, reply: str, reference_answer: str | None = None) -> bool:
        """Heuristically detect a reply that gives away the final answer."""
        if _GIVEAWAY.search(reply):
            return True
        return bool(reference_answer) and _contains_reference(reply, reference_answer or "")

    def fallback_reply(self, level: int, language: Language = "en") -> str:
        """A safe hint used when the model keeps leaking the answer."""
        prompt_key = f"fallback_{level}" if level in (1, 2) else "fallback_default"
        return text(language, "fallback", prompt=text(language, prompt_key))


def _compact(value: str) -> str:
    return re.sub(r"\s+", "", value.lower()).rstrip(".")


def _stated_as_result(reply: str, value: str) -> bool:
    """True if ``value`` appears as a result, e.g. "= 5", "is 5", "equals 5", "là 5"."""
    pattern = rf"(?:=|\bis\b|\bequals\b|\bget\b|\blà\b|\bbằng\b)\s*{re.escape(value)}(?!\w|\.\d)"
    return re.search(pattern, reply.lower()) is not None


def _contains_reference(reply: str, reference: str) -> bool:
    compact_ref = _compact(reference)
    if not compact_ref:
        return False
    if "=" in compact_ref:
        # An equation like "x = 5": flag "x=5" anywhere, or the value stated as a result.
        value = compact_ref.rsplit("=", 1)[1]
        return compact_ref in _compact(reply) or (bool(value) and _stated_as_result(reply, value))
    if len(compact_ref) >= 6:
        return compact_ref in _compact(reply)
    # Short answers such as "5" or "blue" are too common to match anywhere.
    return _stated_as_result(reply, reference.strip().lower().rstrip("."))
