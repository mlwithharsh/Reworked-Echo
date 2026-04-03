from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class PersonalityProfile(BaseModel):
    user_id: str
    engagement_preference: float = 0.5
    brevity_preference: float = 0.5
    support_preference: float = 0.5
    task_focus: float = 0.5
    points: int = 0


class ChatRequest(BaseModel):
    user_id: str
    message: str
    history: list[dict[str, str]] = Field(default_factory=list)
    personality_override: PersonalityProfile | None = None


class FeedbackRequest(BaseModel):
    user_id: str
    interaction_id: str
    vote: Literal["up", "down"]
    tags: list[str] = Field(default_factory=list)
    notes: str | None = None


class FeedbackResponse(BaseModel):
    reward: float
    updated_profile: PersonalityProfile


class InteractionRecord(BaseModel):
    id: str
    user_id: str
    input_text: str
    response_text: str
    model_version: str
    metadata: dict[str, Any]
    created_at: datetime


class StatusResponse(BaseModel):
    status: str
    model_version: str
    supabase_connected: bool
    adaptive_serving: bool = True


class TrainingRunRequest(BaseModel):
    batch_limit: int = 100
    version_label: str = "candidate"


class TrainingRunResponse(BaseModel):
    accepted: bool
    message: str
