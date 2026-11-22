"""
Shared fixtures for the test-suite.

- Redis is replaced by an in-memory fakeredis instance, so rate limits work without a server.
- The LLM service is replaced by a fake, so no Ollama / OpenAI / ChromaDB is needed.
"""

import fakeredis
import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

# Fake credentials for tests only. Strong enough to pass AUTH_PASSWORD_VALIDATORS.
TEST_PASSWORD = "S3cure-pass-123"  # allow-listed in .gitleaks.toml
OTHER_TEST_PASSWORD = "S3cure-pass-456"  # allow-listed in .gitleaks.toml


@pytest.fixture(autouse=True)
def fake_redis(monkeypatch):
    client = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("chat.utilities.ratelimit.redis_client", client)
    return client


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"
    return settings.MEDIA_ROOT


class FakeLLMService:
    """Records what the views pass in, and returns canned answers."""

    def __init__(self):
        self.calls = []
        self.upload_result = ("Successfully uploaded and embedded 3 chunks from test.txt.", 3)
        self.upload_error = None

    async def generate_reply(self, message, history, user_id, use_fast=False):
        self.calls.append({"message": message, "history": history, "user_id": user_id})
        return "fake reply"

    async def stream_reply(self, message, history, user_id, use_fast=False):
        self.calls.append({"message": message, "history": history, "user_id": user_id})
        for part in ("fake ", "stream"):
            yield part

    def upload_document(self, file_path, original_filename, user_id):
        if self.upload_error:
            raise self.upload_error
        return self.upload_result

    def clear_session(self, session_id):
        pass


@pytest.fixture
def fake_llm(monkeypatch):
    service = FakeLLMService()
    monkeypatch.setattr("chat.views.chat_api_views.get_llm_service", lambda: service)
    return service


@pytest.fixture
def user(db):
    return User.objects.create_user(username="alice", email="alice@example.com", password=TEST_PASSWORD)


@pytest.fixture
def other_user(db):
    return User.objects.create_user(username="bob", email="bob@example.com", password=OTHER_TEST_PASSWORD)


def auth_client(u) -> APIClient:
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(u).access_token}")
    return client


@pytest.fixture
def client_a(user):
    return auth_client(user)


@pytest.fixture
def client_b(other_user):
    return auth_client(other_user)
