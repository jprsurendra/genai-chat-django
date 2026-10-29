"""
Django settings for config project.
Default settings only. Custom settings are in local_settings.py
"""
from pathlib import Path
import os
import sys
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
    raise ImportError("❌ local_settings.py not found in the root directory! Please create it.")

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
    "accounts",  # Auth API
    "chat",      # Chat & RAG API
    "web_ui",    # Frontend UI (New)
]

# MIDDLEWARE = [
#     "django.middleware.security.SecurityMiddleware",
#     "whitenoise.middleware.WhiteNoiseMiddleware",
#     "django.middleware.common.CommonMiddleware",
# ]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",     # <-- required
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",  # <-- required
    "django.contrib.messages.middleware.MessageMiddleware",     # <-- required
]


ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",           # <--  Required
                "django.contrib.auth.context_processors.auth",          # <--  Required
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

STATIC_URL = 'static/'
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
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework_simplejwt.authentication.JWTAuthentication",],
    "DEFAULT_PERMISSION_CLASSES": [ "rest_framework.permissions.IsAuthenticated",],
    "UNAUTHENTICATED_USER": None,
}

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