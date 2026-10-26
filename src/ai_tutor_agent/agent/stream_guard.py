"""Streaming without weakening the answer-leak guard.

A streamed reply reaches the student while the model is still writing it, but the leak guard
needs to see text before the student does. :class:`StreamGuard` sits between the two:

- each chunk is appended to the draft, and the draft is checked up to its last whitespace (a
  word that is still being written could change whether a pattern matches);
- released text stays ``holdback`` characters behind the checked text, so the opening words of
  a leaking phrase ("The answer is ...") are never shown;
- once ``leaked`` is set the draft is discarded: the tutor node tells the client to ``reset``
  and streams a regenerated draft (or the safe fallback hint) instead.

Because prefixes are only checked up to a whitespace boundary, a leak found in a prefix is
also a leak in the full draft (no false alarms from a half-written number), and
:meth:`StreamGuard.finish` runs the full check on the complete draft before releasing the
rest. The text a student finally sees is therefore exactly what the non-streaming path sends.
"""

from __future__ import annotations

from ai_tutor_agent.agent.hint_policy import HintPolicy


class StreamGuard:
    """Release a streamed draft to the student only after the leak guard has seen it."""

    def __init__(
        self, policy: HintPolicy, reference_answer: str | None, *, holdback: int | None = None
    ) -> None:
        self._policy = policy
        self._reference = reference_answer
        self.holdback = (
            holdback if holdback is not None else max(48, 2 * len(reference_answer or "") + 16)
        )
        self._draft = ""
        self._released = 0
        self.leaked = False

    @property
    def draft(self) -> str:
        """Everything received so far, released or not."""
        return self._draft

    def feed(self, chunk: str) -> str:
        """Add a chunk of the draft; return the text that is now safe to show (maybe empty)."""
        if self.leaked:
            return ""
        self._draft += chunk
        checked = _last_boundary(self._draft)
        if self._policy.leaks_answer(self._draft[:checked], self._reference):
            self.leaked = True
            return ""
        limit = checked - self.holdback
        if limit <= self._released:
            return ""
        return self._release(_last_boundary(self._draft[:limit]))

    def finish(self) -> str:
        """Check the complete draft and return whatever has not been released yet."""
        if self.leaked or self._policy.leaks_answer(self._draft, self._reference):
            self.leaked = True
            return ""
        return self._release(len(self._draft))

    def _release(self, end: int) -> str:
        if end <= self._released:
            return ""
        released = self._draft[self._released : end]
        self._released = end
        return released


def _last_boundary(value: str) -> int:
    """Index just past the last whitespace character (0 if there is none)."""
    index = len(value)
    while index > 0 and not value[index - 1].isspace():
        index -= 1
    return index
