import threading
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse
import json
from .utils import get_client_ip

# متغير عام لحفظ معلومات المستخدم الحالي
_current_user = threading.local()


class AuditMiddleware(MiddlewareMixin):
    """Middleware لتتبع المستخدم الحالي وتسجيل أنشطة العرض"""
    
    def process_request(self, request):
        """حفظ المستخدم الحالي في thread local storage"""
        _current_user.user = getattr(request, 'user', None)
        _current_user.request = request
        
        # تسجيل أنشطة العرض للمستخدمين المسجلين دخولهم
        if hasattr(request, 'user') and request.user.is_authenticated:
            self.log_view_activity(request)
    
    def log_view_activity(self, request):
        """تسجيل نشاط العرض"""
        try:
            # استثناء بعض المسارات من التسجيل
            excluded_paths = [
                '/static/',
                '/media/',
                '/admin/jsi18n/',
                '/favicon.ico',
                '/api/extend-session/',
                '/api/',
                '.css',
                '.js',
                '.png',
                '.jpg',
                '.ico',
                '.svg',
                '.woff',
                '.ttf'
            ]
            
            # التحقق من استثناء المسار
            if any(excluded in request.path for excluded in excluded_paths):
                return
            
            # استثناء طلبات AJAX للتحديثات المتكررة
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                # تسجيل فقط AJAX المهمة
                important_ajax_paths = [
                    '/delete/',
                    '/create/',
                    '/update/',
                    '/edit/',
                    '/add/',
                    '/save/',
                    '/process/'
                ]
                if not any(path in request.path for path in important_ajax_paths):
                    return
            
            # تسجيل النشاط فقط للصفحات المهمة
            self._create_view_log(request)
            
        except Exception as e:
            # لا نريد أن يتوقف النظام بسبب خطأ في التسجيل
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"خطأ في تسجيل نشاط العرض: {e}")
    
    def _create_view_log(self, request):
        """إنشاء سجل نشاط العرض"""
        try:
            from .models import AuditLog
            from .signals import get_client_ip
            
            # تحديد وصف النشاط بناءً على المسار
            description = self._get_activity_description(request)
            
            if description:  # تسجيل فقط إذا كان هناك وصف مفيد
                # إنشاء كائن وهمي للعرض
                class ViewActivity:
                    def __init__(self, path):
                        self.id = hash(path) % 1000000  # معرف فريد للمسار
                        self.pk = self.id
                        self.path = path
                    
                    def __str__(self):
                        return f"عرض صفحة: {self.path}"
                
                view_obj = ViewActivity(request.path)
                
                # استخدام log_activity بدلاً من إنشاء مباشر لمعالجة أخطاء sequence
                from .signals import log_activity
                log_activity(
                    user=request.user,
                    action_type='view',
                    obj=view_obj,
                    description=description,
                    request=request
                )
                
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"خطأ في إنشاء سجل العرض: {e}")
    
    def _get_activity_description(self, request):
        """تحديد وصف النشاط بناءً على المسار"""
        path = request.path
        method = request.method
        
        # قاموس ترجمة المسارات
        path_descriptions = {
            # الصفحة الرئيسية
            '/': 'عرض الصفحة الرئيسية',
            '/en/': 'عرض الصفحة الرئيسية',
            '/ar/': 'عرض الصفحة الرئيسية',
            
            # المبيعات
            '/sales/': 'عرض قائمة فواتير المبيعات',
            '/en/sales/': 'عرض قائمة فواتير المبيعات',
            '/sales/create/': 'فتح صفحة إنشاء فاتورة مبيعات',
            '/en/sales/create/': 'فتح صفحة إنشاء فاتورة مبيعات',
            '/sales/pos/': 'عرض نقطة البيع',
            '/en/sales/pos/': 'عرض نقطة البيع',
            
            # المشتريات
            '/purchases/': 'عرض قائمة فواتير المشتريات',
            '/en/purchases/': 'عرض قائمة فواتير المشتريات',
            '/purchases/create/': 'فتح صفحة إنشاء فاتورة مشتريات',
            '/en/purchases/create/': 'فتح صفحة إنشاء فاتورة مشتريات',
            
            # العملاء
            '/customers/': 'عرض قائمة العملاء والموردين',
            '/en/customers/': 'عرض قائمة العملاء والموردين',
            '/customers/create/': 'فتح صفحة إضافة عميل جديد',
            '/en/customers/create/': 'فتح صفحة إضافة عميل جديد',
            
            # المنتجات
            '/products/': 'عرض قائمة المنتجات',
            '/en/products/': 'عرض قائمة المنتجات',
            '/products/create/': 'فتح صفحة إضافة منتج جديد',
            '/en/products/create/': 'فتح صفحة إضافة منتج جديد',
            
            # المخزون
            '/inventory/': 'عرض إدارة المخزون',
            '/en/inventory/': 'عرض إدارة المخزون',
            
            # البنوك
            '/banks/': 'عرض الحسابات البنكية',
            '/en/banks/': 'عرض الحسابات البنكية',
            
            # الصناديق
            '/cashboxes/': 'عرض الصناديق النقدية',
            '/en/cashboxes/': 'عرض الصناديق النقدية',
            
            # دفتر اليومية
            '/journal/': 'عرض دفتر اليومية',
            '/en/journal/': 'عرض دفتر اليومية',
            
            # التقارير
            '/reports/': 'عرض قائمة التقارير',
            '/en/reports/': 'عرض قائمة التقارير',
            '/reports/profit-loss/': 'عرض تقرير الأرباح والخسائر',
            '/en/reports/profit-loss/': 'عرض تقرير الأرباح والخسائر',
            '/reports/tax/': 'عرض التقرير الضريبي',
            '/en/reports/tax/': 'عرض التقرير الضريبي',
            
            # المستخدمين
            '/users/': 'عرض قائمة المستخدمين',
            '/en/users/': 'عرض قائمة المستخدمين',
            
            # الإعدادات
            '/settings/': 'عرض الإعدادات',
            '/en/settings/': 'عرض الإعدادات',
            '/settings/company/': 'عرض إعدادات الشركة',
            '/en/settings/company/': 'عرض إعدادات الشركة',
            
            # سجل الأنشطة
            '/audit-log/': 'عرض سجل الأنشطة',
            '/en/audit-log/': 'عرض سجل الأنشطة',
            
            # سندات القبض والدفع
            '/receipts/': 'عرض سندات القبض',
            '/en/receipts/': 'عرض سندات القبض',
            '/payments/': 'عرض سندات الدفع',
            '/en/payments/': 'عرض سندات الدفع',
            
            # الحسابات المحاسبية
            '/accounts/': 'عرض الحسابات المحاسبية',
            '/en/accounts/': 'عرض الحسابات المحاسبية',
        }
        
        # البحث عن وصف مباشر
        if path in path_descriptions:
            return path_descriptions[path]
        
        # البحث عن أنماط في المسار
        if '/edit/' in path or '/update/' in path:
            return f'فتح صفحة تعديل (المسار: {path})'
        elif '/delete/' in path:
            return f'عملية حذف (المسار: {path})'
        elif '/detail/' in path or '/view/' in path:
            return f'عرض تفاصيل (المسار: {path})'
        elif '/create/' in path or '/add/' in path:
            return f'فتح صفحة إضافة جديدة (المسار: {path})'
        elif method == 'POST':
            return f'إرسال بيانات (المسار: {path})'
        elif method == 'GET' and '?' in path:
            return f'بحث أو فلترة (المسار: {path.split("?")[0]})'
        elif method == 'GET':
            return f'عرض صفحة (المسار: {path})'
        
        return None


