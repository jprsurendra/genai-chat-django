"""H8 (no user text in logs) and rate limiter correctness."""

import pytest

from chat.utilities.log_safety import redact
from chat.utilities.ratelimit import check_rate_limit, get_client_ip


def test_redact_hides_text(settings):
    settings.LOG_USER_CONTENT = False
    out = redact("my PAN is ABCDE1234F")
    assert "ABCDE1234F" not in out
    assert out.startswith("<20 chars sha=")


def test_redact_is_stable_for_same_input(settings):
    settings.LOG_USER_CONTENT = False
    assert redact("same") == redact("same")


def test_rate_limit_counts_requests_in_same_instant(monkeypatch, settings):
    """Two requests with the same timestamp must both be counted (old code collided)."""
    from django.core.exceptions import PermissionDenied

    monkeypatch.setattr("chat.utilities.ratelimit.time.time", lambda: 1000.0)
    check_rate_limit("u1", scope="t", limit=2)
    check_rate_limit("u1", scope="t", limit=2)
    with pytest.raises(PermissionDenied):
        check_rate_limit("u1", scope="t", limit=2)


def test_rate_limit_fails_closed_without_redis(monkeypatch):
    from django.core.exceptions import PermissionDenied

    monkeypatch.setattr("chat.utilities.ratelimit.redis_client", None)
    with pytest.raises(PermissionDenied):
        check_rate_limit("u1")


class _Req:
    def __init__(self, meta):
        self.META = meta


def test_client_ip_ignores_forwarded_header_by_default(settings):
    settings.TRUST_X_FORWARDED_FOR = False
    req = _Req({"REMOTE_ADDR": "10.0.0.1", "HTTP_X_FORWARDED_FOR": "1.2.3.4"})
    assert get_client_ip(req) == "10.0.0.1"


def test_client_ip_uses_forwarded_header_behind_trusted_proxy(settings):
    settings.TRUST_X_FORWARDED_FOR = True
    req = _Req({"REMOTE_ADDR": "10.0.0.1", "HTTP_X_FORWARDED_FOR": "1.2.3.4, 10.0.0.1"})
    assert get_client_ip(req) == "1.2.3.4"
