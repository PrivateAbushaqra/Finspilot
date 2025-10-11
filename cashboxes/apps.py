from django.apps import AppConfig


class CashboxesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'cashboxes'
    verbose_name = 'الصناديق'

    def ready(self):
        import cashboxes.signals  # noqa
