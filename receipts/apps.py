from django.apps import AppConfig


class ReceiptsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'receipts'
    verbose_name = 'سندات القبض'
    
    def ready(self):
        """تحميل الإشارات عند بدء التطبيق"""
        import receipts.signals
