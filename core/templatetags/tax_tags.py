from django import template
from decimal import Decimal
from settings.models import Currency, CompanySettings

register = template.Library()

@register.filter
def lookup(dictionary, key):
    """فلتر للبحث في القاموس بمفتاح"""
    if isinstance(dictionary, dict):
        return dictionary.get(key, 0)
    return 0


@register.filter
def currency_format(amount, currency=None):
    """فلتر لتنسيق المبلغ مع العملة الصحيحة"""
    if amount is None:
        amount = 0
    
    # تحويل المبلغ إلى رقم عشري
    if isinstance(amount, str):
        try:
            amount = Decimal(amount)
        except:
            amount = Decimal('0')
    elif not isinstance(amount, Decimal):
        amount = Decimal(str(amount))
    
    # تنسيق المبلغ
    formatted_amount = f"{amount:,.2f}"
    
    # الحصول على العملة
    if currency:
        # إذا تم تمرير عملة محددة
        if hasattr(currency, 'symbol') and currency.symbol:
            return f"{formatted_amount} {currency.symbol}"
        elif hasattr(currency, 'code'):
            return f"{formatted_amount} {currency.code}"
    
    # إذا لم تُمرر عملة، استخدم العملة الأساسية
    try:
        company_settings = CompanySettings.objects.first()
        if company_settings and company_settings.base_currency:
            base_currency = company_settings.base_currency
            if base_currency.symbol:
                return f"{formatted_amount} {base_currency.symbol}"
            return f"{formatted_amount} {base_currency.code}"
    except:
        pass
    
    # إذا لم نجد أي عملة، أرجع المبلغ فقط
    return formatted_amount


@register.filter
def get_currency_symbol(currency=None):
    """فلتر للحصول على رمز العملة فقط"""
    if currency:
        if hasattr(currency, 'symbol') and currency.symbol:
            return currency.symbol
        elif hasattr(currency, 'code'):
            return currency.code
    
    # العملة الأساسية
    try:
        company_settings = CompanySettings.objects.first()
        if company_settings and company_settings.base_currency:
            base_currency = company_settings.base_currency
            if base_currency.symbol:
                return base_currency.symbol
            return base_currency.code
    except:
        pass
    
    return ""
