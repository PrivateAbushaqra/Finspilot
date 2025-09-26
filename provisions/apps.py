from django.apps import AppConfig


class ProvisionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'provisions'

    def ready(self):
        import provisions.signals  # noqa
