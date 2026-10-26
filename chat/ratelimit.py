import time
from collections import defaultdict
from django.core.exceptions import PermissionDenied

RATE_LIMIT = 20
RATE_WINDOW = 60
_hits: dict[str, list[float]] = defaultdict(list)

def check_rate_limit(ip: str) -> None:
    now = time.time()
    _hits[ip] = [t for t in _hits[ip] if now - t < RATE_WINDOW]
    if len(_hits[ip]) >= RATE_LIMIT:
        raise PermissionDenied(
            f"Rate limit exceeded: max {RATE_LIMIT} req / {RATE_WINDOW}s."
        )
    _hits[ip].append(now)