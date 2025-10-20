import threading

_local = threading.local()

def set_restoring(value):
    """تعيين حالة الاستعادة"""
    _local.is_restoring = value

def is_restoring():
    """التحقق من حالة الاستعادة"""
    return getattr(_local, 'is_restoring', False)