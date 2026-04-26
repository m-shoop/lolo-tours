"""In-process rate limiter keyed by client IP.

Sufficient for a single-instance deployment. If the app is ever scaled out,
swap with a Redis-backed limiter — this module is the only thing to replace.
"""
import time
from collections import defaultdict, deque
from threading import Lock


class RateLimiter:
    def __init__(self, *, max_per_minute: int) -> None:
        self.max = max_per_minute
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str) -> bool:
        """Return True if allowed, False if rate-limited."""
        now = time.time()
        cutoff = now - 60.0
        with self._lock:
            q = self._hits[key]
            while q and q[0] < cutoff:
                q.popleft()
            if len(q) >= self.max:
                return False
            q.append(now)
            return True
