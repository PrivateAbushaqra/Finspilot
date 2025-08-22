from settings.models import CompanySettings, Currency

def currency_context(request):
    """إضافة العملة الأساسية إلى جميع templates"""
    try:
        company_settings = CompanySettings.objects.first()
        base_currency = Currency.get_base_currency()
        
        return {
            'base_currency': base_currency,
            'company_settings': company_settings,
        }
    except Exception:
        return {
            'base_currency': None,
            'company_settings': None,
        }