class SessionTimeoutMiddleware:
    """
    Middleware لمعالجة انتهاء الجلسة التلقائي
    هذا الـ Middleware يعمل فقط عند تفعيله من إعدادات الشركة
    ولا يتداخل مع آلية الجلسة الأساسية في Django
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # تخطي المسارات التي لا تحتاج لفحص انتهاء الجلسة
        excluded_paths = [
            '/login/',
            '/logout/',
            '/admin/login/',
            '/admin/logout/',
            '/media/',
            '/static/',
            '/api/extend-session/',
            '/settings/company/',  # إضافة صفحة إعدادات الشركة
            '/auth/',  # جميع مسارات المصادقة
        ]
        
        # التحقق من أن المستخدم مسجل دخوله
        if request.user.is_authenticated and not any(request.path.startswith(path) for path in excluded_paths):
            # الحصول على إعدادات الشركة
            try:
                from core.models import CompanySettings
                company_settings = CompanySettings.objects.first()
                
                # التحقق من تفعيل انتهاء الجلسة التلقائي
                # فقط إذا كانت الإعدادات موجودة ومفعلة
                if company_settings and company_settings.enable_session_timeout:
                    session_timeout_minutes = company_settings.session_timeout_minutes
                    
                    # التحقق من وقت آخر نشاط
                    last_activity = request.session.get('last_activity')
                    now = timezone.now()
                    
                    if last_activity:
                        try:
                            last_activity_time = timezone.datetime.fromisoformat(last_activity)
                            time_since_activity = now - last_activity_time
                            
                            # إذا تجاوز المستخدم مدة عدم النشاط المحددة
                            if time_since_activity > timedelta(minutes=session_timeout_minutes):
                                try:
                                    logout(request)
                                except Exception as e:
                                    # تجاهل أخطاء الجلسة
                                    import logging
                                    logger = logging.getLogger(__name__)
                                    logger.warning(f"خطأ في logout بسبب انتهاء الجلسة: {e}")
                                
                                # إذا كان طلب AJAX، أرسل استجابة JSON
                                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                                    return JsonResponse({
                                        'error': 'انتهت جلسة العمل بسبب عدم النشاط',
                                        'redirect': '/ar/auth/login/',
                                        'session_expired': True
                                    }, status=401)
                                
                                # وإلا قم بإعادة التوجيه لصفحة تسجيل الدخول
                                return redirect('/ar/auth/login/')
                        except (ValueError, TypeError) as e:
                            # في حال وجود خطأ في تحليل التاريخ، امسح last_activity
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.warning(f"خطأ في تحليل last_activity: {e}")
                            request.session['last_activity'] = now.isoformat()
                    else:
                        # إذا لم يكن هناك last_activity، أنشئه
                        request.session['last_activity'] = now.isoformat()
                    
                    # تحديث وقت آخر نشاط فقط للطلبات المهمة (ليس للملفات الثابتة)
                    if not any(ext in request.path for ext in ['.css', '.js', '.png', '.jpg', '.ico', '.svg']):
                        request.session['last_activity'] = now.isoformat()
                    
                    # لا نستخدم set_expiry هنا لأننا نريد الاعتماد على SESSION_COOKIE_AGE
                    # وليس على logout_on_browser_close من CompanySettings
                    # هذا يتجنب التعارض بين الإعدادات
                
            except Exception as e:
                # في حالة حدوث خطأ، تسجيل الخطأ ولكن لا تؤثر على سير العمل
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"خطأ في SessionTimeoutMiddleware: {str(e)}")
        
        response = self.get_response(request)
        return response


class SessionSecurityMiddleware:
    """
    Middleware إضافي للأمان
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # إضافة معلومات الأمان للجلسة
        if request.user.is_authenticated:
            # تسجيل معلومات المتصفح و IP
            request.session['user_agent'] = request.META.get('HTTP_USER_AGENT', '')
            request.session['ip_address'] = get_client_ip(request)
            
            # التحقق من تغيير IP أو المتصفح (اختياري - يمكن تفعيله لاحقاً)
            # stored_ip = request.session.get('stored_ip_address')
            # stored_user_agent = request.session.get('stored_user_agent')
            
            # if stored_ip and stored_ip != request.session['ip_address']:
            #     # IP تغير - يمكن اتخاذ إجراء أمني
            #     pass
        
        response = self.get_response(request)
        return response
    
    # استخدام get_client_ip من core.utils بدلاً من نسخة محلية لتجنب التكرار


