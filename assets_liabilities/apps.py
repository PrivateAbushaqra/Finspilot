from django.apps import AppConfig


class AssetsLiabilitiesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'assets_liabilities'

    def ready(self):
        import assets_liabilities.signals  # noqa
