from __future__ import annotations

from ..schemas import FeedbackRequest, PersonalityProfile


def update_profile_from_feedback(profile: PersonalityProfile, feedback: FeedbackRequest) -> PersonalityProfile:
    """Update user profile based on explicit feedback (thumbs up/down + tags)."""
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
    if "clear" in feedback.tags:
        updated.engagement_preference = min(1.0, updated.engagement_preference + 0.05)

    updated.engagement_preference = max(0.0, min(1.0, updated.engagement_preference + delta))
    updated.points += 5 if feedback.vote == "up" else 1
    return updated


def infer_profile_from_message(profile: PersonalityProfile, message: str) -> PersonalityProfile:
    """Automatically adjust profile based on message characteristics.
    
    This replaces the manual sliders — the system infers user preferences
    from their interaction patterns rather than exposing controls.
    """
    updated = profile.model_copy(deep=True)
    words = message.split()
    word_count = len(words)
    lowered = message.lower()

    # Short messages suggest user prefers brief replies
    if word_count <= 5:
        updated.brevity_preference = min(1.0, updated.brevity_preference + 0.02)
    elif word_count >= 30:
        # Longer messages suggest user is comfortable with detailed responses
        updated.brevity_preference = max(0.0, updated.brevity_preference - 0.02)

    # Question marks suggest task/information seeking
    if "?" in message:
        updated.task_focus = min(1.0, updated.task_focus + 0.02)

    # Emotional keywords suggest preference for supportive tone
    emotional_markers = {"feel", "feeling", "sad", "happy", "stressed", "anxious", "worried",
                         "scared", "lonely", "hurt", "upset", "frustrated", "love", "miss"}
    if emotional_markers & set(lowered.split()):
        updated.support_preference = min(1.0, updated.support_preference + 0.03)

    # Casual greetings suggest low task focus
    casual_markers = {"hey", "hi", "hello", "yo", "sup", "hola", "howdy"}
    if set(lowered.split()) & casual_markers and word_count <= 4:
        updated.task_focus = max(0.0, updated.task_focus - 0.02)
        updated.engagement_preference = min(1.0, updated.engagement_preference + 0.02)

    # Flirty/Playful markers for Suzi/Helix
    playful_markers = {"fun", "play", "playful", "joke", "haha", "lol", "joy"}
    flirty_markers = {"hot", "sexy", "cute", "handsome", "babe", "sweetie", "love", "💋", "😏", "🔥"}
    
    if set(lowered.split()) & playful_markers:
        updated.engagement_preference = min(1.0, updated.engagement_preference + 0.03)
    if set(lowered.split()) & flirty_markers:
        updated.engagement_preference = min(1.0, updated.engagement_preference + 0.05)
        updated.support_preference = min(1.0, updated.support_preference + 0.02) # Intimacy/support

    return updated
