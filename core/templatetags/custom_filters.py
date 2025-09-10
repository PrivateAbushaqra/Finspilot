from django import template
from django.contrib.auth.models import Permission

register = template.Library()

@register.filter
def unique_permissions(permissions):
    """
    إزالة التكرار من قائمة الصلاحيات بناءً على codename
    """
    seen = set()
    unique_perms = []
    for perm in permissions:
        if perm.codename not in seen:
            seen.add(perm.codename)
            unique_perms.append(perm)
    return unique_perms
