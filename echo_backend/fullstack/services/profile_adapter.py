from __future__ import annotations

from ..schemas import FeedbackRequest, PersonalityProfile


def update_profile_from_feedback(profile: PersonalityProfile, feedback: FeedbackRequest) -> PersonalityProfile:
    updated = profile.model_copy(deep=True)
    delta = 0.05 if feedback.vote == "up" else -0.05

    if "too_long" in feedback.tags:
        updated.brevity_preference = min(1.0, updated.brevity_preference + 0.1)
    if "helpful" in feedback.tags:
        updated.task_focus = min(1.0, updated.task_focus + 0.05)
    if "confusing" in feedback.tags:
        updated.task_focus = max(0.0, updated.task_focus - 0.05)
    if "supportive" in feedback.tags:
        updated.support_preference = min(1.0, updated.support_preference + 0.08)
    if "too_cold" in feedback.tags:
        updated.support_preference = min(1.0, updated.support_preference + 0.12)

    updated.engagement_preference = max(0.0, min(1.0, updated.engagement_preference + delta))
    updated.points += 5 if feedback.vote == "up" else 1
    return updated
