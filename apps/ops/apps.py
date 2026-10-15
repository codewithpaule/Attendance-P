from django.apps import AppConfig


class OpsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ops"

    def ready(self):
        # Import jobs module to register jobs
        import apps.ops.jobs  # noqa: F401
