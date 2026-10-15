from .base import *  # noqa: F401, F405

DEBUG = False

# Simple database - use SQLite for now to get Vercel working
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# ALLOWED_HOSTS - accept all for now
ALLOWED_HOSTS = ["*"]

# WebAuthn - make optional for now
WEBAUTHN_RP_ID = env.str("WEBAUTHN_RP_ID", default="localhost")
WEBAUTHN_RP_NAME = env.str("WEBAUTHN_RP_NAME", default="POMSOM")
WEBAUTHN_ORIGIN = env.str("WEBAUTHN_ORIGIN", default="http://localhost:8000")
WEBAUTHN_ENABLED = False  # Disable for now

# Vercel detection
BEHIND_VERCEL = env.bool("BEHIND_VERCEL", default=True)

# Security settings - relax for now
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_TRUSTED_ORIGINS = ["*"]
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

# Proxy settings
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Simple cache
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# Logging - simple stdout
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}

# Job configuration - make optional
JOBS_SECRET = env.str("JOBS_SECRET", default="dev-secret")
JOB_TIME_BUDGET_SECONDS = env.int("JOB_TIME_BUDGET_SECONDS", default=25)

# Backup configuration - make optional
BACKUP_AGE_RECIPIENT = env.str("BACKUP_AGE_RECIPIENT", default="")

# Attendance settings with defaults
QR_TOKEN_MAX_AGE_SECONDS = env.int("QR_TOKEN_MAX_AGE_SECONDS", default=20)
CHECKIN_WINDOW_MINUTES = env.int("CHECKIN_WINDOW_MINUTES", default=15)
HEADCOUNT_TOLERANCE = env.int("HEADCOUNT_TOLERANCE", default=2)
SPOT_CHECK_COUNT = env.int("SPOT_CHECK_COUNT", default=3)
LOCATION_RETENTION_DAYS = env.int("LOCATION_RETENTION_DAYS", default=180)
LOW_ACCURACY_M = env.int("LOW_ACCURACY_M", default=100)
NEW_CREDENTIAL_FLAG_HOURS = env.int("NEW_CREDENTIAL_FLAG_HOURS", default=24)
ENABLE_NETWORK_BURST_FLAG = env.bool("ENABLE_NETWORK_BURST_FLAG", default=False)

# Email settings - make optional
RESEND_API_KEY = env.str("RESEND_API_KEY", default="")
RESEND_FROM_EMAIL = env.str("RESEND_FROM_EMAIL", default="")
EMAIL_DAILY_BUDGET = env.int("EMAIL_DAILY_BUDGET", default=90)
