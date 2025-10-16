from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class PaymentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'payments'
    verbose_name = _('سندات الصرف')
    
    def ready(self):
        """تحميل الإشارات عند بدء التطبيق"""
        import payments.signals