def get_current_user():
    """الحصول على المستخدم الحالي"""
    return getattr(_current_user, 'user', None)


def get_current_request():
    """الحصول على الـ request الحالي"""
    return getattr(_current_user, 'request', None)


def set_audit_user(instance, user):
    """ربط المستخدم بالكائن لأغراض المراجعة"""
    instance._audit_user = user


class POSUserMiddleware:
    """
    Middleware لتوجيه مستخدمي نقطة البيع إلى صفحة POS فقط
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # تحقق من المستخدم ونوعه
        if (request.user.is_authenticated and 
            hasattr(request.user, 'user_type') and 
            request.user.user_type == 'pos_user'):
            
            # التحقق من وجود المستخدم في مجموعات
            # إذا كان في مجموعة، نسمح له بالوصول حسب صلاحيات المجموعة
            user_has_groups = request.user.groups.exists()
            
            # إذا كان المستخدم في مجموعة، لا نقيده بمسارات POS فقط
            if user_has_groups:
                # السماح له بالوصول لأي صفحة حسب صلاحيات مجموعته
                response = self.get_response(request)
                return response
            
            # إذا لم يكن في مجموعة، نطبق القيود العادية لمستخدم POS
            # المسارات المسموحة لمستخدم نقطة البيع
            allowed_paths = [
                '/ar/sales/pos/',
                '/en/sales/pos/',
                '/ar/',  # السماح بالصفحة الرئيسية لأن DashboardView سيوجهه تلقائياً
                '/en/',  # السماح بالصفحة الرئيسية لأن DashboardView سيوجهه تلقائياً
                '/language-switch/',  # السماح بتبديل اللغة
                '/i18n/',  # Django's i18n URLs
                '/ar/logout/',
                '/logout/',
                '/ar/accounts/logout/',
                '/accounts/logout/',
                '/ar/auth/logout/',
                '/auth/logout/',
                '/en/auth/logout/',
                '/static/',
                '/media/',
            ]
            
            # السماح بـ API calls الخاصة بنقطة البيع
            pos_api_paths = [
                '/ar/sales/pos/',
                '/en/sales/pos/',
                '/ar/sales/invoices/pos-print/',
                '/en/sales/invoices/pos-print/',
                '/ar/sales/api/',
                '/en/sales/api/',
                '/ar/products/api/',
                '/en/products/api/',
                '/ar/customers/api/',
                '/en/customers/api/',
                '/ar/inventory/api/',
                '/en/inventory/api/',
            ]
            
            current_path = request.path
            
            # إذا كان المستخدم يحاول الوصول لمسار غير مسموح
            is_allowed = any(current_path.startswith(path) for path in allowed_paths + pos_api_paths)
            
            if not is_allowed:
                # توجيه المستخدم إلى صفحة نقطة البيع مع الحفاظ على اللغة
                from django.utils import translation
                current_language = translation.get_language() or 'ar'
                pos_url = f'/{current_language}/sales/pos/'
                return redirect(pos_url)
            
            # التأكد من استخدام اللغة الصحيحة من الجلسة
            # إذا كان المستخدم يصل إلى POS بلغة مختلفة عن الجلسة، احترم اللغة من المسار
            if current_path.startswith('/ar/sales/pos/') or current_path.startswith('/en/sales/pos/'):
                # استخرج اللغة من المسار
                path_lang = 'ar' if current_path.startswith('/ar/') else 'en'
                session_lang = request.session.get('_language', 'ar')
                
                # إذا كانت اللغة في المسار مختلفة عن الجلسة، حدّث الجلسة
                if path_lang != session_lang:
                    from django.utils import translation
                    translation.activate(path_lang)
                    request.session['_language'] = path_lang

        response = self.get_response(request)
        return response


class SessionErrorMiddleware:
    """
    Middleware للتعامل مع أخطاء الجلسة مثل SessionInterrupted
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            response = self.get_response(request)
            return response
        except Exception as e:
            # التحقق من نوع الخطأ
            if 'SessionInterrupted' in str(type(e)) or 'session was deleted' in str(e):
                # إعادة توجيه لصفحة تسجيل الدخول
                from django.shortcuts import redirect
                return redirect('/ar/auth/login/')
            else:
                # إعادة رفع الخطأ إذا لم يكن SessionInterrupted
                raise


