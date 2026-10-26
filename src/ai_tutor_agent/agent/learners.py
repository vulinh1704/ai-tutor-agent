"""Learner profiles and progress, kept in a LangGraph store (in memory or SQLite).

Sessions stay in the checkpointer; this module keeps what outlives a session, under one
namespace per learner:

- ``("learners",)``: the profile, keyed by learner id.
- ``("learners", id, "sessions")``: one summary per session (subject, turns, scores).
- ``("learners", id, "attempts")``: every graded attempt with per-criterion scores and skill
  tags, the raw material for skill mastery and spaced repetition later on.
- ``("learners", id, "activity")``: one record per local calendar day with activity, for
  streaks.
"""

from __future__ import annotations

import asyncio
import uuid
import weakref
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any, Final
from zoneinfo import ZoneInfo

from langgraph.store.base import BaseStore, Item
from pydantic import BaseModel, Field

from ai_tutor_agent.schemas import (
    CriterionScore,
    GradeResult,
    LearnerProfile,
    SessionProfile,
    TutorMode,
)

_LEARNERS: Final = ("learners",)
_PAGE: Final = 100


class LearnerNotFoundError(LookupError):
    """No learner exists with the given id."""


@dataclass(frozen=True)
class LearnerRecord:
    learner_id: str
    profile: LearnerProfile
    created_at: str
    updated_at: str


class SessionRecord(BaseModel):
    """A learner's session as listed in the sidebar and counted in their progress."""

    session_id: str
    subject: str
    mode: TutorMode
    title: str = Field(description="The assignment question, or the subject for open sessions.")
    created_at: str
    last_active_at: str | None = None
    turns: int = 0
    graded_attempts: int = 0
    best_percentage: float | None = None
    last_percentage: float | None = None


class AttemptRecord(BaseModel):
    attempt_id: str
    session_id: str
    subject: str
    skills: list[str]
    score: int
    max_score: int
    percentage: float
    criteria: list[CriterionScore]
    at: str


class SubjectProgress(BaseModel):
    subject: str
    sessions: int
    graded_attempts: int
    average_score: float | None


class ProgressSummary(BaseModel):
    sessions: int = Field(description="Sessions the learner has practised in (at least one turn).")
    graded_attempts: int
    average_score: float | None = Field(description="Mean percentage over graded attempts.")
    current_streak: int = Field(description="Consecutive days with practice, up to today.")
    best_streak: int
    active_today: bool
    last_active_on: str | None
    subjects: list[SubjectProgress]


def _now() -> datetime:
    return datetime.now(UTC)


