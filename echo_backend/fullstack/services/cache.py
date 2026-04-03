from __future__ import annotations

from cachetools import TTLCache


class ResponseCache:
    def __init__(self, ttl_seconds: int = 300, max_size: int = 256):
        self.cache = TTLCache(maxsize=max_size, ttl=ttl_seconds)

    def get(self, key: str):
        return self.cache.get(key)

    def set(self, key: str, value):
        self.cache[key] = value
