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
    
    # تحديد عدد المنازل العشرية من العملة
    decimal_places = 2  # القيمة الافتراضية
    currency_display = None
    
    # الحصول على العملة
    if currency:
        # إذا تم تمرير عملة محددة
        if hasattr(currency, 'decimal_places'):
            decimal_places = currency.decimal_places
        if hasattr(currency, 'symbol') and currency.symbol:
            currency_display = currency.symbol
        elif hasattr(currency, 'code'):
            currency_display = currency.code
    else:
        # إذا لم تُمرر عملة، استخدم العملة الأساسية
        try:
            # محاولة الحصول على العملة من إعدادات الشركة أولاً
            company_settings = CompanySettings.objects.first()
            if company_settings and hasattr(company_settings, 'base_currency') and company_settings.base_currency:
                base_currency = company_settings.base_currency
                if hasattr(base_currency, 'decimal_places'):
                    decimal_places = base_currency.decimal_places
                if base_currency.symbol:
                    currency_display = base_currency.symbol
                else:
                    currency_display = base_currency.code
            else:
                # إذا لم توجد إعدادات الشركة، ابحث عن العملة الأساسية مباشرة
                from settings.models import Currency as CurrencyModel
                base_currency = CurrencyModel.objects.filter(is_base_currency=True).first()
                if base_currency:
                    if hasattr(base_currency, 'decimal_places'):
                        decimal_places = base_currency.decimal_places
                    if base_currency.symbol:
                        currency_display = base_currency.symbol
                    else:
                        currency_display = base_currency.code
        except:
            pass
    
    # تنسيق المبلغ بعدد المنازل العشرية الصحيح
    formatted_amount = f"{amount:,.{decimal_places}f}"
    
    # إضافة رمز العملة إذا وُجد
    if currency_display:
        return f"{formatted_amount} {currency_display}"
    
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
