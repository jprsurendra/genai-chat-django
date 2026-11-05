import time
import redis
import logging
from django.conf import settings
from django.core.exceptions import PermissionDenied

logger = logging.getLogger(__name__)

# ---------------------------------------------------------
# OLD IN-MEMORY LOGIC (Commented out for reference)
# ---------------------------------------------------------
# import threading
# from collections import defaultdict, deque
# _hits: dict[str, deque] = defaultdict(deque)
# _lock = threading.Lock()
# ---------------------------------------------------------

# Initialize Redis Connection
try:
    redis_client = redis.Redis(
        host=getattr(settings, "REDIS_HOST", "localhost"),
        port=getattr(settings, "REDIS_PORT", 6379),
        db=getattr(settings, "REDIS_DB", 0),
        decode_responses=True,
        socket_timeout=1.0  # Fail fast if Redis is down
    )
except Exception as e:
    logger.error(f"Redis connection failed: {e}")
    redis_client = None


def check_rate_limit(ip: str, scope: str = "chat", limit: int = None) -> None:
    """
    A thread-safe, Redis-backed sliding-window rate limiter.

    Args:
        ip (str): The client's IP address (or user ID for logged-in users).
        scope (str): The context of the request (e.g., "chat", "upload").
        limit (int, optional): The maximum number of requests allowed.
                               If not provided, it falls back to settings.CHAT_RATE_LIMIT.

    Raises:
        PermissionDenied: If the request limit is exceeded.
    """
    # 1. Determine the rate limit. If no specific limit is passed, read from settings.
    if limit is None:
        limit = getattr(settings, "CHAT_RATE_LIMIT", 20)

    # 2. Determine the time window (in seconds) from settings.
    window = getattr(settings, "RATE_WINDOW_SECONDS", 60)

    now = time.time()
    key = f"ratelimit:{scope}:{ip}"

    # If Redis is unavailable, fallback to allowing the request (fail open)
    # 🔥 SECURITY FIX (H9): Fail-Closed by default
    if redis_client is None:
        logger.error("Redis is down. Rate limiter is failing closed (blocking requests).")
        raise PermissionDenied("Service temporarily unavailable. Please try again later.")

    try:
        # Use a Redis Pipeline for atomic operations
        pipe = redis_client.pipeline()

        # 3. Remove old timestamps outside the window
        pipe.zremrangebyscore(key, 0, now - window)

        # 4. Count current requests in the window
        pipe.zcard(key)

        # 5. Add the current timestamp
        pipe.zadd(key, {str(now): now})

        # 6. Set expiry on the key to prevent memory leaks
        pipe.expire(key, window)

        results = pipe.execute()

        # The result at index 1 is the count BEFORE adding the current request
        request_count = results[1]

        # 7. Check if the number of requests has reached the limit.
        if request_count >= limit:
            raise PermissionDenied(f"Rate limit exceeded: max {limit} req / {window}s.")

    except redis.RedisError as e:
        # If Redis fails during execution, block the request (Fail-Closed)
        logger.error(f"Redis rate limit error: {e}")
        raise PermissionDenied("Service temporarily unavailable. Please try again later.")


def reset_rate_limits() -> None:
    """
    Helper function for unit tests to clear all rate limit data.
    """
    if redis_client:
        try:
            # Delete all keys matching the ratelimit pattern
            for key in redis_client.scan_iter("ratelimit:*"):
                redis_client.delete(key)
        except redis.RedisError:
            pass