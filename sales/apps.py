from django.apps import AppConfig


class SalesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'sales'
    verbose_name = 'المبيعات'
    
    def ready(self):
        """تحميل الـ signals عند بدء التطبيق"""
        import sales.signals
