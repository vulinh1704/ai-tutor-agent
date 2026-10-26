"""HTTP API tests with FastAPI's TestClient and the deterministic fake model."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from ai_tutor_agent import __version__
from ai_tutor_agent.api.app import create_app
from ai_tutor_agent.config import Settings
from ai_tutor_agent.llm.base import LLMError, LLMRefusalError
from ai_tutor_agent.llm.factory import ConfigurationError
from ai_tutor_agent.llm.fake import FakeChatModel
from ai_tutor_agent.schemas import CriterionAssessment, GraderOutput

SESSION: dict[str, Any] = {
    "subject": "algebra",
    "level": "grade 8",
    "assignment": {
        "question": "Solve for x: 3x + 5 = 20",
        "reference_answer": "x = 5",
        "rubric": {
            "criteria": [
                {
                    "id": "method",
                    "description": "Subtracts 5 from both sides, then divides both sides by 3",
                    "max_points": 3,
                },
                {"id": "answer", "description": "States the solution x = 5", "max_points": 2},
            ]
        },
    },
}

GRADE_REQUEST: dict[str, Any] = {
    "question": "Solve for x: 3x + 5 = 20",
    "answer": "I subtracted 5 from both sides, so x = 5",
    "rubric": SESSION["assignment"]["rubric"],
    "subject": "algebra",
    "level": "grade 8",
}


def _create_session(client: TestClient, **overrides: Any) -> dict[str, Any]:
    response = client.post("/sessions", json={**SESSION, **overrides})
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "version": __version__,
        "llm_provider": "fake",
        "llm_model": "fake-tutor",
        "checkpointer": "memory",
    }


def test_create_session_hides_the_reference_answer(client: TestClient) -> None:
    body = _create_session(client)
    assert len(body["session_id"]) == 32
    assert body["mode"] == "homework"
    assert body["assignment"]["has_reference_answer"] is True
    assert "reference_answer" not in body["assignment"]
    assert body["messages"] == []


@pytest.mark.parametrize(
    "payload",
    [
        {"subject": "", "level": "grade 8"},
        {"subject": "math", "level": "grade 8", "mode": "cheat"},
        {
            "subject": "math",
            "level": "grade 8",
            "assignment": {
                "question": "Solve it",
                "rubric": {
                    "criteria": [
                        {"id": "a", "description": "first", "max_points": 1},
                        {"id": "a", "description": "again", "max_points": 1},
                    ]
                },
            },
        },
    ],
)
def test_create_session_validates_input(client: TestClient, payload: dict[str, Any]) -> None:
    assert client.post("/sessions", json=payload).status_code == 422


def test_chat_flow_tutor_then_grader(client: TestClient) -> None:
    session_id = _create_session(client)["session_id"]

    hint = client.post(f"/sessions/{session_id}/messages", json={"content": "How do I start?"})
    assert hint.status_code == 200
    assert hint.json()["route"] == "tutor"
    assert hint.json()["hint_level"] == 1
    assert hint.json()["grade"] is None

    graded = client.post(
        f"/sessions/{session_id}/messages",
        json={"content": "My answer: subtract 5 from both sides, divide both sides by 3, x = 5"},
    )
    assert graded.status_code == 200
    body = graded.json()
    assert body["route"] == "grader"
    assert body["grade"]["score"] == body["grade"]["max_score"] == 5

    history = client.get(f"/sessions/{session_id}").json()["messages"]
    assert [m["role"] for m in history] == ["student", "tutor", "student", "tutor"]
    assert history[0]["content"] == "How do I start?"


def test_unknown_session_returns_404(client: TestClient) -> None:
    assert client.get("/sessions/nope").status_code == 404
    response = client.post("/sessions/nope/messages", json={"content": "hello"})
    assert response.status_code == 404
    assert response.json() == {"detail": "Session 'nope' not found."}


@pytest.mark.parametrize("content", ["", "x" * 4001])
def test_message_length_is_validated(client: TestClient, content: str) -> None:
    session_id = _create_session(client)["session_id"]
    response = client.post(f"/sessions/{session_id}/messages", json={"content": content})
    assert response.status_code == 422


def test_grade_returns_structured_feedback(client: TestClient) -> None:
    response = client.post("/grade", json=GRADE_REQUEST)
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"score", "max_score", "percentage", "criteria", "next_step_hint"}
    assert [c["criterion_id"] for c in body["criteria"]] == ["method", "answer"]
    assert body["max_score"] == 5
    assert 0 <= body["score"] <= 5


def test_grade_rejects_invalid_rubric(client: TestClient) -> None:
    payload = {**GRADE_REQUEST, "rubric": {"criteria": []}}
    assert client.post("/grade", json=payload).status_code == 422


def test_model_refusal_maps_to_422(client: TestClient, fake_llm: FakeChatModel) -> None:
    fake_llm.queue_structured(LLMRefusalError("declined"))
    response = client.post("/grade", json=GRADE_REQUEST)
    assert response.status_code == 422
    assert response.json()["detail"] == "The model declined to respond to this request."


def test_provider_failure_maps_to_502(client: TestClient, fake_llm: FakeChatModel) -> None:
    fake_llm.queue_structured(LLMError("upstream timeout"))
    assert client.post("/grade", json=GRADE_REQUEST).status_code == 502


def test_invalid_grading_maps_to_502(client: TestClient, fake_llm: FakeChatModel) -> None:
    bad = GraderOutput(
        assessments=[CriterionAssessment(criterion_id="nope", points=1, feedback="?")],
        next_step_hint="?",
    )
    fake_llm.queue_structured(bad, bad)
    response = client.post("/grade", json=GRADE_REQUEST)
    assert response.status_code == 502
    assert "invalid grading" in response.json()["detail"]


def test_app_fails_fast_on_missing_api_key() -> None:
    settings = Settings(_env_file=None, llm_provider="openai")
    with pytest.raises(ConfigurationError, match="LLM_PROVIDER=fake"):
        create_app(settings)


def test_openapi_schema_lists_the_endpoints(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    assert {"/health", "/sessions", "/sessions/{session_id}", "/grade"} <= set(paths)
    assert "/sessions/{session_id}/messages" in paths