class FiscalYearMiddleware:
    """
    Middleware للتحكم بالوصول إلى السنوات المالية المقفلة
    فقط المستخدمون من نوع superadmin يمكنهم الوصول للسنوات المقفلة
    """
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # السماح للمستخدمين غير المسجلين والصفحات المستثناة
        if not request.user.is_authenticated:
            return self.get_response(request)
        
        # استثناء مسارات معينة من الفحص
        excluded_paths = [
            '/static/',
            '/media/',
            '/admin/',
            '/ar/auth/',
            '/ar/journal/open-fiscal-year/',  # السماح بفتح سنة جديدة
            '/ar/journal/year-end-closing/',  # السماح بالإقفال
        ]
        
        if any(request.path.startswith(path) for path in excluded_paths):
            return self.get_response(request)
        
        # التحقق من السنة الحالية
        try:
            from journal.models import FiscalYear
            current_year = FiscalYear.objects.filter(is_current=True).first()
            
            # إذا كانت السنة الحالية مقفلة وليس superadmin
            if current_year and current_year.status == 'closed':
                user = request.user
                is_superadmin = (
                    getattr(user, 'is_superuser', False) or
                    getattr(user, 'user_type', None) == 'superadmin'
                )
                
                if not is_superadmin:
                    # إعادة توجيه لصفحة تنبيه
                    from django.contrib import messages
                    from django.shortcuts import redirect
                    messages.warning(
                        request,
                        'السنة المالية الحالية مقفلة. يرجى التواصل مع المدير لفتح سنة جديدة.'
                    )
                    return redirect('/ar/')
        
        except Exception:
            # في حالة أي خطأ، نسمح بالمرور
            pass
        
        return self.get_response(request)
