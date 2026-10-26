"""Offline demo: a scripted tutoring session driven by the deterministic fake model.

Runs the real graph, hint policy, grader and checkpointer, just without a network call.
"""

from __future__ import annotations

import sys
from typing import TextIO

from langgraph.checkpoint.memory import InMemorySaver

from ai_tutor_agent.agent.events import DoneEvent
from ai_tutor_agent.agent.graph import build_graph
from ai_tutor_agent.agent.hint_policy import HintPolicy
from ai_tutor_agent.agent.service import TutorService
from ai_tutor_agent.llm.fake import FakeChatModel
from ai_tutor_agent.schemas import (
    Assignment,
    Criterion,
    LearnerProfile,
    Rubric,
    SessionProfile,
    TutorPreferences,
)

DEMO_PROFILE = SessionProfile(
    subject="algebra",
    level="grade 8",
    mode="homework",
    assignment=Assignment(
        question="Solve for x: 3x + 5 = 20",
        reference_answer="x = 5",
        rubric=Rubric(
            criteria=[
                Criterion(
                    id="method",
                    description="Subtracts 5 from both sides, then divides both sides by 3",
                    max_points=3,
                ),
                Criterion(id="answer", description="States the solution x = 5", max_points=2),
            ]
        ),
    ),
)

DEMO_TURNS = (
    "hi",
    "How do I even start with 3x + 5 = 20?",
    "I'm still not sure what to do first",
    "Can you just tell me the answer?",
    "My answer: I subtracted 5 from both sides to get 3x = 15, then divided both sides by 3, "
    "so x = 5",
)

GRADE_QUESTION = "What does photosynthesis produce, and why does it matter for plants?"
GRADE_ANSWER = (
    "Photosynthesis makes glucose and oxygen. The plant converts light energy into chemical "
    "energy that is stored in glucose."
)
GRADE_RUBRIC = Rubric(
    criteria=[
        Criterion(id="products", description="Names glucose and oxygen", max_points=3),
        Criterion(
            id="energy",
            description="Explains that light energy is converted into chemical energy",
            max_points=4,
        ),
        Criterion(
            id="chlorophyll", description="Mentions chlorophyll capturing sunlight", max_points=3
        ),
    ]
)


DEMO_LEARNER = LearnerProfile(
    display_name="Linh",
    level="lớp 8",
    subjects=["Toán"],
    goal="Tự tin giải phương trình",
    preferences=TutorPreferences(language="vi", tone="direct", scaffolding="more"),
    timezone="Asia/Ho_Chi_Minh",
)
DEMO_LEARNER_ASSIGNMENT = Assignment(
    question="Giải phương trình: 3x + 5 = 20",
    reference_answer="x = 5",
    rubric=Rubric(
        criteria=[
            Criterion(
                id="method", description="Trừ 5 ở cả hai vế, rồi chia cả hai vế cho 3", max_points=3
            ),
            Criterion(id="answer", description="Nêu nghiệm x = 5", max_points=2),
        ]
    ),
    skills=["linear-equations"],
)
DEMO_LEARNER_TURNS = (
    "Mình nên bắt đầu bài 3x + 5 = 20 từ đâu?",
    "Bài làm của mình: trừ 5 ở hai vế được 3x = 15, rồi chia hai vế cho 3 nên x = 5",
)


async def run_demo(out: TextIO | None = None) -> None:
    stream = out or sys.stdout  # resolved per call, so redirected stdout is honoured
    llm = FakeChatModel()
    policy = HintPolicy()
    service = TutorService(
        build_graph(llm, checkpointer=InMemorySaver(), policy=policy), llm, policy
    )

    def say(text: str = "") -> None:
        print(text, file=stream)

    session = await service.create_session(DEMO_PROFILE)
    say("AI Tutor Agent - offline demo (deterministic fake model, no API key needed)")
    say(f"Session {session.session_id}: {DEMO_PROFILE.subject}, {DEMO_PROFILE.level}, homework")
    say(f"Assignment: {DEMO_PROFILE.assignment.question if DEMO_PROFILE.assignment else '-'}")

    for text in DEMO_TURNS:
        turn = await service.send_message(session.session_id, text)
        say()
        say(f"student > {text}")
        say(f"tutor   [{turn.route}, hint level {turn.hint_level}]")
        for line in turn.reply.splitlines():
            say(f"          {line}")

    say()
    say("POST /grade example (stateless)")
    grade = await service.grade(
        question=GRADE_QUESTION,
        answer=GRADE_ANSWER,
        rubric=GRADE_RUBRIC,
        subject="biology",
        level="grade 7",
    )
    say(grade.model_dump_json(indent=2))

    # Personalisation: a learner profile changes the reply language, tone and hint ladder.
    learner = await service.learners.create(DEMO_LEARNER)
    prefs = DEMO_LEARNER.preferences
    say()
    say(
        f"Learner profile: {DEMO_LEARNER.display_name}, language={prefs.language}, "
        f"tone={prefs.tone}, scaffolding={prefs.scaffolding}"
    )
    personal = await service.create_session(
        SessionProfile(
            subject="Toán",
            level=DEMO_LEARNER.level,
            assignment=DEMO_LEARNER_ASSIGNMENT,
            learner_id=learner.learner_id,
        )
    )
    for text in DEMO_LEARNER_TURNS:
        events = [event async for event in service.stream_message(personal.session_id, text)]
        done = events[-1]
        assert isinstance(done, DoneEvent)  # a streamed turn always ends with "done"
        say()
        say(f"student > {text}")
        say(f"tutor   [{done.route}, hint level {done.hint_level}]")
        for line in done.reply.splitlines():
            say(f"          {line}")
        say(f"          (streamed as: {summarise_events([e.type for e in events])})")

    progress = await service.learners.progress(learner.learner_id)
    say()
    say(
        f"Progress: {progress.sessions} session, {progress.graded_attempts} graded attempt, "
        f"average score {progress.average_score or 0:g}%, streak {progress.current_streak} day"
    )


def summarise_events(types: list[str]) -> str:
    """``["route", "token", "token", "done"]`` -> ``"route -> token x2 -> done"``."""
    groups: list[tuple[str, int]] = []
    for name in types:
        if groups and groups[-1][0] == name:
            groups[-1] = (name, groups[-1][1] + 1)
        else:
            groups.append((name, 1))
    return " -> ".join(name if count == 1 else f"{name} x{count}" for name, count in groups)
