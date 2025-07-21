from django.db.models.signals import post_save, post_delete, pre_save, pre_delete
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.signals import user_logged_in, user_logged_out
from .models import AuditLog
from .middleware import get_current_user, get_current_request


def get_client_ip(request):
    """الحصول على عنوان IP للمستخدم"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def log_activity(user, action_type, obj, description, request=None):
    """تسجيل نشاط في سجل المراجعة"""
    try:
        if not user or not user.is_authenticated:
            return
        
        # تحديد نوع المحتوى
        content_type = obj.__class__.__name__
        object_id = getattr(obj, 'id', None) or getattr(obj, 'pk', None)
        
        # الحصول على عنوان IP
        ip_address = None
        if request:
            ip_address = get_client_ip(request)
        
        # إنشاء سجل المراجعة
        AuditLog.objects.create(
            user=user,
            action_type=action_type,
            content_type=content_type,
            object_id=object_id,
            description=description,
            ip_address=ip_address
        )
    except Exception as e:
        # في حالة حدوث خطأ، لا نريد أن يتوقف النظام
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error logging activity: {e}")


# دالة مساعدة لتسجيل الأنشطة من الـ Views
def log_user_activity(request, action_type, obj, description):
    """دالة مساعدة لتسجيل الأنشطة من الـ Views"""
    if hasattr(request, 'user'):
        log_activity(request.user, action_type, obj, description, request)


def get_model_description(instance, action_type):
    """الحصول على وصف تفصيلي للنموذج حسب نوعه"""
    model_name = instance.__class__.__name__
    
    # وصف مخصص لكل نموذج
    model_descriptions = {
        'SalesInvoice': f'فاتورة مبيعات رقم {getattr(instance, "invoice_number", "غير محدد")}',
        'PurchaseInvoice': f'فاتورة مشتريات رقم {getattr(instance, "invoice_number", "غير محدد")}',
        'SalesReturn': f'مردود مبيعات رقم {getattr(instance, "return_number", "غير محدد")}',
        'PurchaseReturn': f'مردود مشتريات رقم {getattr(instance, "return_number", "غير محدد")}',
        'CustomerSupplier': f'عميل/مورد: {getattr(instance, "name", "غير محدد")}',
        'Product': f'منتج: {getattr(instance, "name", "غير محدد")}',
        'BankAccount': f'حساب بنكي: {getattr(instance, "account_name", "غير محدد")}',
        'Cashbox': f'صندوق نقدي: {getattr(instance, "name", "غير محدد")}',
        'PaymentReceipt': f'سند قبض رقم {getattr(instance, "receipt_number", "غير محدد")}',
        'PaymentVoucher': f'سند دفع رقم {getattr(instance, "voucher_number", "غير محدد")}',
        'JournalEntry': f'قيد يومية رقم {getattr(instance, "entry_number", "غير محدد")}',
        'User': f'مستخدم: {getattr(instance, "username", "غير محدد")}',
        'CompanySettings': 'إعدادات الشركة',
        'Currency': f'عملة: {getattr(instance, "code", "غير محدد")}',
        'Account': f'حساب محاسبي: {getattr(instance, "name", "غير محدد")}',
        'InventoryMovement': f'حركة مخزون: {getattr(instance, "product", "غير محدد")}',
        'BankTransfer': f'تحويل بنكي رقم {getattr(instance, "transfer_number", "غير محدد")}',
        'CashboxTransfer': f'تحويل صندوق رقم {getattr(instance, "transfer_number", "غير محدد")}',
        'Revenue': f'إيراد: {getattr(instance, "description", "غير محدد")}',
        'Expense': f'مصروف: {getattr(instance, "description", "غير محدد")}',
        'Asset': f'أصل: {getattr(instance, "name", "غير محدد")}',
        'Liability': f'التزام: {getattr(instance, "name", "غير محدد")}',
    }
    
    # الحصول على الوصف المخصص أو استخدام وصف عام
    item_description = model_descriptions.get(model_name, str(instance))
    
    # إضافة معلومات إضافية حسب نوع العملية
    action_descriptions = {
        'create': 'إنشاء',
        'update': 'تحديث', 
        'delete': 'حذف',
        'view': 'عرض'
    }
    
    action_desc = action_descriptions.get(action_type, action_type)
    
    return f"{action_desc} {item_description}"


def get_field_changes(instance, previous_values=None):
    """الحصول على تفاصيل التغييرات في الحقول"""
    if not previous_values:
        return ""
    
    changes = []
    for field_name, old_value in previous_values.items():
        try:
            new_value = getattr(instance, field_name, None)
            if old_value != new_value:
                # ترجمة أسماء الحقول
                field_translations = {
                    'name': 'الاسم',
                    'total_amount': 'المبلغ الإجمالي',
                    'invoice_number': 'رقم الفاتورة',
                    'invoice_date': 'تاريخ الفاتورة',
                    'customer': 'العميل',
                    'supplier': 'المورد',
                    'phone': 'الهاتف',
                    'email': 'البريد الإلكتروني',
                    'address': 'العنوان',
                    'is_active': 'النشاط',
                    'price': 'السعر',
                    'quantity': 'الكمية',
                    'description': 'الوصف',
                    'account_name': 'اسم الحساب',
                    'account_number': 'رقم الحساب',
                    'balance': 'الرصيد',
                    'status': 'الحالة',
                }
                
                field_display = field_translations.get(field_name, field_name)
                changes.append(f"{field_display}: من '{old_value}' إلى '{new_value}'")
        except:
            continue
    
    return " | ".join(changes) if changes else ""


# متغير لحفظ القيم السابقة قبل التحديث
_previous_values = {}


# Signals لتسجيل أنشطة النماذج تلقائياً
@receiver(pre_save)
def store_previous_values(sender, instance, **kwargs):
    """حفظ القيم السابقة قبل التحديث"""
    # تجنب AuditLog نفسه
    if sender == AuditLog:
        return
    
    # تجنب النماذج المستثناة
    excluded_models = [
        'Session', 'LogEntry', 'Migration', 'SystemNotification',
        'ContentType', 'Permission', 'Group'
    ]
    
    if sender.__name__ in excluded_models:
        return
    
    # إذا كان الكائن موجود مسبقاً (تحديث)
    if instance.pk:
        try:
            previous_instance = sender.objects.get(pk=instance.pk)
            _previous_values[instance.pk] = {}
            
            # حفظ القيم المهمة
            important_fields = ['name', 'total_amount', 'invoice_number', 'invoice_date', 
                              'customer', 'supplier', 'phone', 'email', 'address', 
                              'is_active', 'price', 'quantity', 'description',
                              'account_name', 'account_number', 'balance', 'status']
            
            for field in important_fields:
                if hasattr(previous_instance, field):
                    _previous_values[instance.pk][field] = getattr(previous_instance, field)
        except:
            pass


@receiver(post_save)
def log_model_save(sender, instance, created, **kwargs):
    """تسجيل عمليات الحفظ/التحديث"""
    # تجنب تسجيل AuditLog نفسه لمنع الحلقة اللانهائية
    if sender == AuditLog:
        return
    
    # تجنب تسجيل جلسات المستخدمين وبعض النماذج الأخرى
    excluded_models = [
        'Session', 'LogEntry', 'Migration', 'SystemNotification',
        'ContentType', 'Permission', 'Group'
    ]
    
    if sender.__name__ in excluded_models:
        return
    
    # محاولة الحصول على المستخدم من الـ context
    user = getattr(instance, '_audit_user', None)
    if not user:
        user = get_current_user()
    
    if not user or not user.is_authenticated:
        return
    
    action_type = 'create' if created else 'update'
    
    # الحصول على وصف مفصل
    description = get_model_description(instance, action_type)
    
    # إضافة تفاصيل التغييرات للتحديثات
    if not created and instance.pk in _previous_values:
        changes = get_field_changes(instance, _previous_values[instance.pk])
        if changes:
            description += f" - التغييرات: {changes}"
        # تنظيف القيم السابقة
        del _previous_values[instance.pk]
    
    # الحصول على الطلب الحالي
    request = get_current_request()
    
    log_activity(user, action_type, instance, description, request)


@receiver(post_delete)
def log_model_delete(sender, instance, **kwargs):
    """تسجيل عمليات الحذف"""
    # تجنب تسجيل AuditLog نفسه
    if sender == AuditLog:
        return
    
    # تجنب تسجيل النماذج المستثناة
    excluded_models = [
        'Session', 'LogEntry', 'Migration', 'SystemNotification',
        'ContentType', 'Permission', 'Group'
    ]
    
    if sender.__name__ in excluded_models:
        return
    
    # محاولة الحصول على المستخدم
    user = getattr(instance, '_audit_user', None)
    if not user:
        user = get_current_user()
    
    if not user or not user.is_authenticated:
        return
    
    description = get_model_description(instance, 'delete')
    
    # الحصول على الطلب الحالي
    request = get_current_request()
    
    log_activity(user, 'delete', instance, description, request)


# Signals لتسجيل عمليات تسجيل الدخول والخروج
@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """تسجيل عملية تسجيل الدخول"""
    try:
        description = f"تسجيل الدخول للمستخدم: {user.get_full_name() or user.username}"
        
        # إنشاء كائن وهمي للمستخدم لتسجيل النشاط
        class LoginActivity:
            def __init__(self, user):
                self.id = user.id
                self.pk = user.id
            
            def __str__(self):
                return f"تسجيل الدخول - {user.get_full_name() or user.username}"
        
        login_obj = LoginActivity(user)
        log_activity(user, 'login', login_obj, description, request)
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error logging user login: {e}")


@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    """تسجيل عملية تسجيل الخروج"""
    try:
        if not user:
            return
            
        description = f"تسجيل الخروج للمستخدم: {user.get_full_name() or user.username}"
        
        # إنشاء كائن وهمي للمستخدم لتسجيل النشاط
        class LogoutActivity:
            def __init__(self, user):
                self.id = user.id
                self.pk = user.id
            
            def __str__(self):
                return f"تسجيل الخروج - {user.get_full_name() or user.username}"
        
        logout_obj = LogoutActivity(user)
        log_activity(user, 'logout', logout_obj, description, request)
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error logging user logout: {e}")


# دالة لتسجيل أنشطة مخصصة من Views
def log_view_activity(request, action_type, obj, description):
    """تسجيل نشاط مخصص من view"""
    if hasattr(request, 'user') and request.user.is_authenticated:
        log_activity(request.user, action_type, obj, description, request)


# دالة لتسجيل أنشطة البحث والفلترة
def log_search_activity(request, search_query, model_name, results_count=None):
    """تسجيل نشاط البحث"""
    if hasattr(request, 'user') and request.user.is_authenticated:
        description = f"بحث في {model_name}: '{search_query}'"
        if results_count is not None:
            description += f" (النتائج: {results_count})"
        
        class SearchActivity:
            def __init__(self, query):
                self.id = hash(query) % 1000000
                self.pk = self.id
                self.query = query
            
            def __str__(self):
                return f"بحث: {self.query}"
        
        search_obj = SearchActivity(search_query)
        log_activity(request.user, 'view', search_obj, description, request)


# دالة لتسجيل تصدير التقارير
def log_export_activity(request, export_type, file_name, format_type='PDF'):
    """تسجيل نشاط تصدير التقارير"""
    if hasattr(request, 'user') and request.user.is_authenticated:
        description = f"تصدير {export_type} بصيغة {format_type}: {file_name}"
        
        class ExportActivity:
            def __init__(self, export_info):
                self.id = hash(export_info) % 1000000
                self.pk = self.id
                self.export_info = export_info
            
            def __str__(self):
                return f"تصدير: {self.export_info}"
        
        export_obj = ExportActivity(f"{export_type} - {file_name}")
        log_activity(request.user, 'view', export_obj, description, request)


# دالة لتسجيل أنشطة الطباعة
def log_print_activity(request, document_type, document_id):
    """تسجيل نشاط الطباعة"""
    if hasattr(request, 'user') and request.user.is_authenticated:
        description = f"طباعة {document_type} رقم {document_id}"
        
        class PrintActivity:
            def __init__(self, print_info):
                self.id = hash(print_info) % 1000000
                self.pk = self.id
                self.print_info = print_info
            
            def __str__(self):
                return f"طباعة: {self.print_info}"
        
        print_obj = PrintActivity(f"{document_type} - {document_id}")
        log_activity(request.user, 'view', print_obj, description, request)
