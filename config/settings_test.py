"""
Settings for the automated tests (pytest).

- SQLite in memory instead of MySQL, so tests need no database server.
- Ollama as the provider, so no API key is needed; the LLM service is mocked in tests anyway.
- Redis is replaced by fakeredis in tests/conftest.py.
"""
import os

# Must be set BEFORE settings are imported; load_dotenv() does not override existing values.
os.environ["LLM_PROVIDER"] = "ollama"
os.environ["DJANGO_DEBUG"] = "1"
os.environ.setdefault("DJANGO_SECRET_KEY", "test-only-secret-key-not-for-production-use-0123456789")

from .settings import *  # noqa: E402,F401,F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]  # fast, tests only
LOG_USER_CONTENT = False
LOGGING = {"version": 1, "disable_existing_loggers": False}
