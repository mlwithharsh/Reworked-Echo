from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4, UUID

from supabase import Client, create_client

from werkzeug.security import generate_password_hash, check_password_hash
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

    def signup(self, email, password, name=""):
        try:
            if not self.client:
                return None, "Database not connected"
            
            # Check if user exists
            existing = self.client.table("users").select("id").eq("email", email).execute()
            if existing.data:
                return None, "Email already registered"
            
            user_id = str(uuid4())
            hashed_pwd = generate_password_hash(password)
            
            payload = {
                "id": user_id,
                "email": email,
                "password_hash": hashed_pwd,
                "name": name,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            self.client.table("users").insert(payload).execute()
            return user_id, None
        except Exception as e:
            return None, str(e)

    def login(self, email, password):
        try:
            if not self.client:
                return None, "Database not connected"
                
            result = self.client.table("users").select("*").eq("email", email).execute()
            if not result.data:
                return None, "Invalid email or password"
            
            user = result.data[0]
            if not check_password_hash(user["password_hash"], password):
                return None, "Invalid email or password"
            
            return user["id"], None
        except Exception as e:
            return None, str(e)

    def _default_profile(self, user_id: str) -> PersonalityProfile:
        return PersonalityProfile(user_id=user_id)

    def _is_valid_uuid(self, user_id: str) -> bool:
        try:
            UUID(str(user_id))
            return True
        except (ValueError, AttributeError):
            return False

    def get_user_profile(self, user_id: str) -> PersonalityProfile:
        if not self.client or not self._is_valid_uuid(user_id):
            return self.local_users.get(user_id, self._default_profile(user_id))
        try:
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
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Supabase get_user_profile failed, using local: {e}")
        return self.local_users.get(user_id, self._default_profile(user_id))

    def upsert_user_profile(self, profile: PersonalityProfile) -> PersonalityProfile:
        payload = {
            "id": profile.user_id,
            "engagement_preference": profile.engagement_preference,
            "brevity_preference": profile.brevity_preference,
            "support_preference": profile.support_preference,
            "task_focus": profile.task_focus,
            "points": profile.points,
        }
        if not self.client or not self._is_valid_uuid(profile.user_id):
            self.local_users[profile.user_id] = profile
            return profile
        try:
            self.client.table("users").upsert(payload).execute()
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Supabase upsert_user_profile failed: {e}")
            self.local_users[profile.user_id] = profile
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
        if not self.client or not self._is_valid_uuid(user_id):
            self.local_interactions[interaction_id] = record
            return record
        try:
            self.client.table("interactions").insert(payload).execute()
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Supabase create_interaction failed: {e}")
            self.local_interactions[interaction_id] = record
        return record

    def list_recent_interactions(self, user_id: str, limit: int = 20) -> list[InteractionRecord]:
        if not self.client:
            return self._get_local_interactions(user_id, limit)
            
        # Supabase Join if possible, fallback to separate fetch
        try:
            try:
                # We use a join if the foreign key exists, otherwise we'll fetch separately
                result = self.client.table("interactions").select("*, feedback(vote, tags)").eq("user_id", user_id).order("timestamp", desc=False).limit(limit).execute()
            except Exception:
                # Fallback for when feedback table join fails
                result = self.client.table("interactions").select("*").eq("user_id", user_id).order("timestamp", desc=False).limit(limit).execute()

            items = []
            for row in result.data or []:
                fb_list = row.get("feedback", [])
                fb = fb_list[0] if isinstance(fb_list, list) and fb_list else (fb_list if isinstance(fb_list, dict) else {})
                
                items.append(
                    InteractionRecord(
                        id=row["id"],
                        user_id=row["user_id"],
                        input_text=row["input"],
                        response_text=row["response"],
                        model_version=row.get("model_version", self.settings.active_model_version),
                        metadata=row.get("metadata", {}),
                        created_at=datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00")),
                        vote=fb.get("vote"),
                        tags=fb.get("tags", [])
                    )
                )
            return items
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Supabase connection/query failed in list_recent_interactions: {e}")
            return self._get_local_interactions(user_id, limit)

    def _get_local_interactions(self, user_id: str, limit: int = 20) -> list[InteractionRecord]:
        records = [record for record in self.local_interactions.values() if record.user_id == user_id]
        # Merge local feedback
        for record in records:
            matched_fb = next((fb for fb in self.local_feedback if fb.get("interaction_id") == record.id), None)
            if matched_fb:
                record.vote = matched_fb.get("vote")
                record.tags = matched_fb.get("tags", [])
        return sorted(records, key=lambda item: item.created_at)[-limit:]

    def add_feedback(self, feedback: FeedbackRequest, reward: float) -> None:
        payload = {
            "interaction_id": feedback.interaction_id,
            "user_id": feedback.user_id,
            "reward": reward,
            "tags": feedback.tags,
            "notes": feedback.notes,
            "vote": feedback.vote,
        }
        if not self.client or not self._is_valid_uuid(feedback.user_id):
            self.local_feedback.append(payload)
            return
            
        try:
            self.client.table("feedback").insert(payload).execute()
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to persist feedback to Supabase: {e}")
            self.local_feedback.append(payload)

    def store_embedding(self, interaction_id: str, user_id: str, vector: list[float], source_text: str) -> None:
        payload = {
            "interaction_id": interaction_id,
            "user_id": user_id,
            "embedding": vector,
            "source_text": source_text,
        }
        if not self.client:
            return
        try:
            self.client.table("embeddings").insert(payload).execute()
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Supabase store_embedding failed: {e}")

    def fetch_embeddings(self, user_id: str, limit: int = 100) -> list[dict[str, Any]]:
        if not self.client:
            return []
        try:
            result = self.client.table("embeddings").select("*").eq("user_id", user_id).limit(limit).execute()
            return result.data or []
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Supabase fetch_embeddings failed: {e}")
            return []

    def list_model_versions(self) -> list[dict[str, Any]]:
        if not self.client:
            return self.local_model_versions
        try:
            result = self.client.table("model_versions").select("*").order("created_at", desc=True).execute()
            return result.data or []
        except Exception:
            return self.local_model_versions

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

    def clear_history(self, user_id: str) -> None:
        if not self.client:
            self.local_interactions = {
                k: v for k, v in self.local_interactions.items() if v.user_id != user_id
            }
            return
        self.client.table("interactions").delete().eq("user_id", user_id).execute()
        self.client.table("embeddings").delete().eq("user_id", user_id).execute()
