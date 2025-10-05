"""
متغير عام لتتبع حالة الاستعادة (Backup Restore)
يُستخدم لتعطيل السيجنالات مؤقتاً أثناء استعادة النسخة الاحتياطية
"""

_is_restoring = False

def set_restoring(value: bool):
    """
    تفعيل/إيقاف وضع الاستعادة
    
    Args:
        value (bool): True لتفعيل وضع الاستعادة، False لإيقافه
    """
    global _is_restoring
    _is_restoring = value

def is_restoring() -> bool:
    """
    التحقق من وضع الاستعادة الحالي
    
    Returns:
        bool: True إذا كانت عملية الاستعادة جارية، False otherwise
    """
    return _is_restoring
