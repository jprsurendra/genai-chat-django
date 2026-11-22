"""
Django settings for config project.
Default settings only. Custom settings are in local_settings.py
"""

import os
import sys
import warnings
from datetime import timedelta
from pathlib import Path

from django.utils.csp import CSP
from dotenv import load_dotenv

# Load environment variables at the very beginning
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# ==========================================
# IMPORT CUSTOM LOCAL SETTINGS FIRST
# ==========================================
# We add the root directory (where manage.py is) to Python's path
# so we can import local_settings from outside the config folder.
sys.path.insert(0, str(BASE_DIR))

try:
    from local_settings import *
except ImportError:
    # local_settings.py is git-ignored. Fall back to the committed example so a fresh
    # clone (or CI) can start; all secrets still come from environment variables.
    warnings.warn("local_settings.py not found; using local_settings_example.py", stacklevel=1)
    from local_settings_example import *

BASE_DIR = Path(__file__).resolve().parent.parent
# ==========================================
# DEFAULT DJANGO SETTINGS
# ==========================================
# INSTALLED_APPS = [
#     "django.contrib.contenttypes",
#     "django.contrib.staticfiles",
#     "rest_framework",
#     "chat",
# ]
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",  # refresh-token rotation + logout
    "accounts",  # Auth API
    "chat",  # Chat & RAG API
    "web_ui",  # Frontend UI (New)
]

# MIDDLEWARE = [
#     "django.middleware.security.SecurityMiddleware",
#     "whitenoise.middleware.WhiteNoiseMiddleware",
#     "django.middleware.common.CommonMiddleware",
# ]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",  # <-- required
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",  # <-- required
    "django.contrib.messages.middleware.MessageMiddleware",  # <-- required
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.middleware.csp.ContentSecurityPolicyMiddleware",
]


ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",  # <--  Required
                "django.contrib.auth.context_processors.auth",  # <--  Required
                "django.contrib.messages.context_processors.messages",  # <-- Required
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# REST_FRAMEWORK = {
#     "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
#     "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
#     "DEFAULT_AUTHENTICATION_CLASSES": [],
#     "DEFAULT_PERMISSION_CLASSES": [],
#     "UNAUTHENTICATED_USER": None,
# }
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "UNAUTHENTICATED_USER": None,
}

# ==========================================
# JWT SETTINGS (M5 / R3)
# ==========================================
# The frontend refreshes the access token automatically (see static/web_ui/app.js),
# so a short access lifetime does not log the user out.
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(os.getenv("JWT_ACCESS_MINUTES", "30"))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(os.getenv("JWT_REFRESH_DAYS", "7"))),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
}

# ==========================================
# PASSWORD VALIDATION (M5)
# ==========================================
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ==========================================
# SECURITY HEADERS (M5)
# ==========================================
SECURE_CONTENT_TYPE_NOSNIFF = True

# Content-Security-Policy (Django built-in). Everything is served from our own origin:
# vendor libraries live in static/vendor/, and there are no inline scripts or styles.
# This is the main defence if an XSS bug ever slips through (the JWT is in localStorage).
SECURE_CSP = {
    "default-src": [CSP.SELF],
    "script-src": [CSP.SELF],
    "style-src": [CSP.SELF],
    "img-src": [CSP.SELF, "data:", "blob:"],
    "font-src": [CSP.SELF],
    "connect-src": [CSP.SELF],
    "object-src": [CSP.NONE],
    "base-uri": [CSP.SELF],
    "form-action": [CSP.SELF],
    "frame-ancestors": [CSP.NONE],
}
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    # Turn these on once the app is served over HTTPS (usually behind Nginx).
    SECURE_SSL_REDIRECT = os.getenv("DJANGO_SECURE_SSL_REDIRECT", "0") == "1"
    SECURE_HSTS_SECONDS = int(os.getenv("DJANGO_SECURE_HSTS_SECONDS", "0"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = SECURE_HSTS_SECONDS > 0
    # Only enable after the domain is submitted to hstspreload.org (hard to undo).
    SECURE_HSTS_PRELOAD = os.getenv("DJANGO_SECURE_HSTS_PRELOAD", "0") == "1"
    if os.getenv("TRUST_X_FORWARDED_FOR", "0") == "1":
        SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# ==========================================
# LOGGING PRIVACY (H8)
# ==========================================
# User text (prompts, queries, tool arguments) is NOT written to logs unless this is on.
# Never enable it in production.
LOG_USER_CONTENT = DEBUG and os.getenv("LOG_USER_CONTENT", "0") == "1"

# ==========================================
# AUTH RATE LIMIT (R11) - per client IP, for login / register / refresh
# ==========================================
AUTH_RATE_LIMIT = int(os.getenv("AUTH_RATE_LIMIT", "10"))

# ==========================================
# STORAGE SETTINGS (Depends on DEBUG from local_settings)
# ==========================================
# Now Python knows what DEBUG is because we imported local_settings above.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG  # DEBUG is successfully imported
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        )
    },
}
STATIC_ROOT = BASE_DIR / "staticfiles"

# Media files (User uploaded files)
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"


# ==========================================
# LOGGING CONFIGURATION
# ==========================================
from .logger_config import LOGGING  # noqa: F401  (read by Django from the settings module)
