"""Abuse and spend protection for the public analyst endpoint (every call costs real money).

Four independent guards: requests per minute per client, requests per day per client, a global daily spend budget,
and a cap on analyses running at once. State lives in this process, which is correct for one API instance.
ponytail: move the counters to Postgres or Redis before running more than one instance."""

import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

from app.core.config import settings

UNKNOWN_COST_USD = 0.25  # charged when a model's price is not in the table, so the budget still protects us


class Limiter:
    def __init__(self, per_minute: int, per_day: int, daily_budget_usd: float, max_concurrent: int, clock=time.time):
        self.per_minute, self.per_day, self.budget, self.clock = per_minute, per_day, daily_budget_usd, clock
        self._lock = threading.Lock()
        self._recent: dict[str, deque] = defaultdict(deque)
        self._today = self._day()
        self._day_counts: dict[str, int] = defaultdict(int)
        self._spent = 0.0
        self._free_slots = max_concurrent

    def _day(self) -> int:
        return int(self.clock() // 86400)  # UTC day

    def _roll_day(self) -> None:
        if self._day() != self._today:
            self._today, self._day_counts, self._spent = self._day(), defaultdict(int), 0.0

    def acquire(self, client: str) -> None:
        """Admit one analysis or raise HTTPException (429 for the client's own limits, 503 for global ones)."""
        with self._lock:
            self._roll_day()
            now = self.clock()
            recent = self._recent[client]
            while recent and now - recent[0] >= 60:
                recent.popleft()
            if self._spent >= self.budget:
                raise HTTPException(503, "The demo's daily AI budget has been used up. The dashboards still work; try the analyst again tomorrow (UTC).")
            if len(recent) >= self.per_minute:
                wait = max(1, int(60 - (now - recent[0])) + 1)
                raise HTTPException(429, f"Too many questions. Try again in {wait}s.", headers={"Retry-After": str(wait)})
            if self._day_counts[client] >= self.per_day:
                raise HTTPException(429, "Daily question limit reached for this visitor. Try again tomorrow.", headers={"Retry-After": "3600"})
            if self._free_slots <= 0:
                raise HTTPException(503, "The analyst is busy answering other questions. Try again in a few seconds.", headers={"Retry-After": "5"})
            self._free_slots -= 1
            recent.append(now)
            self._day_counts[client] += 1

    def release(self, cost_usd: float | None = None, charged: bool = True) -> None:
        """End an analysis. A finished run is charged its cost (a conservative default if unpriced)."""
        with self._lock:
            self._free_slots += 1
            if charged:
                self._spent += UNKNOWN_COST_USD if cost_usd is None else cost_usd

    @property
    def spent_today(self) -> float:
        with self._lock:
            self._roll_day()
            return round(self._spent, 4)


limiter = Limiter(settings.analyst_rate_per_minute, settings.analyst_daily_per_client, settings.analyst_daily_budget_usd,
                  settings.analyst_max_concurrent)


def get_limiter() -> Limiter:
    return limiter


def client_id(request: Request) -> str:
    """The caller. Behind a trusted proxy the real address is the first X-Forwarded-For entry."""
    if settings.trust_proxy:
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
