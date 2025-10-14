from django.apps import AppConfig


class CustomersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'customers'
    verbose_name = 'العملاء والموردون'
    
    def ready(self):
        """استيراد الإشارات عند بدء التطبيق"""
        import customers.signals
