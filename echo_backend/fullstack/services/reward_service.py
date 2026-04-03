from __future__ import annotations

from collections import Counter
from math import log

from rl.state import StatePreprocessor


def cosine_similarity(text_a: str, text_b: str) -> float:
    preprocessor = StatePreprocessor()
    a = preprocessor._hash_embedding(text_a)
    b = preprocessor._hash_embedding(text_b)
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def repetition_penalty(response: str, ngram: int = 3) -> float:
    tokens = response.lower().split()
    if len(tokens) < ngram:
        return 0.0
    grams = [tuple(tokens[index : index + ngram]) for index in range(len(tokens) - ngram + 1)]
    counts = Counter(grams)
    repeats = sum(count - 1 for count in counts.values() if count > 1)
    return min(1.0, repeats / max(1, len(grams)))


def confusion_penalty(response: str) -> float:
    markers = ["i don't know", "maybe", "unclear", "not sure", "possibly"]
    return min(1.0, sum(0.15 for marker in markers if marker in response.lower()))


def entropy_penalty(response: str) -> float:
    tokens = response.lower().split()
    if not tokens:
        return 0.0
    counts = Counter(tokens)
    total = len(tokens)
    entropy = -sum((count / total) * log(count / total) for count in counts.values())
    return 0.0 if entropy > 1.5 else 0.2


def feedback_reward(vote: str, tags: list[str]) -> float:
    base = 1.0 if vote == "up" else -1.0
    tag_bonus = 0.2 * sum(1 for tag in tags if tag in {"helpful", "supportive", "clear"})
    tag_penalty = 0.2 * sum(1 for tag in tags if tag in {"confusing", "too_long", "irrelevant"})
    return base + tag_bonus - tag_penalty
