from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from supabase import Client, create_client

from ..config import Settings
from ..schemas import FeedbackRequest, InteractionRecord, PersonalityProfile


class SupabaseRepository:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client: Client | None = None
        self.connected = bool(settings.supabase_url and settings.supabase_key)
        self.local_users: dict[str, PersonalityProfile] = {}
        self.local_interactions: dict[str, InteractionRecord] = {}
        self.local_feedback: list[dict[str, Any]] = []
        self.local_model_versions: list[dict[str, Any]] = [
            {"version": settings.active_model_version, "status": "active", "ab_bucket": "A", "adapter_path": None}
        ]
        if self.connected:
            self.client = create_client(settings.supabase_url, settings.supabase_key)

    def _default_profile(self, user_id: str) -> PersonalityProfile:
        return PersonalityProfile(user_id=user_id)

    def get_user_profile(self, user_id: str) -> PersonalityProfile:
        if not self.client:
            return self.local_users.get(user_id, self._default_profile(user_id))
        result = self.client.table("users").select("*").eq("id", user_id).limit(1).execute()
        if result.data:
            row = result.data[0]
            return PersonalityProfile(
                user_id=row["id"],
                engagement_preference=row.get("engagement_preference", 0.5),
                brevity_preference=row.get("brevity_preference", 0.5),
                support_preference=row.get("support_preference", 0.5),
                task_focus=row.get("task_focus", 0.5),
                points=row.get("points", 0),
            )
        return self._default_profile(user_id)

    def upsert_user_profile(self, profile: PersonalityProfile) -> PersonalityProfile:
        payload = {
            "id": profile.user_id,
            "engagement_preference": profile.engagement_preference,
            "brevity_preference": profile.brevity_preference,
            "support_preference": profile.support_preference,
            "task_focus": profile.task_focus,
            "points": profile.points,
        }
        if not self.client:
            self.local_users[profile.user_id] = profile
            return profile
        self.client.table("users").upsert(payload).execute()
        return profile

    def create_interaction(self, user_id: str, input_text: str, response_text: str, model_version: str, metadata: dict[str, Any]) -> InteractionRecord:
        interaction_id = str(uuid4())
        created_at = datetime.now(timezone.utc)
        record = InteractionRecord(
            id=interaction_id,
            user_id=user_id,
            input_text=input_text,
            response_text=response_text,
            model_version=model_version,
            metadata=metadata,
            created_at=created_at,
        )
        payload = {
            "id": interaction_id,
            "user_id": user_id,
            "input": input_text,
            "response": response_text,
            "timestamp": created_at.isoformat(),
            "metadata": metadata,
            "model_version": model_version,
        }
        if not self.client:
            self.local_interactions[interaction_id] = record
            return record
        self.client.table("interactions").insert(payload).execute()
        return record

    def list_recent_interactions(self, user_id: str, limit: int = 20) -> list[InteractionRecord]:
        if not self.client:
            records = [record for record in self.local_interactions.values() if record.user_id == user_id]
            return sorted(records, key=lambda item: item.created_at)[-limit:]
        result = self.client.table("interactions").select("*").eq("user_id", user_id).order("timestamp", desc=False).limit(limit).execute()
        items = []
        for row in result.data or []:
            items.append(
                InteractionRecord(
                    id=row["id"],
                    user_id=row["user_id"],
                    input_text=row["input"],
                    response_text=row["response"],
                    model_version=row.get("model_version", self.settings.active_model_version),
                    metadata=row.get("metadata", {}),
                    created_at=datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00")),
                )
            )
        return items

    def add_feedback(self, feedback: FeedbackRequest, reward: float) -> None:
        payload = {
            "interaction_id": feedback.interaction_id,
            "user_id": feedback.user_id,
            "reward": reward,
            "tags": feedback.tags,
            "notes": feedback.notes,
            "vote": feedback.vote,
        }
        if not self.client:
            self.local_feedback.append(payload)
            return
        self.client.table("feedback").insert(payload).execute()

    def store_embedding(self, interaction_id: str, user_id: str, vector: list[float], source_text: str) -> None:
        payload = {
            "interaction_id": interaction_id,
            "user_id": user_id,
            "embedding": vector,
            "source_text": source_text,
        }
        if not self.client:
            return
        self.client.table("embeddings").insert(payload).execute()

    def fetch_embeddings(self, user_id: str, limit: int = 100) -> list[dict[str, Any]]:
        if not self.client:
            return []
        result = self.client.table("embeddings").select("*").eq("user_id", user_id).limit(limit).execute()
        return result.data or []

    def list_model_versions(self) -> list[dict[str, Any]]:
        if not self.client:
            return self.local_model_versions
        result = self.client.table("model_versions").select("*").order("created_at", desc=True).execute()
        return result.data or []

    def register_model_version(self, payload: dict[str, Any]) -> None:
        if not self.client:
            self.local_model_versions.append(payload)
            return
        self.client.table("model_versions").insert(payload).execute()

    def fetch_training_batch(self, limit: int = 100) -> list[dict[str, Any]]:
        if not self.client:
            batch = []
            for feedback in self.local_feedback[-limit:]:
                interaction = self.local_interactions.get(feedback["interaction_id"])
                if interaction:
                    batch.append({"interaction": interaction.model_dump(), "feedback": feedback})
            return batch
        result = self.client.table("feedback").select("reward,tags,vote,interaction_id,interactions(*)").limit(limit).execute()
        return result.data or []
