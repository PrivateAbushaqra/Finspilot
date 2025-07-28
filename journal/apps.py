from django.apps import AppConfig


class JournalConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'journal'
    verbose_name = 'القيود المحاسبية'
    
    def ready(self):
        """تسجيل الإشارات عند بدء التطبيق"""
        import journal.signals
