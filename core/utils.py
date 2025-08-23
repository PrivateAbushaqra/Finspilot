from typing import Optional


def get_client_ip(request) -> Optional[str]:
    """الحصول على عنوان IP الحقيقي للعميل من الطلب.

    يعتمد أولاً على ترويسة X-Forwarded-For (عند وجود Proxy) ثم يسقط إلى REMOTE_ADDR.
    """
    try:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # في حال وجود أكثر من IP (Proxy chain)، نأخذ الأول
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')
    except Exception:
        return None
