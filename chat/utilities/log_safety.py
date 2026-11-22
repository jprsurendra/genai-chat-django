"""
Helpers to keep user content out of the logs (review finding H8).

Logs are copied to files, shipped to log services and read by many people, so they must
not contain what users type. Use `redact()` wherever a log line would include a prompt,
a search query, a tool argument or a document excerpt.
"""

import hashlib

from django.conf import settings


def redact(text: object) -> str:
    """
    Returns a privacy-safe description of `text` for logging.

    By default only the length and a short hash are logged. The hash lets you match
    two log lines about the same input without revealing it. Set LOG_USER_CONTENT=1
    (only works when DEBUG is on) to log the real text during local debugging.
    """
    if text is None:
        return "<none>"
    text = str(text)
    if getattr(settings, "LOG_USER_CONTENT", False):
        return repr(text[:500])
    digest = hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()[:10]
    return f"<{len(text)} chars sha={digest}>"
