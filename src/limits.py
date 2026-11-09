"""Protection for the public demo: a per-visitor limit and a hard daily cap.

The Gemini free tier allows a fixed number of requests per day, so a public page must not let
one visitor (or a script) use them all. Counts live in memory: a restart resets them, which is
fine for a demo. Contract text is never stored here.
"""
import threading
import time
from collections import deque


class RateLimited(Exception):
    def __init__(self, message: str, retry_after: int):
        super().__init__(message)
        self.message = message
        self.retry_after = max(1, int(retry_after))


class DemoLimiter:
    def __init__(self, per_visitor=5, window_s=3600, daily_cap=100, clock=time.time):
        self.per_visitor, self.window_s, self.daily_cap, self.clock = per_visitor, window_s, daily_cap, clock
        self._visitors = {}
        self._day = deque()
        self._lock = threading.Lock()

    def check(self, visitor: str) -> None:
        """Count one analysis for this visitor, or raise RateLimited."""
        now = self.clock()
        with self._lock:
            while self._day and now - self._day[0] >= 86400:
                self._day.popleft()
            if len(self._day) >= self.daily_cap:
                raise RateLimited("The demo has reached its limit for today. Please try again tomorrow, "
                                  "or run Obelus yourself from the GitHub repo.", 86400 - (now - self._day[0]))
            hits = self._visitors.setdefault(visitor, deque())
            while hits and now - hits[0] >= self.window_s:
                hits.popleft()
            if len(hits) >= self.per_visitor:
                raise RateLimited(f"You have used {self.per_visitor} analyses this hour. "
                                  "Please try again later.", self.window_s - (now - hits[0]))
            hits.append(now)
            self._day.append(now)
            if len(self._visitors) > 5000:               # keep memory bounded
                for key in [k for k, v in self._visitors.items() if not v or now - v[-1] >= self.window_s]:
                    del self._visitors[key]
