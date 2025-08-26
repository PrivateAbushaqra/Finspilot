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


def superadmin_context(request):
    """Inject SuperadminSettings into all templates so site-wide UI settings are available."""
    try:
        # import lazily to avoid potential circular imports during startup
        from settings.models import SuperadminSettings
        superadmin_settings = SuperadminSettings.get_settings()
        return {'superadmin_settings': superadmin_settings}
    except Exception:
        return {'superadmin_settings': None}
