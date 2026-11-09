from django.apps import AppConfig


class MonitoringConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.monitoring"
    verbose_name = "Performance monitoring"

    def ready(self):
        from . import checks  # noqa: F401 - register configuration checks
