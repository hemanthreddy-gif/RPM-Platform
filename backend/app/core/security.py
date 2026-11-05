"""Small, deterministic in-process protections for the synthetic demo API."""

from collections import defaultdict, deque
from time import monotonic


class SlidingWindowRateLimiter:
    """Bound one endpoint/source pair without retaining request content or credentials."""

    def __init__(self) -> None:
        self._events: dict[tuple[str, str], deque[float]] = defaultdict(deque)

    def allowed(self, *, scope: str, source: str, limit: int, window_seconds: int) -> bool:
        now = monotonic()
        events = self._events[(scope, source)]
        cutoff = now - window_seconds
        while events and events[0] <= cutoff:
            events.popleft()
        if len(events) >= limit:
            return False
        events.append(now)
        return True
