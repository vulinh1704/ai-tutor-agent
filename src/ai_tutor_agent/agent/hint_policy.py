"""Hint policy: how much help the tutor gives, and a guard against leaking the answer.

In homework mode the tutor climbs a *hint ladder* one rung per consecutive tutoring turn on the
same problem (nudge -> strategy -> worked step on a similar example ...), capped at
``max_level``. Every draft reply is checked by :meth:`HintPolicy.leaks_answer` before it is
sent; the tutor node regenerates once and then falls back to a safe canned hint.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# "The answer is 5", "the correct solution is ...", "Final answer: 5", "final answer = 5".
# Questions such as "What do you think the answer is?" do not match.
_GIVEAWAY = re.compile(
    r"\b(?:the\s+(?:final\s+|correct\s+|right\s+)?(?:answer|solution)\s+is"
    r"|final\s+answer\s*(?:is\b|[:=]))"
    r"\s*[:=]?\s*[\w$(-]",
    re.IGNORECASE,
)

_FALLBACK_PROMPTS = {
    1: "What is the problem asking you to find, in your own words?",
    2: "Which rule or method do you think applies here? Try the first step and tell me what "
    "you get.",
}
_FALLBACK_DEFAULT = "Try the next step on your own and tell me what you get. I'll check your work."


@dataclass(frozen=True)
class HintPolicy:
    max_level: int = 3

    def __post_init__(self) -> None:
        if not 1 <= self.max_level <= 5:
            raise ValueError("max_level must be between 1 and 5")

    def next_level(self, current_level: int, *, new_problem: bool = False) -> int:
        """Escalate one rung per consecutive tutoring turn; restart on a new problem."""
        if new_problem:
            return 1
        return min(max(current_level, 0) + 1, self.max_level)

    def leaks_answer(self, reply: str, reference_answer: str | None = None) -> bool:
        """Heuristically detect a reply that gives away the final answer."""
        if _GIVEAWAY.search(reply):
            return True
        return bool(reference_answer) and _contains_reference(reply, reference_answer or "")

    def fallback_reply(self, level: int) -> str:
        """A safe hint used when the model keeps leaking the answer."""
        prompt = _FALLBACK_PROMPTS.get(level, _FALLBACK_DEFAULT)
        return (
            "I can't hand you the final answer in homework mode, but you're closer than you "
            f"think. {prompt}"
        )


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text.lower()).rstrip(".")


def _stated_as_result(reply: str, value: str) -> bool:
    """True if ``value`` appears as a result, e.g. "= 5", "is 5", "equals 5", "get 5"."""
    pattern = rf"(?:=|\bis\b|\bequals\b|\bget\b)\s*{re.escape(value)}(?!\w|\.\d)"
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
