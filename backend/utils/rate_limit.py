import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

from backend.config import RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW_SECONDS

# client IP -> times of its recent requests. Kept in memory, so it resets when the server restarts.
_recent: dict[str, deque[float]] = defaultdict(deque)


def check_rate_limit(request: Request) -> None:
    """FastAPI dependency: stop a client that sends too many requests in a short time."""
    client = request.client.host if request.client else "unknown"
    now = time.monotonic()
    times = _recent[client]
    while times and now - times[0] > RATE_LIMIT_WINDOW_SECONDS:
        times.popleft()  # forget requests outside the window
    if len(times) >= RATE_LIMIT_REQUESTS:
        raise HTTPException(status_code=429, detail="יותר מדי בקשות. נסו שוב בעוד דקה.")
    times.append(now)
