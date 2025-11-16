"""
Custom template filters for journal app
"""
from django import template
from decimal import Decimal

register = template.Library()


@register.filter(name='sum_debit')
def sum_debit(balances):
    """
    Calculate the sum of debit values from a list of balance objects.
    
    Args:
        balances: List of objects with 'debit' attribute
        
    Returns:
        Decimal: Total sum of debit values
    """
    try:
        total = Decimal('0')
        for item in balances:
            if hasattr(item, 'debit') and item.debit:
                total += Decimal(str(item.debit))
        return total
    except (TypeError, ValueError, AttributeError):
        return Decimal('0')


@register.filter(name='sum_credit')
def sum_credit(balances):
    """
    Calculate the sum of credit values from a list of balance objects.
    
    Args:
        balances: List of objects with 'credit' attribute
        
    Returns:
        Decimal: Total sum of credit values
    """
    try:
        total = Decimal('0')
        for item in balances:
            if hasattr(item, 'credit') and item.credit:
                total += Decimal(str(item.credit))
        return total
    except (TypeError, ValueError, AttributeError):
        return Decimal('0')
