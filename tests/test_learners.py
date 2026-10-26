"""Learner profiles, session summaries, progress and streaks (store and HTTP API)."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from langgraph.store.memory import InMemoryStore
from pydantic import ValidationError

from ai_tutor_agent.agent.checkpointer import open_store
from ai_tutor_agent.agent.learners import (
    LearnerNotFoundError,
    LearnerStore,
    best_streak,
    current_streak,
)
from ai_tutor_agent.config import Settings
from ai_tutor_agent.schemas import (
    CriterionScore,
    GradeResult,
    LearnerProfile,
    SessionProfile,
    TutorPreferences,
)

LEARNER: dict[str, Any] = {
    "display_name": "  Linh ",
    "level": "grade 8",
    "subjects": ["math", "physics"],
    "goal": "Feel confident with equations",
    "preferences": {"language": "vi", "tone": "gentle", "scaffolding": "more"},
    "appearance": {"avatar": "owl", "accent": "teal", "font_scale": "large"},
    "timezone": "Asia/Ho_Chi_Minh",
}


class Clock:
    def __init__(self, start: datetime) -> None:
        self.now = start

    def __call__(self) -> datetime:
        return self.now


def _grade(percentage_points: int) -> GradeResult:
    return GradeResult(
        score=percentage_points,
        max_score=10,
        percentage=percentage_points * 10,
        criteria=[
            CriterionScore(criterion_id="a", points=percentage_points, max_points=10, feedback="")
        ],
        next_step_hint="?",
    )


# --------------------------------------------------------------------------- schema


def test_profile_defaults_and_cleanup() -> None:
    profile = LearnerProfile(display_name="  Linh ", level="grade 8")
    assert profile.display_name == "Linh"
    assert profile.preferences == TutorPreferences(
        language="en", tone="gentle", scaffolding="standard"
    )
    assert profile.timezone == "UTC"


@pytest.mark.parametrize(
    "changes",
    [
        {"timezone": "Mars/Olympus"},
        {"display_name": " "},
        {"preferences": {"language": "fr"}},
        {"appearance": {"accent": "Not A Slug"}},
        {"subjects": ["math"] * 9},
    ],
)
def test_profile_validation(changes: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        LearnerProfile.model_validate({**LEARNER, **changes})


# --------------------------------------------------------------------------- streaks


@pytest.mark.parametrize(
    ("offsets", "current", "best"),
    [
        ([], 0, 0),
        ([0], 1, 1),
        ([0, 1, 2], 3, 3),
        ([1, 2], 2, 2),  # today not practised yet: the streak is still alive
        ([2, 3, 4, 5], 0, 4),
        ([0, 2, 3, 4], 1, 3),
    ],
)
def test_streaks(offsets: list[int], current: int, best: int) -> None:
    today = date(2026, 10, 26)
    days = {today - timedelta(days=offset) for offset in offsets}
    assert current_streak(days, today) == current
    assert best_streak(days) == best


# --------------------------------------------------------------------------- store


async def test_create_get_and_update() -> None:
    learners = LearnerStore(InMemoryStore())
    record = await learners.create(LearnerProfile.model_validate(LEARNER))
    assert (await learners.get(record.learner_id)).profile.display_name == "Linh"

    updated = await learners.update(
        record.learner_id, record.profile.model_copy(update={"level": "grade 9"})
    )
    assert updated.created_at == record.created_at
    assert (await learners.get(record.learner_id)).profile.level == "grade 9"

    with pytest.raises(LearnerNotFoundError):
        await learners.get("missing")
    with pytest.raises(LearnerNotFoundError):
        await learners.update("missing", record.profile)


async def test_progress_counts_sessions_scores_and_local_streaks() -> None:
    # 23:30 UTC is already the next day in Ho Chi Minh City (UTC+7).
    clock = Clock(datetime(2026, 10, 24, 23, 30, tzinfo=UTC))
    learners = LearnerStore(InMemoryStore(), clock=clock)
    learner = await learners.create(LearnerProfile.model_validate(LEARNER))
    lid = learner.learner_id
    math = SessionProfile(subject="math", level="grade 8")
    physics = SessionProfile(subject="physics", level="grade 8")
    await learners.add_session(lid, "s1", math, clock().isoformat())
    await learners.add_session(lid, "s2", physics, clock().isoformat())
    await learners.add_session(lid, "unused", math, clock().isoformat())

    await learners.record_turn(lid, "s1", subject="math", skills=["algebra"], grade=None)
    clock.now += timedelta(days=1)
    await learners.record_turn(lid, "s1", subject="math", skills=["algebra"], grade=_grade(6))
    clock.now += timedelta(days=1)
    await learners.record_turn(lid, "s2", subject="physics", skills=[], grade=_grade(9))

    progress = await learners.progress(lid)

    assert progress.sessions == 2  # "unused" never had a turn
    assert progress.graded_attempts == 2
    assert progress.average_score == 75.0
    assert (progress.current_streak, progress.best_streak) == (3, 3)
    assert progress.active_today is True
    assert progress.last_active_on == "2026-10-27"
    assert [(s.subject, s.graded_attempts, s.average_score) for s in progress.subjects] == [
        ("math", 1, 60.0),
        ("physics", 1, 90.0),
    ]

    sessions = await learners.list_sessions(lid)
    assert [s.session_id for s in sessions][:2] == ["s2", "s1"]  # most recent first
    s1 = next(s for s in sessions if s.session_id == "s1")
    assert (s1.turns, s1.graded_attempts, s1.best_percentage) == (2, 1, 60.0)

    attempts = await learners.list_attempts(lid)
    assert [a.skills for a in attempts] == [["algebra"], []]
    assert attempts[0].criteria[0].points == 6

    clock.now += timedelta(days=2)
    later = await learners.progress(lid)
    assert (later.current_streak, later.best_streak, later.active_today) == (0, 3, False)


async def test_progress_of_a_new_learner_is_empty() -> None:
    learners = LearnerStore(InMemoryStore())
    learner = await learners.create(LearnerProfile.model_validate(LEARNER))
    progress = await learners.progress(learner.learner_id)
    assert progress.sessions == progress.graded_attempts == progress.current_streak == 0
    assert progress.average_score is None
    assert progress.last_active_on is None


async def test_sqlite_store_keeps_learners_across_restarts(tmp_path: Path) -> None:
    settings = Settings(
        _env_file=None,
        llm_provider="fake",
        checkpointer="sqlite",
        sqlite_path=tmp_path / "nested" / "tutor.sqlite",
    )
    async with open_store(settings) as store:
        learner = await LearnerStore(store).create(LearnerProfile.model_validate(LEARNER))

    async with open_store(settings) as store:  # a fresh process would do the same
        restored = await LearnerStore(store).get(learner.learner_id)

    assert restored.profile == learner.profile


async def test_many_sessions_are_listed_across_pages() -> None:
    learners = LearnerStore(InMemoryStore())
    learner = await learners.create(LearnerProfile.model_validate(LEARNER))
    profile = SessionProfile(subject="math", level="grade 8")
    for i in range(105):
        await learners.add_session(learner.learner_id, f"s{i}", profile, f"2026-10-26T00:{i:03d}")
    assert len(await learners.list_sessions(learner.learner_id)) == 105


# --------------------------------------------------------------------------- HTTP API


def _create_learner(client: TestClient, **changes: Any) -> dict[str, Any]:
    response = client.post("/learners", json={**LEARNER, **changes})
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


def test_learner_api_round_trip(client: TestClient) -> None:
    created = _create_learner(client)
    learner_id = created["learner_id"]
    assert created["display_name"] == "Linh"
    assert created["preferences"]["language"] == "vi"

    assert client.get(f"/learners/{learner_id}").json() == created

    updated = client.put(
        f"/learners/{learner_id}",
        json={**LEARNER, "preferences": {"language": "en", "tone": "direct"}},
    )
    assert updated.status_code == 200
    assert updated.json()["preferences"] == {
        "language": "en",
        "tone": "direct",
        "scaffolding": "standard",
    }
    assert updated.json()["created_at"] == created["created_at"]


def test_unknown_learner_returns_404(client: TestClient) -> None:
    for response in (
        client.get("/learners/nope"),
        client.put("/learners/nope", json=LEARNER),
        client.get("/learners/nope/progress"),
        client.get("/learners/nope/sessions"),
        client.post("/sessions", json={"subject": "math", "level": "8", "learner_id": "nope"}),
    ):
        assert response.status_code == 404
        assert response.json() == {"detail": "Learner 'nope' not found."}


def test_invalid_learner_is_rejected(client: TestClient) -> None:
    assert client.post("/learners", json={**LEARNER, "timezone": "Nowhere/City"}).status_code == 422


def test_sessions_and_progress_follow_chat_turns(client: TestClient) -> None:
    learner_id = _create_learner(client, preferences={"scaffolding": "less"})["learner_id"]
    session = client.post(
        "/sessions",
        json={
            "subject": "algebra",
            "level": "grade 8",
            "learner_id": learner_id,
            "assignment": {
                "question": "Solve for x: 3x + 5 = 20",
                "reference_answer": "x = 5",
                "skills": ["linear-equations"],
                "rubric": {
                    "criteria": [
                        {
                            "id": "answer",
                            "description": "States the solution x = 5",
                            "max_points": 2,
                        }
                    ]
                },
            },
        },
    ).json()
    assert session["learner_id"] == learner_id
    assert session["max_hint_level"] == 2  # "less" scaffolding stops one rung lower
    assert session["assignment"]["skills"] == ["linear-equations"]

    sid = session["session_id"]
    client.post(f"/sessions/{sid}/messages", json={"content": "How do I start?"})
    graded = client.post(f"/sessions/{sid}/messages", json={"content": "x = 5", "intent": "submit"})
    assert graded.json()["route"] == "grader"

    assert client.get(f"/sessions/{sid}").json()["last_grade"]["percentage"] == 100.0
    sessions = client.get(f"/learners/{learner_id}/sessions").json()
    assert [(s["session_id"], s["turns"], s["best_percentage"]) for s in sessions] == [
        (sid, 2, 100.0)
    ]
    progress = client.get(f"/learners/{learner_id}/progress").json()
    assert progress["sessions"] == 1
    assert progress["graded_attempts"] == 1
    assert progress["average_score"] == 100.0
    assert progress["current_streak"] == 1
