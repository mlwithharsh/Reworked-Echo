from __future__ import annotations

from typing import Iterable

from ..schemas import PersonalityProfile


def build_conditioned_prompt(
    user_message: str,
    profile: PersonalityProfile,
    history: list[dict[str, str]],
    retrieved_examples: Iterable[str],
    model_version: str,
) -> str:
    verbosity = "brief" if profile.brevity_preference >= 0.65 else "detailed"
    tone = "emotionally supportive" if profile.support_preference >= 0.6 else "neutral-professional"
    mode = "task-focused" if profile.task_focus >= 0.6 else "casual-conversational"

    return (
        f"You are Echo, model version {model_version}.\n"
        f"User preferences: verbosity={verbosity}, tone={tone}, mode={mode}, engagement={profile.engagement_preference:.2f}.\n"
        f"Conversation history: {history[-6:]}\n"
        f"Successful prior examples: {list(retrieved_examples)}\n"
        "Instructions:\n"
        "1. Match the requested level of brevity.\n"
        "2. Stay consistent with emotional support preference.\n"
        "3. Favor actionable structure when task_focus is high.\n"
        "4. Avoid repetition and unclear filler.\n"
        f"User: {user_message}\n"
        "Assistant:"
    )
