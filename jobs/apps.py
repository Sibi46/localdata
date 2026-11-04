from django.apps import AppConfig


class JobsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'jobs'

    def ready(self):
        from . import admin_activity  # noqa: F401
        from . import production_checks  # noqa: F401
