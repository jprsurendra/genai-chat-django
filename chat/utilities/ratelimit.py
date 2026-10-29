import threading
import time
from collections import defaultdict, deque
from django.conf import settings
from django.core.exceptions import PermissionDenied

# Thread-safe storage for tracking requests per IP and scope
_hits: dict[str, deque] = defaultdict(deque)
_lock = threading.Lock()


def check_rate_limit(ip: str, scope: str = "chat", limit: int = None) -> None:
    """
    A thread-safe, in-memory sliding-window rate limiter.

    Args:
        ip (str): The client's IP address.
        scope (str): The context of the request (e.g., "chat", "upload").
                     Different scopes have separate limits.
        limit (int, optional): The maximum number of requests allowed.
                               If not provided, it falls back to settings.CHAT_RATE_LIMIT.

    Raises:
        PermissionDenied: If the request limit is exceeded.
    """

    # 1. Determine the rate limit. If no specific limit is passed, read from settings.
    # We use getattr() to provide a default value if the setting is missing.
    if limit is None:
        limit = getattr(settings, "CHAT_RATE_LIMIT", 20)

    # 2. Determine the time window (in seconds) from settings.
    window = getattr(settings, "RATE_WINDOW_SECONDS", 60)

    now = time.time()

    # 3. Create a unique key for the user's IP and the current scope.
    key = f"{scope}:{ip}"

    # 4. Acquire the lock to ensure thread safety
    with _lock:
        bucket = _hits[key]

        # 5. Remove timestamps that are older than the allowed time window.
        while bucket and now - bucket[0] >= window:
            bucket.popleft()

        # 6. Check if the number of requests has reached the limit.
        if len(bucket) >= limit:
            raise PermissionDenied(f"Rate limit exceeded: max {limit} req / {window}s.")

        # 7. If allowed, add the current timestamp to the bucket.
        bucket.append(now)

        # 8. Memory Cleanup: If the dictionary gets too large, remove inactive IPs.
        if len(_hits) > 1000:
            for k in [k for k, v in _hits.items() if not v or now - v[-1] >= window]:
                del _hits[k]


def reset_rate_limits() -> None:
    """
    Helper function for unit tests to clear all rate limit data.
    """
    with _lock:
        _hits.clear()