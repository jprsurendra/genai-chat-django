"""R3 (refresh), M5 (password validation), R11 (auth rate limit), logout."""

import pytest
from rest_framework.test import APIClient

from tests.conftest import TEST_PASSWORD

pytestmark = pytest.mark.django_db


def _register(client, password=TEST_PASSWORD, username="carol", email="carol@example.com"):
    return client.post(
        "/api/auth/register",
        {"username": username, "email": email, "password": password, "confirm_password": password},
        format="json",
    )


def _login(client, username="alice", password=TEST_PASSWORD):
    return client.post("/api/auth/login", {"username": username, "password": password}, format="json")


def test_register_rejects_weak_password():
    resp = _register(APIClient(), password="12345678")
    assert resp.status_code == 400
    assert "password" in resp.data["error"].lower()


def test_register_rejects_bad_email():
    resp = _register(APIClient(), email="not-an-email")
    assert resp.status_code == 400


def test_register_with_strong_password_works():
    assert _register(APIClient()).status_code == 201


def test_refresh_gives_new_access_token(user):
    client = APIClient()
    tokens = _login(client).data
    resp = client.post("/api/auth/refresh", {"refresh": tokens["refresh"]}, format="json")
    assert resp.status_code == 200
    assert resp.data["access"]
    assert resp.data["refresh"] != tokens["refresh"]  # rotated

    # the old refresh token is blacklisted after rotation
    again = client.post("/api/auth/refresh", {"refresh": tokens["refresh"]}, format="json")
    assert again.status_code == 401


def test_logout_blacklists_refresh_token(user):
    client = APIClient()
    tokens = _login(client).data
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    assert client.post("/api/auth/logout", {"refresh": tokens["refresh"]}, format="json").status_code == 200
    client.credentials()
    assert client.post("/api/auth/refresh", {"refresh": tokens["refresh"]}, format="json").status_code == 401


def test_login_is_rate_limited_per_ip(settings, user):
    settings.AUTH_RATE_LIMIT = 3
    client = APIClient()
    codes = [_login(client, password="wrong").status_code for _ in range(4)]
    assert codes == [401, 401, 401, 429]


def test_register_is_rate_limited_per_ip(settings):
    settings.AUTH_RATE_LIMIT = 2
    client = APIClient()
    codes = [_register(client, username=f"u{i}", email=f"u{i}@example.com").status_code for i in range(3)]
    assert codes == [201, 201, 429]


def test_jwt_lifetimes_are_configured(settings):
    assert settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds() >= 15 * 60
    assert settings.SIMPLE_JWT["ROTATE_REFRESH_TOKENS"] is True
