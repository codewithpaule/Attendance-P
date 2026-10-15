from .base import *  # noqa: F401, F405

DEBUG = False

# Database configuration for Neon with transaction pooling
# If DATABASE_URL is set, use it. Otherwise, use individual components.
if DATABASE_URL := env.str("DATABASE_URL", default=None):
    import dj_database_url
    DATABASES = {
        "default": dj_database_url.config(
            DATABASE_URL,
            conn_max_age=0,
            ssl_require=True,
            conn_health_checks=True,
        )
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env.str("DB_NAME", "pomsom"),
            "USER": env.str("DB_USER", "pomsom"),
            "PASSWORD": env.str("DB_PASSWORD"),
            "HOST": env.str("DB_HOST", "localhost"),
            "PORT": env.str("DB_PORT", "5432"),
            "CONN_MAX_AGE": 0,
            "OPTIONS": {
                "sslmode": "require",
                "connect_timeout": 10,
            },
        }
    }

# Direct connection for migrations and backups (never used by running app)
DATABASE_URL_DIRECT = env.str("DATABASE_URL_DIRECT", default=None)

# ALLOWED_HOSTS - accept Vercel URLs and custom domain
# In production, set this explicitly. For now, accept all to get it working.
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["*"])

# WebAuthn configuration - fail fast if missing or invalid
WEBAUTHN_RP_ID = env.str("WEBAUTHN_RP_ID")
WEBAUTHN_RP_NAME = env.str("WEBAUTHN_RP_NAME")
WEBAUTHN_ORIGIN = env.str("WEBAUTHN_ORIGIN")

if not all([WEBAUTHN_RP_ID, WEBAUTHN_RP_NAME, WEBAUTHN_ORIGIN]):
    raise ValueError("WebAuthn environment variables (WEBAUTHN_RP_ID, WEBAUTHN_RP_NAME, WEBAUTHN_ORIGIN) are required in production")

if not WEBAUTHN_ORIGIN.startswith("https://"):
    raise ValueError("WEBAUTHN_ORIGIN must use HTTPS in production")

# Disable WebAuthn on preview deployments
IS_PREVIEW = env.bool("IS_PREVIEW", default=False)
WEBAUTHN_ENABLED = not IS_PREVIEW

# Vercel detection
BEHIND_VERCEL = env.bool("BEHIND_VERCEL", default=True)

# Security settings
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

# SSL redirect - exempt health endpoints
SECURE_SSL_REDIRECT = True
SECURE_SSL_REDIRECT_EXEMPT = [r"^/healthz$", r"^/readyz$"]

# HSTS - start with short value, document how to raise
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=86400)  # 1 day initially
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True)
SECURE_HSTS_PRELOAD = env.bool("SECURE_HSTS_PRELOAD", default=False)

# Proxy settings
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Caching - use DatabaseCache for throttling (shared across instances)
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "cache_table",
    }
}

# Logging - JSON to stdout
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "apps": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# Job configuration
JOBS_SECRET = env.str("JOBS_SECRET")
JOB_TIME_BUDGET_SECONDS = env.int("JOB_TIME_BUDGET_SECONDS", default=25)

# Backup configuration
BACKUP_AGE_RECIPIENT = env.str("BACKUP_AGE_RECIPIENT")

# Attendance settings
QR_TOKEN_MAX_AGE_SECONDS = env.int("QR_TOKEN_MAX_AGE_SECONDS", default=20)
CHECKIN_WINDOW_MINUTES = env.int("CHECKIN_WINDOW_MINUTES", default=15)
HEADCOUNT_TOLERANCE = env.int("HEADCOUNT_TOLERANCE", default=2)
SPOT_CHECK_COUNT = env.int("SPOT_CHECK_COUNT", default=3)
LOCATION_RETENTION_DAYS = env.int("LOCATION_RETENTION_DAYS", default=180)
LOW_ACCURACY_M = env.int("LOW_ACCURACY_M", default=100)
NEW_CREDENTIAL_FLAG_HOURS = env.int("NEW_CREDENTIAL_FLAG_HOURS", default=24)
ENABLE_NETWORK_BURST_FLAG = env.bool("ENABLE_NETWORK_BURST_FLAG", default=False)

# Email settings
RESEND_API_KEY = env.str("RESEND_API_KEY", default="")
RESEND_FROM_EMAIL = env.str("RESEND_FROM_EMAIL", default="")
EMAIL_DAILY_BUDGET = env.int("EMAIL_DAILY_BUDGET", default=90)
