"""The streaming leak guard releases exactly what the non-streaming guard would send."""

from __future__ import annotations

import random

import pytest

from ai_tutor_agent.agent.hint_policy import HintPolicy
from ai_tutor_agent.agent.stream_guard import StreamGuard
from ai_tutor_agent.llm.fake import split_into_chunks

DRAFTS = [
    "Good question! What do you already know about equations like this one? Try the first step.",
    "Let's pick a strategy: undo the + 5 first. What equation do you get after that step?",
    "Easy one. The answer is x = 5, so you are done!",
    "Subtract 5 from both sides and you get 3x = 15. Then divide by 3, so x = 5",
    "If you get 50 apples and give away 45, how many are left? Count carefully.",
    "Đáp án là 5 nhé, bạn chỉ cần chép lại thôi.",
    "Bạn thử trừ 5 ở hai vế xem được phương trình nào nhé?",
    "Theo bạn, đáp số là bao nhiêu? Đáp án là gì nhỉ?",
]


def _stream(guard: StreamGuard, chunks: list[str]) -> str:
    released = []
    for chunk in chunks:
        released.append(guard.feed(chunk))
        if guard.leaked:
            return "".join(released)
    released.append(guard.finish())
    return "".join(released)


def _random_chunks(text: str, rng: random.Random) -> list[str]:
    cuts = sorted(rng.sample(range(1, len(text)), k=min(len(text) - 1, rng.randint(1, 12))))
    return [text[i:j] for i, j in zip([0, *cuts], [*cuts, len(text)], strict=True)]


@pytest.mark.parametrize("draft", DRAFTS)
@pytest.mark.parametrize("reference", [None, "x = 5", "5"])
def test_streaming_agrees_with_the_full_check(draft: str, reference: str | None) -> None:
    policy = HintPolicy()
    expected_leak = policy.leaks_answer(draft, reference)
    rng = random.Random(f"{draft}|{reference}")
    for _ in range(25):
        guard = StreamGuard(policy, reference, holdback=rng.choice([0, 8, 48]))
        released = _stream(guard, _random_chunks(draft, rng))
        assert guard.leaked is expected_leak
        if expected_leak:
            assert not policy.leaks_answer(released, reference)
        else:
            assert released == draft


def test_holdback_delays_release_until_enough_text_is_checked() -> None:
    guard = StreamGuard(HintPolicy(), None, holdback=20)
    assert guard.feed("Try the first ") == ""  # 14 checked characters, all held back
    # 45 checked: release whole words up to 20 characters behind the checked text.
    assert guard.feed("step on your own, then tell me ") == "Try the first step on "
    assert guard.finish() == "your own, then tell me "


def test_the_opening_words_of_a_leak_are_never_released() -> None:
    guard = StreamGuard(HintPolicy(), "x = 5")
    released = _stream(guard, split_into_chunks("Great work so far. So the final answer is x = 5."))
    assert guard.leaked
    assert "answer" not in released
    assert released == ""


def test_a_half_written_number_is_not_a_false_alarm() -> None:
    # "you get 5" would leak a reference of "5", but the full text says "50".
    guard = StreamGuard(HintPolicy(), "5", holdback=0)
    assert guard.feed("Count again: you get 5") == "Count again: you get "
    assert not guard.leaked
    assert guard.feed("0 apples in total. ") == "50 apples in total. "
    assert guard.finish() == ""
    assert not guard.leaked


def test_finish_catches_a_leak_at_the_very_end() -> None:
    guard = StreamGuard(HintPolicy(), "x = 5", holdback=0)
    guard.feed("Divide both sides by 3, so x =")
    assert not guard.leaked
    guard.feed(" 5")
    assert guard.finish() == ""
    assert guard.leaked
    assert guard.feed("more") == ""  # a leaked draft releases nothing more
