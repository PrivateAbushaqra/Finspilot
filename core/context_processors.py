from .models import CompanySettings
from settings.models import Currency, CompanySettings as SettingsCompanySettings


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
