from django import template
from settings.models import Currency, CompanySettings
from decimal import Decimal

register = template.Library()

@register.filter
def currency_format(value, currency_code=None):
    """تنسيق قيمة العملة"""
    if value is None:
        return ""
    
    try:
        # التحقق من نوع البيانات
        if isinstance(value, str):
            value = Decimal(value)
        elif not isinstance(value, Decimal):
            value = Decimal(str(value))
        
        # الحصول على العملة
        if currency_code:
            currency = Currency.objects.filter(code=currency_code).first()
        else:
            # البحث عن العملة الأساسية من إعدادات الشركة أولاً
            company_settings = CompanySettings.objects.first()
            if company_settings and company_settings.base_currency:
                currency = company_settings.base_currency
            else:
                currency = Currency.get_base_currency()
        
        if not currency:
            return f"{value:.2f}"
        
        # تنسيق العدد حسب عدد الخانات العشرية
        decimal_places = currency.decimal_places
        if decimal_places == 0:
            formatted_value = f"{value:.0f}"
        else:
            formatted_value = f"{value:.{decimal_places}f}"
        
        # إضافة رمز العملة
        company_settings = CompanySettings.objects.first()
        if company_settings and company_settings.show_currency_symbol and currency.symbol:
            return f"{formatted_value} {currency.symbol}"
        else:
            return f"{formatted_value} {currency.symbol if currency.symbol else currency.code}"
            
    except Exception as e:
        return str(value)

@register.filter
def currency_symbol(currency_code=None):
    """الحصول على رمز العملة"""
    if currency_code:
        currency = Currency.objects.filter(code=currency_code).first()
    else:
        # البحث عن العملة الأساسية من إعدادات الشركة أولاً
        company_settings = CompanySettings.objects.first()
        if company_settings and company_settings.base_currency:
            currency = company_settings.base_currency
        else:
            currency = Currency.get_base_currency()
    
    if currency:
        company_settings = CompanySettings.objects.first()
        if company_settings and company_settings.show_currency_symbol and currency.symbol:
            return currency.symbol
        else:
            return currency.code
    return ""

@register.simple_tag
def get_base_currency():
    """الحصول على العملة الأساسية"""
    company_settings = CompanySettings.objects.first()
    if company_settings and company_settings.base_currency:
        return company_settings.base_currency
    return Currency.get_base_currency()

@register.simple_tag
def get_active_currencies():
    """الحصول على العملات النشطة"""
    return Currency.get_active_currencies()

@register.simple_tag
def get_currency_code():
    """الحصول على رمز العملة الأساسية"""
    company_settings = CompanySettings.objects.first()
    if company_settings and company_settings.base_currency:
        return company_settings.base_currency.code
    
    # البحث عن العملة الأساسية في النظام
    currency = Currency.get_base_currency()
    if currency:
        return currency.code
    
    # إذا لم توجد عملة، عدم إنشاء أي عملة افتراضية
    return ""

@register.simple_tag
def get_currency_symbol():
    """الحصول على رمز العملة الأساسية"""
    company_settings = CompanySettings.objects.first()
    if company_settings and company_settings.base_currency:
        currency = company_settings.base_currency
        if company_settings.show_currency_symbol and currency.symbol:
            return currency.symbol
        return currency.code
    
    # البحث عن العملة الأساسية في النظام
    currency = Currency.get_base_currency()
    if currency:
        return currency.symbol if currency.symbol else currency.code
    
    # إذا لم توجد عملة، عدم إنشاء أي عملة افتراضية
    return ""

@register.filter
def format_currency(value):
    """
    تنسيق الأرقام المالية حسب عدد الخانات العشرية للعملة الأساسية
    يستخدم فقط للتنسيق بدون إضافة رمز العملة
    """
    if value is None:
        return "0"
    
    try:
        # التحقق من نوع البيانات
        if isinstance(value, str):
            value = Decimal(value)
        elif not isinstance(value, Decimal):
            value = Decimal(str(value))
        
        # الحصول على العملة الأساسية
        company_settings = CompanySettings.objects.first()
        if company_settings and company_settings.base_currency:
            currency = company_settings.base_currency
        else:
            currency = Currency.get_base_currency()
        
        # إذا لم توجد عملة، استخدم خانتين عشريتين افتراضياً
        if not currency:
            return f"{value:.2f}"
        
        # تنسيق العدد حسب عدد الخانات العشرية
        decimal_places = currency.decimal_places
        if decimal_places == 0:
            return f"{value:.0f}"
        else:
            return f"{value:.{decimal_places}f}"
            
    except Exception as e:
        # في حالة الخطأ، إرجاع القيمة كما هي
        return str(value)