class LearnerStore:
    """Profiles, session summaries, graded attempts and streaks on top of a LangGraph store."""

    def __init__(self, store: BaseStore, *, clock: Callable[[], datetime] = _now) -> None:
        self.store = store
        self._clock = clock
        self._locks: weakref.WeakValueDictionary[str, asyncio.Lock] = weakref.WeakValueDictionary()

    # ------------------------------------------------------------------ profiles

    async def create(self, profile: LearnerProfile) -> LearnerRecord:
        learner_id = uuid.uuid4().hex
        now = self._clock().isoformat()
        value = {"profile": profile.model_dump(mode="json"), "created_at": now, "updated_at": now}
        await self.store.aput(_LEARNERS, learner_id, value)
        return LearnerRecord(learner_id, profile, now, now)

    async def get(self, learner_id: str) -> LearnerRecord:
        item = await self.store.aget(_LEARNERS, learner_id) if learner_id else None
        if item is None:
            raise LearnerNotFoundError(learner_id)
        return LearnerRecord(
            learner_id=learner_id,
            profile=LearnerProfile.model_validate(item.value["profile"]),
            created_at=item.value["created_at"],
            updated_at=item.value["updated_at"],
        )

    async def update(self, learner_id: str, profile: LearnerProfile) -> LearnerRecord:
        async with self._lock(learner_id):
            current = await self.get(learner_id)
            now = self._clock().isoformat()
            value = {
                "profile": profile.model_dump(mode="json"),
                "created_at": current.created_at,
                "updated_at": now,
            }
            await self.store.aput(_LEARNERS, learner_id, value)
        return LearnerRecord(learner_id, profile, current.created_at, now)

    # ------------------------------------------------------------------ sessions and turns

    async def add_session(
        self, learner_id: str, session_id: str, profile: SessionProfile, created_at: str
    ) -> SessionRecord:
        title = profile.assignment.question if profile.assignment else profile.subject
        record = SessionRecord(
            session_id=session_id,
            subject=profile.subject,
            mode=profile.mode,
            title=title[:200],
            created_at=created_at,
        )
        await self.store.aput(_ns(learner_id, "sessions"), session_id, record.model_dump())
        return record

    async def record_turn(
        self,
        learner_id: str,
        session_id: str,
        *,
        subject: str,
        skills: list[str],
        grade: GradeResult | None,
    ) -> None:
        """Count a chat turn (and its grade, if any) towards the learner's progress."""
        async with self._lock(learner_id):
            learner = await self.get(learner_id)
            now = self._clock()
            sessions_ns = _ns(learner_id, "sessions")
            item = await self.store.aget(sessions_ns, session_id)
            if item is not None:
                record = SessionRecord.model_validate(item.value)
                record.turns += 1
                record.last_active_at = now.isoformat()
                if grade is not None:
                    record.graded_attempts += 1
                    record.last_percentage = grade.percentage
                    record.best_percentage = max(record.best_percentage or 0.0, grade.percentage)
                await self.store.aput(sessions_ns, session_id, record.model_dump())

            if grade is not None:
                attempt = AttemptRecord(
                    attempt_id=uuid.uuid4().hex,
                    session_id=session_id,
                    subject=subject,
                    skills=skills,
                    score=grade.score,
                    max_score=grade.max_score,
                    percentage=grade.percentage,
                    criteria=grade.criteria,
                    at=now.isoformat(),
                )
                await self.store.aput(
                    _ns(learner_id, "attempts"), attempt.attempt_id, attempt.model_dump(mode="json")
                )

            day = now.astimezone(ZoneInfo(learner.profile.timezone)).date().isoformat()
            activity_ns = _ns(learner_id, "activity")
            current = await self.store.aget(activity_ns, day)
            turns = (current.value.get("turns", 0) if current else 0) + 1
            await self.store.aput(activity_ns, day, {"turns": turns})

    async def list_sessions(self, learner_id: str) -> list[SessionRecord]:
        """The learner's sessions, most recently active first."""
        await self.get(learner_id)
        records = [
            SessionRecord.model_validate(item.value)
            for item in await self._all(_ns(learner_id, "sessions"))
        ]
        return sorted(records, key=lambda r: r.last_active_at or r.created_at, reverse=True)

    async def list_attempts(self, learner_id: str) -> list[AttemptRecord]:
        """Every graded attempt, oldest first."""
        await self.get(learner_id)
        attempts = [
            AttemptRecord.model_validate(item.value)
            for item in await self._all(_ns(learner_id, "attempts"))
        ]
        return sorted(attempts, key=lambda a: a.at)

    # ------------------------------------------------------------------ progress

    async def progress(self, learner_id: str) -> ProgressSummary:
        learner = await self.get(learner_id)
        sessions = [s for s in await self.list_sessions(learner_id) if s.turns > 0]
        attempts = await self.list_attempts(learner_id)
        days = {
            date.fromisoformat(item.key) for item in await self._all(_ns(learner_id, "activity"))
        }
        today = self._clock().astimezone(ZoneInfo(learner.profile.timezone)).date()

        by_subject: dict[str, list[AttemptRecord]] = defaultdict(list)
        for attempt in attempts:
            by_subject[attempt.subject].append(attempt)
        session_counts: dict[str, int] = defaultdict(int)
        for session in sessions:
            session_counts[session.subject] += 1
        subjects = [
            SubjectProgress(
                subject=subject,
                sessions=session_counts.get(subject, 0),
                graded_attempts=len(by_subject[subject]),
                average_score=_mean(a.percentage for a in by_subject[subject]),
            )
            for subject in sorted(set(session_counts) | set(by_subject))
        ]
        return ProgressSummary(
            sessions=len(sessions),
            graded_attempts=len(attempts),
            average_score=_mean(a.percentage for a in attempts),
            current_streak=current_streak(days, today),
            best_streak=best_streak(days),
            active_today=today in days,
            last_active_on=max(days).isoformat() if days else None,
            subjects=subjects,
        )

    # ------------------------------------------------------------------ helpers

    def _lock(self, learner_id: str) -> asyncio.Lock:
        lock = self._locks.get(learner_id)
        if lock is None:
            lock = self._locks[learner_id] = asyncio.Lock()
        return lock

    async def _all(self, namespace: tuple[str, ...]) -> list[Item]:
        items: list[Item] = []
        while True:
            page = await self.store.asearch(namespace, limit=_PAGE, offset=len(items))
            items.extend(page)
            if len(page) < _PAGE:
                return items


def _ns(learner_id: str, collection: str) -> tuple[str, ...]:
    return (*_LEARNERS, learner_id, collection)


def _mean(values: Any) -> float | None:
    numbers = list(values)
    return round(sum(numbers) / len(numbers), 1) if numbers else None


def current_streak(days: set[date], today: date) -> int:
    """Consecutive active days ending today, or yesterday if today has no activity yet."""
    day = today if today in days else today - timedelta(days=1)
    streak = 0
    while day in days:
        streak += 1
        day -= timedelta(days=1)
    return streak


def best_streak(days: set[date]) -> int:
    best = run = 0
    previous: date | None = None
    for day in sorted(days):
        run = run + 1 if previous is not None and day - previous == timedelta(days=1) else 1
        best = max(best, run)
        previous = day
    return best
