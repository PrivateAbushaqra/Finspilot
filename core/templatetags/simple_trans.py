from django import template
from django.utils.translation import get_language
from core.translations import get_translation

register = template.Library()

@register.filter
def simple_trans(text):
    """
    فلتر بسيط للترجمة
    """
    current_language = get_language()
    return get_translation(text, current_language)

@register.simple_tag
def simple_translate(text):
    """
    تاج بسيط للترجمة
    """
    current_language = get_language()
    return get_translation(text, current_language)
