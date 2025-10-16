from django.apps import AppConfig


class BanksConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'banks'
    verbose_name = 'الحسابات البنكية'
    
    def ready(self):
        """تحميل الإشارات عند بدء التطبيق"""
        try:
            import banks.signals
        except ImportError:
            pass
