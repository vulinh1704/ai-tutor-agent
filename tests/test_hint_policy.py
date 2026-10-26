import pytest

from ai_tutor_agent.agent.hint_policy import HintPolicy
from ai_tutor_agent.schemas import Language, Scaffolding


def test_hint_level_escalates_and_caps() -> None:
    policy = HintPolicy(max_level=3)
    levels = []
    level = 0
    for _ in range(5):
        level = policy.next_level(level)
        levels.append(level)
    assert levels == [1, 2, 3, 3, 3]


def test_new_problem_restarts_the_ladder() -> None:
    assert HintPolicy().next_level(3, new_problem=True) == 1


def _climb(policy: HintPolicy, scaffolding: Scaffolding, turns: int = 4) -> list[int]:
    levels, level = [], 0
    for _ in range(turns):
        level = policy.next_level(level, scaffolding=scaffolding)
        levels.append(level)
    return levels


@pytest.mark.parametrize(
    ("scaffolding", "expected"),
    [("standard", [1, 2, 3, 3]), ("more", [2, 3, 3, 3]), ("less", [1, 2, 2, 2])],
)
def test_scaffolding_shifts_the_ladder(scaffolding: Scaffolding, expected: list[int]) -> None:
    assert _climb(HintPolicy(max_level=3), scaffolding) == expected


def test_scaffolding_respects_a_one_rung_ladder() -> None:
    policy = HintPolicy(max_level=1)
    assert _climb(policy, "less") == _climb(policy, "more") == [1, 1, 1, 1]
    assert policy.cap("less") == 1


def test_more_scaffolding_restarts_one_rung_higher() -> None:
    assert HintPolicy().next_level(3, new_problem=True, scaffolding="more") == 2


@pytest.mark.parametrize("max_level", [0, 6])
def test_max_level_is_validated(max_level: int) -> None:
    with pytest.raises(ValueError, match="max_level"):
        HintPolicy(max_level=max_level)


@pytest.mark.parametrize(
    ("reply", "reference", "leaks"),
    [
        # Explicit giveaways, with or without a reference answer.
        ("The answer is 5.", None, True),
        ("So the correct solution is to divide by 3, giving 5.", None, True),
        ("Final answer: x = 5", None, True),
        ("final answer = 42", None, True),
        # Socratic questions that merely mention "the answer".
        ("What do you think the answer is?", None, False),
        ("What's your final answer?", None, False),
        ("Write your final answer in words.", None, False),
        # Equation references.
        ("So x = 5, nice work!", "x = 5", True),
        ("That means x equals 5.", "x = 5", True),
        ("Subtract 5 from both sides first. What do you get?", "x = 5", False),
        ("We get 3x = 15 after that step.", "x = 5", False),
        # Short references only count when stated as a result.
        ("It is 5 apples in total.", "5", True),
        ("There are 5 steps in this method.", "5", False),
        # Longer text references count anywhere.
        ("Remember: chlorophyll absorbs light energy.", "chlorophyll absorbs light", True),
        ("Which pigment absorbs light?", "chlorophyll absorbs light", False),
        # Vietnamese giveaways and results.
        ("Đáp án là 5 nhé.", None, True),
        ("Đáp số: x = 5", None, True),
        ("Kết quả cuối cùng là 12.", None, True),
        ("Theo bạn, đáp án là gì?", None, False),
        ("Vậy đáp số là bao nhiêu?", None, False),
        ("Vậy x bằng 5 đó!", "x = 5", True),
        ("Bạn thử trừ 5 ở hai vế xem được gì?", "x = 5", False),
    ],
)
def test_leak_detection(reply: str, reference: str | None, leaks: bool) -> None:
    assert HintPolicy().leaks_answer(reply, reference) is leaks


@pytest.mark.parametrize("language", ["en", "vi"])
@pytest.mark.parametrize("level", [1, 2, 3, 4, 5])
def test_fallback_reply_never_leaks(level: int, language: Language) -> None:
    policy = HintPolicy(max_level=5)
    reply = policy.fallback_reply(level, language)
    assert reply.endswith("?") or reply.endswith(".")
    assert not policy.leaks_answer(reply, "x = 5")


def test_fallback_reply_is_localised() -> None:
    assert HintPolicy().fallback_reply(1, "vi").startswith("Ở chế độ làm bài tập")
