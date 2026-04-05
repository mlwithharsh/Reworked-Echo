import json
import logging
import hashlib
from typing import Dict, Optional

class CacheManager:
    """Production Response Caching (LRU-inspired)."""
    def __init__(self, size: int = 100):
        self.size = size
        self.cache: Dict[str, dict] = {}
        self.logger = logging.getLogger("HELIX.Cache")

    def _get_hash(self, text: str, personality: str) -> str:
        key = f"{text.strip().lower()}:{personality.lower()}"
        return hashlib.md5(key.encode()).hexdigest()

    def get(self, text: str, personality: str) -> Optional[str]:
        h = self._get_hash(text, personality)
        if h in self.cache:
            self.logger.info(f"CACHE HIT: {text[:20]}...")
            return self.cache[h]['response']
        return None

    def set(self, text: str, personality: str, response: str):
        h = self._get_hash(text, personality)
        if len(self.cache) >= self.size:
            # Simple eviction
            first_key = next(iter(self.cache))
            del self.cache[first_key]
        
        self.cache[h] = {'response': response, 'timestamp': None}
        self.logger.info(f"CACHE STORED: {text[:20]}...")

# Singleton
cache_manager = CacheManager()
