import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # python-dotenv is optional
    load_dotenv = None


BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR.parent / "frontend"
FRONTEND_BUILD_DIR = FRONTEND_DIR / "dist"
# DRIVEWISE_ENV_FILE picks another env file, e.g. ".env.local" for the local-testing profile
# (see .env.local.example). Relative paths are resolved from backend/.
ENV_FILE = BASE_DIR / os.environ.get("DRIVEWISE_ENV_FILE", ".env")
if load_dotenv:
    load_dotenv(ENV_FILE)
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "local-development-only-not-for-production")
DEBUG = os.environ.get("DJANGO_DEBUG", "true").lower() == "true"
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")
    if host.strip()
]
# Full origins (with https://) allowed to submit forms, e.g. the admin login when
# served over HTTPS on PythonAnywhere: "https://<username>.pythonanywhere.com".
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.api",
    "apps.knowledge",
    "apps.monitoring",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

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

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        # The local-testing profile uses its own file so offline embeddings never mix with Gemini ones.
        "NAME": BASE_DIR / os.environ.get("SQLITE_PATH", "db.sqlite3"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = (
    [("frontend", FRONTEND_BUILD_DIR)]
    if FRONTEND_BUILD_DIR.is_dir()
    else []
)
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- RAG chatbot -----------------------------------------------------------
# Providers: RAG_EMBEDDER = "gemini" | "hashing" (offline, no key);
# RAG_LLM = "gemini" | "claude_code" (local testing through the Claude Code CLI, no API key).
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
RAG_EMBEDDER = os.environ.get("RAG_EMBEDDER", "gemini")
RAG_LLM = os.environ.get("RAG_LLM", "gemini")
RAG_EMBEDDING_MODEL = os.environ.get("RAG_EMBEDDING_MODEL", "gemini-embedding-001")
RAG_EMBEDDING_DIMENSIONS = int(os.environ.get("RAG_EMBEDDING_DIMENSIONS", "768"))
RAG_CHAT_MODEL = os.environ.get("RAG_CHAT_MODEL", "gemini-3.1-flash-lite")
CLAUDE_CODE_BIN = os.environ.get("CLAUDE_CODE_BIN", "claude")
CLAUDE_CODE_MODEL = os.environ.get("CLAUDE_CODE_MODEL", "")  # Blank uses your Claude Code default.
CLAUDE_CODE_TIMEOUT_SECONDS = int(os.environ.get("CLAUDE_CODE_TIMEOUT_SECONDS", "120"))
RAG_TOP_K = int(os.environ.get("RAG_TOP_K", "5"))
# Passages scoring below this cosine similarity are ignored. If nothing is left,
# the bot says it couldn't find the answer instead of guessing (US 3).
RAG_MIN_SCORE = float(os.environ.get("RAG_MIN_SCORE", "0.55"))
KNOWLEDGE_DATA_DIR = BASE_DIR / "data" / "manuals"
KNOWLEDGE_ALLOWED_HOSTS = tuple(
    host.strip()
    for host in os.environ.get("KNOWLEDGE_ALLOWED_HOSTS", "").split(",")
    if host.strip()
)

# Chat questions allowed per visitor per window; 0 disables the limit.
CHAT_RATE_LIMIT = int(os.environ.get("CHAT_RATE_LIMIT", "10"))
CHAT_RATE_LIMIT_WINDOW_SECONDS = int(os.environ.get("CHAT_RATE_LIMIT_WINDOW_SECONDS", "60"))

# Zero disables a warning threshold while collecting a performance baseline.
PERFORMANCE_LATENCY_WARNING_MS = float(os.environ.get("PERFORMANCE_LATENCY_WARNING_MS", "0"))
PERFORMANCE_FAILURE_WARNING_PERCENT = float(os.environ.get("PERFORMANCE_FAILURE_WARNING_PERCENT", "0"))
