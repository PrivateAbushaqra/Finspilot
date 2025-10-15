from typing import Optional
from django.apps import apps


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


def get_adjustment_account_code(adjustment_type: str, is_bank: bool = False, is_customer_supplier: bool = False) -> str:
    """
    تحديد رمز الحساب المناسب حسب نوع التعديل - متوافق مع IFRS
    
    Args:
        adjustment_type: نوع التعديل (capital, error_correction, bank_interest, etc.)
        is_bank: هل التعديل على حساب بنكي (True) أم صندوق نقدي (False)
        is_customer_supplier: هل التعديل على حساب عميل/مورد (True)
    
    Returns:
        رمز الحساب المناسب حسب المعايير الدولية IFRS
        
    Reference:
        - IAS 8: تصحيح الأخطاء السابقة يُسجل في الأرباح المحتجزة (305)
        - IAS 18/IFRS 15: الإيرادات التشغيلية في حسابات الإيرادات (40xx)
        - IAS 1: المصاريف التشغيلية في حسابات المصاريف (50xx)
        - IAS 39/IFRS 9: خسائر الديون المعدومة في المصاريف (50xx)
    """
    
    # خريطة تفاصيل الحسابات (رمز، اسم، نوع)
    ACCOUNT_DETAILS_MAP = {
        '301': ('رأس المال / Capital Account', 'equity'),
        '305': ('الأرباح المحتجزة / Retained Earnings', 'equity'),
        '4011': ('إيرادات الفوائد البنكية / Interest Revenue', 'revenue'),
        '5011': ('مصاريف الرسوم البنكية / Bank Charges Expense', 'expense'),
        '5021': ('مصاريف الديون المعدومة / Bad Debt Expense', 'expense'),
        '5022': ('مصاريف الخصم المسموح / Discount Allowed Expense', 'expense'),
        '4022': ('إيرادات الخصم المستلم / Discount Received Revenue', 'revenue'),
        '5099': ('مصاريف متنوعة / Miscellaneous Expenses', 'expense'),
        '4099': ('إيرادات متنوعة / Miscellaneous Revenue', 'revenue'),
    }
    
    # خريطة أنواع التعديلات إلى رموز الحسابات
    ADJUSTMENT_ACCOUNT_MAP = {
        # رأس المال - الحساب 301
        'capital': '301',  # Capital Account
        'capital_contribution': '301',  # مساهمة رأسمالية
        
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
        
        # شطب الديون المعدومة - مصاريف (IAS 39/IFRS 9)
        'bad_debt_write_off': '5021',  # Bad Debt Expense
        
        # خصم مسموح به - مصاريف
        'discount_allowed': '5022',  # Discount Allowed Expense
        
        # خصم مستلم - إيرادات
        'discount_received': '4022',  # Discount Received Revenue
        
        # إعادة تقييم - الأرباح المحتجزة
        'revaluation': '305',  # Retained Earnings
        
        # غير محدد - الأرباح المحتجزة (آمن)
        'other': '305',  # Retained Earnings
    }
    
    # إذا كان النوع غير محدد، استخدم الأرباح المحتجزة
    if not adjustment_type:
        account_code = '305'
    else:
        account_code = ADJUSTMENT_ACCOUNT_MAP.get(adjustment_type)
        # إذا كان الحساب غير محدد، استخدم الأرباح المحتجزة (آمن)
        if account_code is None:
            account_code = '305'
    
    # التحقق من وجود الحساب وإنشاؤه تلقائياً إذا لم يكن موجوداً
    Account = apps.get_model('journal', 'Account')
    account, created = Account.objects.get_or_create(
        code=account_code,
        defaults={
            'name': ACCOUNT_DETAILS_MAP.get(account_code, ('حساب تعديل / Adjustment Account', 'equity'))[0],
            'account_type': ACCOUNT_DETAILS_MAP.get(account_code, ('حساب تعديل / Adjustment Account', 'equity'))[1],
            'description': f'حساب تم إنشاؤه تلقائياً لنوع التعديل: {adjustment_type}',
            'is_active': True,
            'balance': 0
        }
    )
    
    return account_code
