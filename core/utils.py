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


def get_adjustment_account_code(adjustment_type: str, is_bank: bool = False) -> str:
    """
    تحديد رمز الحساب المناسب حسب نوع التعديل - متوافق مع IFRS
    
    Args:
        adjustment_type: نوع التعديل (capital, error_correction, bank_interest, etc.)
        is_bank: هل التعديل على حساب بنكي (True) أم صندوق نقدي (False)
    
    Returns:
        رمز الحساب المناسب حسب المعايير الدولية IFRS
        
    Reference:
        - IAS 8: تصحيح الأخطاء السابقة يُسجل في الأرباح المحتجزة (305)
        - IAS 18/IFRS 15: الإيرادات التشغيلية في حسابات الإيرادات (40xx)
        - IAS 1: المصاريف التشغيلية في حسابات المصاريف (50xx)
    """
    
    # خريطة أنواع التعديلات إلى رموز الحسابات
    ADJUSTMENT_ACCOUNT_MAP = {
        # رأس المال - الحساب 301
        'capital': '301',  # Capital Account
        
        # تصحيح الأخطاء - الأرباح المحتجزة (IAS 8)
        'error_correction': '305',  # Retained Earnings
        
        # إيرادات الفوائد البنكية (IAS 18/IFRS 15)
        'bank_interest': '4011',  # Interest Revenue
        
        # مصاريف الرسوم البنكية (IAS 1)
        'bank_charges': '5011',  # Bank Charges Expense
        
        # فروق العملة (IAS 21)
        'exchange_difference': None,  # يتم تحديده حسب الربح أو الخسارة
        
        # نقص النقدية - مصاريف متنوعة
        'cash_shortage': '5099',  # Miscellaneous Expenses
        
        # فائض النقدية - إيرادات متنوعة
        'cash_surplus': '4099',  # Miscellaneous Revenue
        
        # تسويات البنوك والصناديق - الأرباح المحتجزة (IAS 8)
        'reconciliation': '305',  # Retained Earnings
        
        # غير محدد - الأرباح المحتجزة (آمن)
        'other': '305',  # Retained Earnings
    }
    
    # إذا كان النوع غير محدد، استخدم الأرباح المحتجزة
    if not adjustment_type:
        return '305'
    
    account_code = ADJUSTMENT_ACCOUNT_MAP.get(adjustment_type)
    
    # إذا كان الحساب غير محدد، استخدم الأرباح المحتجزة (آمن)
    if account_code is None:
        return '305'
    
    return account_code
