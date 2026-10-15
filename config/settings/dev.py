from .base import *  # noqa: F401, F405

DEBUG = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

LOGGING["loggers"]["django"]["level"] = "DEBUG"
