from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import InMemorySaver

from ai_tutor_agent.agent.graph import TutorGraph, build_graph
from ai_tutor_agent.agent.hint_policy import HintPolicy
from ai_tutor_agent.agent.service import TutorService
from ai_tutor_agent.api.app import create_app
from ai_tutor_agent.config import Settings
from ai_tutor_agent.llm.fake import FakeChatModel
from ai_tutor_agent.schemas import Assignment, Criterion, Rubric, SessionProfile


@pytest.fixture(autouse=True)
def _isolated_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the developer's shell configuration out of the tests."""
    for name in Settings.model_fields:
        monkeypatch.delenv(name.upper(), raising=False)


@pytest.fixture
def rubric() -> Rubric:
    return Rubric(
        criteria=[
            Criterion(
                id="method",
                description="Subtracts 5 from both sides, then divides both sides by 3",
                max_points=3,
            ),
            Criterion(id="answer", description="States the solution x = 5", max_points=2),
        ]
    )


@pytest.fixture
def profile(rubric: Rubric) -> SessionProfile:
    return SessionProfile(
        subject="algebra",
        level="grade 8",
        mode="homework",
        assignment=Assignment(
            question="Solve for x: 3x + 5 = 20", rubric=rubric, reference_answer="x = 5"
        ),
    )


@pytest.fixture
def fake_llm() -> FakeChatModel:
    return FakeChatModel()


@pytest.fixture
def graph(fake_llm: FakeChatModel) -> TutorGraph:
    return build_graph(fake_llm, checkpointer=InMemorySaver(), policy=HintPolicy())


@pytest.fixture
def service(graph: TutorGraph, fake_llm: FakeChatModel) -> TutorService:
    return TutorService(graph, fake_llm, HintPolicy())


@pytest.fixture
def settings() -> Settings:
    return Settings(_env_file=None, llm_provider="fake")


@pytest.fixture
def client(settings: Settings, fake_llm: FakeChatModel) -> Iterator[TestClient]:
    with TestClient(create_app(settings, llm=fake_llm)) as test_client:
        yield test_client
