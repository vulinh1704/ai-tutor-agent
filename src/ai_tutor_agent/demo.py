"""Offline demo: a scripted tutoring session driven by the deterministic fake model.

Runs the real graph, hint policy, grader and checkpointer, just without a network call.
"""

from __future__ import annotations

import sys
from typing import TextIO

from langgraph.checkpoint.memory import InMemorySaver

from ai_tutor_agent.agent.graph import build_graph
from ai_tutor_agent.agent.hint_policy import HintPolicy
from ai_tutor_agent.agent.service import TutorService
from ai_tutor_agent.llm.fake import FakeChatModel
from ai_tutor_agent.schemas import Assignment, Criterion, Rubric, SessionProfile

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


async def run_demo(out: TextIO = sys.stdout) -> None:
    llm = FakeChatModel()
    policy = HintPolicy()
    service = TutorService(
        build_graph(llm, checkpointer=InMemorySaver(), policy=policy), llm, policy
    )

    def say(text: str = "") -> None:
        print(text, file=out)

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
