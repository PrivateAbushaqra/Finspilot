from django import template
from django.conf import settings

register = template.Library()


@register.simple_tag
def get_session_settings():
    """الحصول على إعدادات الجلسة من إعدادات الشركة"""
    try:
        from settings.models import CompanySettings
        company_settings = CompanySettings.objects.first()
        
        if company_settings:
            return {
                'timeout_minutes': company_settings.session_timeout_minutes,
                'enable_timeout': company_settings.enable_session_timeout,
                'logout_on_browser_close': company_settings.logout_on_browser_close,
            }
        else:
            # القيم الافتراضية إذا لم توجد إعدادات الشركة
            return {
                'timeout_minutes': 30,
                'enable_timeout': True,
                'logout_on_browser_close': True,
            }
    except Exception:
        # في حالة حدوث خطأ، إرجاع القيم الافتراضية
        return {
            'timeout_minutes': 30,
            'enable_timeout': True,
            'logout_on_browser_close': True,
        }


@register.filter
def company_setting(key, default=None):
    """فلتر للحصول على إعدادات الشركة"""
    try:
        from settings.models import CompanySettings
        company_settings = CompanySettings.objects.first()
        
        if company_settings:
            return getattr(company_settings, key, default)
        return default
    except Exception:
        return default
