import time
from collections import defaultdict
from django.core.exceptions import PermissionDenied

# Configuration for the Rate Limiter
RATE_LIMIT = 20
RATE_WINDOW = 60
_hits: dict[str, list[float]] = defaultdict(list)


def check_rate_limit(ip: str) -> None:
    """
    A simple in-memory rate limiter.
    Tracks the number of requests made by an IP address within a time window.
    Raises PermissionDenied (HTTP 429) if the user exceeds 20 requests per 60 seconds.
    """
    now = time.time()
    # Filter out timestamps older than the allowed time window
    _hits[ip] = [t for t in _hits[ip] if now - t < RATE_WINDOW]

    if len(_hits[ip]) >= RATE_LIMIT:
        raise PermissionDenied(
            f"Rate limit exceeded: max {RATE_LIMIT} req / {RATE_WINDOW}s."
        )
    _hits[ip].append(now)