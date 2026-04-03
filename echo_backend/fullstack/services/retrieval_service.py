from __future__ import annotations

from .reward_service import cosine_similarity


class RetrievalService:
    def __init__(self, repository):
        self.repository = repository

    def retrieve_successful_examples(self, user_id: str, query: str, top_k: int = 3) -> list[str]:
        candidates = self.repository.fetch_embeddings(user_id)
        if not candidates:
            return []
        ranked = []
        for row in candidates:
            score = cosine_similarity(query, row.get("source_text", ""))
            ranked.append((score, row.get("source_text", "")))
        ranked.sort(key=lambda item: item[0], reverse=True)
        return [item[1] for item in ranked[:top_k]]
