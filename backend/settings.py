from pathlib import Path
import os
from decouple import config, Csv
import dj_database_url


BASE_DIR = Path(__file__).resolve().parent.parent

# -------------------------
# Security
# -------------------------
SECRET_KEY = config("DJANGO_SECRET_KEY", default="insecure-key-for-dev")
DEBUG = config("DEBUG", default=False, cast=bool)

ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=lambda v: [s.strip() for s in v.split(",")]
)

CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS", default="http://localhost,https://yourapp.onrender.com", 
    cast=lambda v: [s.strip() for s in v.split(",")]
)

# -------------------------
# Security cookies (only for production)
# -------------------------
CSRF_COOKIE_HTTPONLY = False  
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"

if not DEBUG:
    # SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# -------------------------
# Installed apps
# -------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "api",
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
}

# -------------------------
# Middleware
# -------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "backend.urls"
WSGI_APPLICATION = "backend.wsgi.application"

# -------------------------
# Database
# -------------------------
from decouple import config


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    },
    'customers': {
        'ENGINE': 'djongo',
        'NAME': config('MONGODB_NAME'),
        'ENFORCE_SCHEMA': False,  # Add this for MongoDB
        'CLIENT': {
            'host': config('MONGODB_URI'),
            'username': config('MONGODB_USERNAME'),
            'password': config('MONGODB_PASSWORD'),
            'authSource': 'admin',
            'authMechanism': 'SCRAM-SHA-1',
        },
    }
}

# settings.py - add this
MIGRATION_MODULES = {
    'api': None,  # Disable migrations for the api app
}

DATABASE_ROUTERS = ['api.db_routers.AuthRouter', 'api.db_routers.CustomerRouter']


# -------------------------
# Templates
# -------------------------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# -------------------------
# Password validation
# -------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 9}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# -------------------------
# Internationalization
# -------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# -------------------------
# Static & Media files
# -------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# -------------------------
# CORS
# -------------------------
CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS", default="http://localhost:3000,http://localhost:8081,https://yourapp.onrender.com",
    cast=lambda v: [s.strip() for s in v.split(",")]
)
CORS_ALLOW_CREDENTIALS = True

# Add this to handle preflight requests properly
CORS_ALLOW_ALL_ORIGINS = DEBUG  # Only allow all in development

# -------------------------
# Logging
# -------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "file": {
            "level": "ERROR",
            "class": "logging.FileHandler",
            "filename": BASE_DIR / "logs/django.log",
        },
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["file", "console"],
            "level": "ERROR",
            "propagate": True,
        },
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
