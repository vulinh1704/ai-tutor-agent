"""Canned, learner-facing text in every supported reply language.

Only deterministic strings live here (clarifying questions, safe fallback hints, the grade
summary). Model replies are steered into the learner's language through the prompts.
"""

from __future__ import annotations

from typing import Final

from ai_tutor_agent.schemas import Language

_TEXT: Final[dict[Language, dict[str, str]]] = {
    "en": {
        "clarify_assignment": (
            "I'd love to help with this {subject} problem! Which part are you stuck on, and what "
            "have you tried so far?"
        ),
        "clarify_open": (
            "I'd love to help with your {subject} work! Could you share the exact problem and "
            "what you've tried so far?"
        ),
        "fallback": (
            "I can't hand you the final answer in homework mode, but you're closer than you "
            "think. {prompt}"
        ),
        "fallback_1": "What is the problem asking you to find, in your own words?",
        "fallback_2": (
            "Which rule or method do you think applies here? Try the first step and tell me what "
            "you get."
        ),
        "fallback_default": (
            "Try the next step on your own and tell me what you get. I'll check your work."
        ),
        "safe_next_step": (
            "Compare your answer with each criterion above. Which one could you strengthen?"
        ),
        "score": "Score",
        "next_step": "Next step",
    },
    "vi": {
        "clarify_assignment": (
            "Mình rất sẵn lòng giúp bạn với bài {subject} này! Bạn đang vướng ở chỗ nào, và bạn "
            "đã thử làm những gì rồi?"
        ),
        "clarify_open": (
            "Mình rất sẵn lòng giúp bạn học {subject}! Bạn gửi mình đề bài cụ thể và cho mình "
            "biết bạn đã thử những gì nhé?"
        ),
        "fallback": (
            "Ở chế độ làm bài tập, mình không thể cho bạn đáp án cuối cùng, nhưng bạn đang ở rất "
            "gần rồi đấy. {prompt}"
        ),
        "fallback_1": "Theo cách hiểu của bạn, đề bài đang yêu cầu mình tìm gì?",
        "fallback_2": (
            "Bạn nghĩ quy tắc hay phương pháp nào áp dụng được ở đây? Thử làm bước đầu tiên rồi "
            "cho mình biết kết quả nhé."
        ),
        "fallback_default": (
            "Bạn thử tự làm bước tiếp theo rồi cho mình biết kết quả nhé. Mình sẽ kiểm tra "
            "giúp bạn."
        ),
        "safe_next_step": (
            "Hãy so bài làm của bạn với từng tiêu chí ở trên. Tiêu chí nào bạn có thể làm tốt hơn?"
        ),
        "score": "Điểm",
        "next_step": "Bước tiếp theo",
    },
}


def text(language: Language, key: str, **values: str) -> str:
    """Return the canned string ``key`` in ``language``, with ``{placeholders}`` filled in."""
    template = _TEXT[language].get(key) or _TEXT["en"][key]
    return template.format(**values) if values else template
