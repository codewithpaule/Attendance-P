from .base import *  # noqa: F401, F405

DEBUG = False

ALLOWED_HOSTS = ["*"]

# Database configuration for Neon with transaction pooling
if DATABASE_URL := env.str("DATABASE_URL", default=None):
    import dj_database_url

    DATABASES = {
        "default": dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=0,
            ssl_require=True,
            conn_health_checks=True,
        )
    }
else:
    # Fallback to SQLite for local development if DATABASE_URL not set
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# Direct connection for migrations and backups (never used by running app)
DATABASE_URL_DIRECT = env.str("DATABASE_URL_DIRECT", default=None)
