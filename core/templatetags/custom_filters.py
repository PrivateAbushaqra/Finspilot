from django import template
from django.contrib.auth.models import Permission
import re

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

@register.filter
def get_item(dictionary, key):
    """
    Get an item from a dictionary using a key
    """
    return dictionary.get(key, None)

@register.filter
def dict_lookup(dictionary, key):
    """
    Get value from dictionary using key
    """
    if dictionary and key:
        return dictionary.get(key, key)
    return key

@register.filter
def get_document_number(description):
    """
    استخراج رقم المستند من وصف المعاملة
    """
    if not description:
        return None
    
    # أنماط شائعة لأرقام المستندات
    patterns = [
        r'فاتورة رقم\s*([A-Za-z0-9\-]+)',  # فاتورة رقم INV-001
        r'رقم\s*([A-Za-z0-9\-]+)',  # رقم INV-001
        r'#([A-Za-z0-9\-]+)',  # #INV-001
        r'([A-Za-z]{2,}-[0-9]+)',  # INV-001, REC-001, PAY-001
        r'([A-Za-z]{3,}[0-9]+)',  # INV001, REC001
        r'سند\s+(قبض|دفع|صرف)\s+([A-Za-z0-9\-]+)',  # سند قبض REC-001
        r'([0-9]{3,}-?[0-9]*)',  # أرقام مثل 001, 001-1, 12345
    ]
    
    for pattern in patterns:
        match = re.search(pattern, description)
        if match:
            # للنمط الذي يحتوي على نوع السند، أعد الرقم الثاني
            if 'سند' in pattern:
                result = match.group(2)
            else:
                result = match.group(1)
            
            # تجنب استخراج التواريخ أو المبالغ
            if len(result) >= 3 and not result.startswith(('20', '19')) and not '.' in result:
                return result
    
    return None
