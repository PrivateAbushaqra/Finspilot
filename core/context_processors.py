from .models import CompanySettings
from settings.models import Currency, CompanySettings as SettingsCompanySettings
from django.utils import translation


def company_settings(request):
    """إضافة إعدادات الشركة إلى السياق"""
    return {
        'company_settings': CompanySettings.get_settings()
    }


def currency_context(request):
    """إضافة معلومات العملة إلى السياق"""
    base_currency = Currency.get_base_currency()
    settings_company = SettingsCompanySettings.objects.first()
    
    return {
        'base_currency': base_currency,
        'settings_company': settings_company,
        'show_currency_symbol': settings_company.show_currency_symbol if settings_company else True,
    }

# دالة company_context المطلوبة في الإعدادات
def company_context(request):
    """إرجاع سياق فارغ أو معلومات الشركة إذا لزم الأمر"""
    return {}

# دالة notifications_context المطلوبة في الإعدادات
def notifications_context(request):
    """إرجاع سياق فارغ أو إشعارات إذا لزم الأمر"""
    return {}

def language_context(request):
    """إضافة اللغة الحالية إلى السياق"""
    return {
        'current_language': translation.get_language(),
        'LANGUAGE_CODE': translation.get_language(),
    }
