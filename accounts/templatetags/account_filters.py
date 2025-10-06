from django import template
from decimal import Decimal

register = template.Library()

@register.filter(name='sum_attr')
def sum_attr(queryset, attr_name):
    """
    Calculate sum of a specific attribute in queryset
    Usage: {{ queryset|sum_attr:'attribute_name' }}
    """
    try:
        total = Decimal('0')
        for item in queryset:
            value = getattr(item, attr_name, 0)
            if value:
                total += Decimal(str(value))
        return total
    except (ValueError, TypeError, AttributeError):
        return Decimal('0')
