from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import Depends, HTTPException, Request, status

from .config import Settings, get_settings


class InMemoryRateLimiter:
    def __init__(self):
        self.events: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str, limit: int, window_seconds: int) -> None:
        now = time.time()
        queue = self.events[key]
        while queue and now - queue[0] > window_seconds:
            queue.popleft()
        if len(queue) >= limit:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")
        queue.append(now)


rate_limiter = InMemoryRateLimiter()


def rate_limit_dependency(request: Request, settings: Settings = Depends(get_settings)) -> None:
    key = request.headers.get("x-api-token") or request.client.host or "anonymous"
    rate_limiter.check(key, settings.rate_limit_requests, settings.rate_limit_window_seconds)
