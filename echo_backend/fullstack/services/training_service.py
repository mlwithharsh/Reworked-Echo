from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from rl.reward import RewardFunction
from rl.state import StatePreprocessor

from .reward_service import confusion_penalty, cosine_similarity, entropy_penalty, feedback_reward, repetition_penalty


class OfflineRLHFService:
    def __init__(self, repository, model_service, adapter_root: str):
        self.repository = repository
        self.model_service = model_service
        self.adapter_root = Path(adapter_root)
        self.adapter_root.mkdir(parents=True, exist_ok=True)
        self.state_preprocessor = StatePreprocessor()
        self.reward_function = RewardFunction()

    def build_training_rows(self, limit: int = 100) -> list[dict]:
        rows = []
        for item in self.repository.fetch_training_batch(limit):
            interaction = item.get("interaction") or item.get("interactions") or {}
            feedback = item.get("feedback", item)
            input_text = interaction.get("input") or interaction.get("input_text", "")
            response_text = interaction.get("response") or interaction.get("response_text", "")
            tags = feedback.get("tags", [])
            reward = self.reward_function.compute(
                response_text=response_text,
                metrics={
                    "engagement_score": 0.4,
                    "sentiment_improvement": 0.3,
                    "task_success": 0.5,
                    "emotional_alignment": cosine_similarity(input_text, response_text),
                    "confusion_penalty": confusion_penalty(response_text) + entropy_penalty(response_text),
                    "repetition_penalty": repetition_penalty(response_text),
                    "response_clarity": 0.6,
                },
                feedback_provider=lambda _: feedback_reward(feedback.get("vote", "down"), tags),
            )
            state = self.state_preprocessor.preprocess(
                user_input=input_text,
                emotional_state_vector=[0.5, 0.5, 0.0, 0.0, 0.0],
                conversation_history=[],
                user_profile_features={},
            )
            rows.append({"state": state.to_dict(), "action": response_text, "reward": reward.to_dict(), "tags": tags})
        return rows

    async def run_batch(self, version_label: str, limit: int = 100) -> dict:
        training_rows = self.build_training_rows(limit)
        version = f"{version_label}-{uuid4().hex[:8]}"
        adapter_dir = self.adapter_root / version
        adapter_dir.mkdir(parents=True, exist_ok=True)
        (adapter_dir / "README.txt").write_text(
            "Placeholder adapter artifact. Replace with LoRA weights from the offline PPO job.\n",
            encoding="utf-8",
        )
        payload = {
            "version": version,
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "metadata": {"training_examples": len(training_rows)},
            "adapter_path": str(adapter_dir),
            "ab_bucket": "B",
        }
        self.repository.register_model_version(payload)
        await self.model_service.reload_adapter(str(adapter_dir), version)
        return payload
