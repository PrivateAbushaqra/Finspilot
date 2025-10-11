from django import template
from django.utils.translation import get_language
from decimal import Decimal

register = template.Library()

@register.filter
def currency_format(value, currency_code='JOD'):
    """
    تنسيق المبلغ العملي مع العملة باستخدام النقطة كفاصل عشري
    """
    if value is None:
        return '0.000'

    try:
        # تحويل إلى Decimal إذا لزم الأمر
        if not isinstance(value, Decimal):
            value = Decimal(str(value))

        # تنسيق مع 3 خانات عشرية ونقطة
        formatted = f"{value:.3f}"

        # إضافة رمز العملة
        currency_symbols = {
            'JOD': 'د.أ',
            'USD': '$',
            'EUR': '€',
            'GBP': '£',
            'SAR': 'ر.س',
            'AED': 'د.إ',
        }

        symbol = currency_symbols.get(currency_code, currency_code)
        return f"{formatted} {symbol}"

    except (ValueError, TypeError):
        return f"0.000 {currency_code}"