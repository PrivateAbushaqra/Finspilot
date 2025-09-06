from .models import CompanySettings
from settings.models import Currency, CompanySettings as SettingsCompanySettings
from django.utils import translation


def company_settings(request):
    """إضافة إعدادات الشركة إلى السياق"""
    return {
        'company_settings': CompanySettings.get_settings()
    }


def currency_context(request):
    """إضافة معلومات العملة إلى السياق"""
    base_currency = Currency.get_base_currency()
    settings_company = SettingsCompanySettings.objects.first()
    
    return {
        'base_currency': base_currency,
        'settings_company': settings_company,
        'show_currency_symbol': settings_company.show_currency_symbol if settings_company else True,
    }

# دالة company_context المطلوبة في الإعدادات
def company_context(request):
    """إرجاع سياق فارغ أو معلومات الشركة إذا لزم الأمر"""
    return {}

# دالة notifications_context المطلوبة في الإعدادات
def notifications_context(request):
    """إرجاع سياق فارغ أو إشعارات إذا لزم الأمر"""
    return {}

def language_context(request):
    """إضافة اللغة الحالية إلى السياق"""
    return {
        'current_language': translation.get_language(),
        'LANGUAGE_CODE': translation.get_language(),
    }


def active_menu_context(request):
    """تحديد القائمة النشطة في الشريط الجانبي بناءً على المسار الحالي"""
    path = request.path
    active_menu = ''
    
    # تحديد القائمة النشطة بناءً على المسار
    if '/search/' in path:
        active_menu = 'search'
    elif path == '/' or '/dashboard/' in path:
        active_menu = 'dashboard'
    elif '/banks/' in path:
        active_menu = 'banks'
    elif '/cashboxes/' in path:
        active_menu = 'cashboxes'
    elif '/receipts/' in path:
        active_menu = 'receipts'
    elif '/payments/' in path:
        active_menu = 'payments'
    elif '/products/' in path:
        active_menu = 'products'
    elif '/customers/' in path:
        active_menu = 'customers'
    elif '/purchases/' in path:
        active_menu = 'purchases'
    elif '/sales/' in path:
        active_menu = 'sales'
    elif '/inventory/' in path:
        active_menu = 'inventory'
    elif '/accounts/' in path:
        active_menu = 'accounts'
    elif '/journal/' in path:
        active_menu = 'journal'
    elif '/reports/' in path:
        active_menu = 'reports'
    elif '/revenues_expenses/' in path:
        active_menu = 'revenues_expenses'
    elif '/assets_liabilities/' in path:
        active_menu = 'assets_liabilities'
    elif '/backup/' in path:
        active_menu = 'backup'
    elif '/settings/' in path:
        active_menu = 'settings'
    elif '/users/' in path:
        active_menu = 'users'
    elif '/hr/' in path:
        active_menu = 'hr'
    elif '/tools/' in path:
        active_menu = 'tools'
    elif '/audit-log/' in path:
        active_menu = 'audit_log'
    
    # تسجيل العملية في سجل الأنشطة (فقط للصفحات المهمة)
    if request.user.is_authenticated and active_menu and hasattr(request, '_navigation_logged') is False:
        try:
            from .models import AuditLog
            # تجنب التسجيل المكرر للصفحة نفسها
            request._navigation_logged = True
            
            # تحديد اسم القسم بالعربية
            section_names = {
                'search': 'البحث الشامل',
                'dashboard': 'لوحة التحكم',
                'banks': 'الحسابات البنكية',
                'cashboxes': 'الصناديق النقدية',
                'receipts': 'إيصالات الاستلام',
                'payments': 'أذون الصرف',
                'products': 'الفئات والمنتجات',
                'customers': 'العملاء والموردون',
                'purchases': 'المشتريات',
                'sales': 'المبيعات',
                'inventory': 'المخزون',
                'accounts': 'الحسابات',
                'journal': 'القيود المحاسبية',
                'reports': 'التقارير',
                'revenues_expenses': 'الإيرادات والمصروفات',
                'assets_liabilities': 'الأصول والخصوم',
                'backup': 'النسخ الاحتياطي',
                'settings': 'الإعدادات',
                'users': 'المستخدمون',
                'hr': 'الموارد البشرية',
                'tools': 'الأدوات',
                'audit_log': 'سجل الأنشطة'
            }
            
            section_name = section_names.get(active_menu, active_menu)
            
            AuditLog.objects.create(
                user=request.user,
                action_type='navigation',
                content_type='sidebar_navigation',
                description=f'انتقال إلى قسم: {section_name}'
            )
        except Exception:
            # تجاهل الأخطاء في تسجيل الأنشطة
            pass
    
    return {
        'active_menu': active_menu,
        'current_path': path,
    }
