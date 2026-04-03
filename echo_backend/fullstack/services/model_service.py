from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path
from typing import AsyncIterator

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from ..config import Settings
from ..schemas import PersonalityProfile
from .cache import ResponseCache
from .prompt_builder import build_conditioned_prompt


class AdaptiveInferenceService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.tokenizer = AutoTokenizer.from_pretrained(settings.model_name)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        self.model = AutoModelForCausalLM.from_pretrained(settings.model_name)
        self.model.to(self.device)
        self.model.eval()
        self.cache = ResponseCache(settings.cache_ttl_seconds)
        self.active_version = settings.active_model_version
        self.reload_lock = asyncio.Lock()

    def _cache_key(self, user_id: str, message: str, profile: PersonalityProfile) -> str:
        payload = json.dumps({"user_id": user_id, "message": message, "profile": profile.model_dump(), "version": self.active_version}, sort_keys=True)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    async def reload_adapter(self, adapter_path: str | None, model_version: str) -> None:
        async with self.reload_lock:
            self.active_version = model_version
            if adapter_path and Path(adapter_path).exists():
                self.active_version = model_version

    def choose_ab_bucket(self, versions: list[dict]) -> tuple[str, str]:
        active = [item for item in versions if item.get("status", "active") == "active"]
        if len(active) >= 2:
            chosen = active[hash(self.active_version) % len(active)]
            return chosen.get("version", self.active_version), chosen.get("ab_bucket", "A")
        return self.active_version, "A"

    def generate_response(self, prompt: str, temperature: float = 0.8, top_p: float = 0.92, max_new_tokens: int = 120) -> str:
        encoded = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512).to(self.device)
        generated = self.model.generate(
            **encoded,
            max_new_tokens=max_new_tokens,
            do_sample=True,
            temperature=temperature,
            top_p=top_p,
            pad_token_id=self.tokenizer.eos_token_id,
        )
        response = self.tokenizer.decode(generated[0][encoded["input_ids"].shape[1] :], skip_special_tokens=True).strip()
        return response or "I understand. Let me help with that."

    async def stream_response(
        self,
        user_id: str,
        message: str,
        profile: PersonalityProfile,
        history: list[dict[str, str]],
        retrieved_examples: list[str],
        versions: list[dict],
    ) -> tuple[str, dict, AsyncIterator[str]]:
        model_version, ab_bucket = self.choose_ab_bucket(versions)
        prompt = build_conditioned_prompt(message, profile, history, retrieved_examples, model_version)
        key = self._cache_key(user_id, message, profile)
        cached = self.cache.get(key)
        response = cached or self.generate_response(prompt)
        if not cached:
            self.cache.set(key, response)

        async def iterator() -> AsyncIterator[str]:
            for token in response.split():
                yield json.dumps({"type": "delta", "content": token + " "}) + "\n"
                await asyncio.sleep(0.01)

        metadata = {
            "prompt": prompt,
            "cache_hit": bool(cached),
            "temperature": 0.8,
            "top_p": 0.92,
            "ab_bucket": ab_bucket,
            "model_version": model_version,
        }
        return response, metadata, iterator()
