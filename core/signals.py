from django.db.models.signals import post_save, post_delete, pre_save, pre_delete
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.db.models.signals import m2m_changed
from .models import AuditLog
from .middleware import get_current_user, get_current_request
from .utils import get_client_ip
from django.conf import settings


"""تم نقل دالة get_client_ip إلى core.utils.get_client_ip لتجنب التكرار."""

from django.contrib.auth import get_user_model

from django.contrib.auth.models import Permission, Group

User = get_user_model()

def log_activity(user, action_type, obj, description, request=None):
    """تسجيل نشاط في سجل المراجعة"""
    try:
        # أثناء الاختبارات نتجنب كتابة AuditLog الفعلي لتفادي قيود FK ومشاكل teardown
        if getattr(settings, 'TESTING', False):
            return
        if not user or not user.is_authenticated:
            return
        
        # تحديد نوع المحتوى
        content_type = obj.__class__.__name__ if obj else ''
        object_id = getattr(obj, 'id', None) or getattr(obj, 'pk', None) if obj else None
        
        # الحصول على عنوان IP
        ip_address = None
        if request:
            ip_address = get_client_ip(request)
        
        # إنشاء سجل المراجعة مع حماية من تضارب IDs
        AuditLog.objects.create(
            user=user,
            action_type=action_type,
            content_type=content_type,
            object_id=object_id,
            description=description,
            ip_address=ip_address
        )
    except Exception as e:
        # إذا كان الخطأ متعلق بـ primary key constraint
        if 'duplicate key' in str(e).lower() or 'unique constraint' in str(e).lower():
            try:
                # إعادة تعيين sequence AuditLog
                from django.db import connection
                with connection.cursor() as cursor:
                    cursor.execute("SELECT MAX(id) FROM core_auditlog")
                    max_id = cursor.fetchone()[0] or 0
                    cursor.execute(f"SELECT setval('core_auditlog_id_seq', {max_id + 1}, false)")
                
                # محاولة مرة أخرى
                AuditLog.objects.create(
                    user=user,
                    action_type=action_type,
                    content_type=content_type,
                    object_id=object_id,
                    description=description,
                    ip_address=ip_address
                )
            except Exception as retry_e:
                # في حالة حدوث خطأ، لا نريد أن يتوقف النظام
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"فشل في تسجيل نشاط المستخدم حتى بعد إعادة تعيين sequence: {retry_e}")
        else:
            # في حالة حدوث خطأ، لا نريد أن يتوقف النظام
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error logging activity: {e}")


# دالة مساعدة لتسجيل الأنشطة من الـ Views
def log_user_activity(request, action_type, obj, description):
    """دالة مساعدة لتسجيل الأنشطة من الـ Views"""
    if hasattr(request, 'user'):
        log_activity(request.user, action_type, obj, description, request)

def sync_user_permissions(user):
    """تزامن صلاحيات المستخدم مع صلاحيات مجموعاته"""
    perms = Permission.objects.filter(group__user=user)
    user.user_permissions.set(perms)
    user.save(update_fields=["updated_at"])

def sync_group_users_permissions(group):
    """تحديث صلاحيات جميع أعضاء المجموعة عند تعديل صلاحيات المجموعة"""
    for user in group.user_set.all():
        sync_user_permissions(user)

# عند تعديل صلاحيات المجموعة
def group_permissions_changed(sender, instance, action, **kwargs):
    if action in ["post_add", "post_remove", "post_clear"]:
        sync_group_users_permissions(instance)

m2m_changed.connect(group_permissions_changed, sender=Group.permissions.through)

# عند تعديل عضوية المستخدم في المجموعات
def user_groups_changed(sender, instance, action, **kwargs):
    if action in ["post_add", "post_remove", "post_clear"]:
        sync_user_permissions(instance)

m2m_changed.connect(user_groups_changed, sender=User.groups.through)

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
        'DocumentSequence': f'تسلسل مستند: {getattr(instance, "get_document_type_display", lambda: getattr(instance, "document_type", "غير محدد"))()}',
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


def setup_initial_system_data():
    """إعداد البيانات الأساسية للنظام عند بدء التشغيل لأول مرة"""
    try:
        from django.contrib.auth import get_user_model
        from inventory.models import Warehouse
        from .models import DocumentSequence, CompanySettings
        
        User = get_user_model()
        
        # التحقق من وجود أي مستخدمين (إذا لم يوجد أي مستخدم، فهذا بدء جديد)
        if User.objects.count() == 0:
            return  # لا نفعل شيء إذا لم يكن هناك مستخدمين
        
        # التحقق من وجود مستودع "Main" وإنشاؤه إذا لم يكن موجوداً
        if not Warehouse.objects.filter(name='Main').exists():
            try:
                # إنشاء مستودع "Main"
                main_warehouse = Warehouse.objects.create(
                    name='Main',
                    code='MAIN',
                    address='الموقع الرئيسي',
                    is_active=True,
                )
                print(f"تم إنشاء المستودع الرئيسي: {main_warehouse.name}")
            except Exception as e:
                print(f"خطأ في إنشاء المستودع الرئيسي: {e}")
        
        # التحقق من وجود Document Sequences وإنشاؤها إذا لم تكن موجودة
        sequences = [
            {'document_type': 'sales_invoice', 'prefix': 'INV'},
            {'document_type': 'purchase_invoice', 'prefix': 'PUR'},
            {'document_type': 'sales_return', 'prefix': 'SRN'},
            {'document_type': 'purchase_return', 'prefix': 'PRN'},
            {'document_type': 'receipt_voucher', 'prefix': 'RCP'},
            {'document_type': 'payment_voucher', 'prefix': 'PAY'},
            {'document_type': 'journal_entry', 'prefix': 'JE'},
        ]
        
        for seq_data in sequences:
            if not DocumentSequence.objects.filter(document_type=seq_data['document_type']).exists():
                try:
                    DocumentSequence.objects.create(
                        document_type=seq_data['document_type'],
                        prefix=seq_data['prefix'],
                        digits=6,
                        current_number=1,
                    )
                    print(f"تم إنشاء تسلسل: {seq_data['document_type']}")
                except Exception as e:
                    print(f"خطأ في إنشاء التسلسل {seq_data['document_type']}: {e}")
        
        # التأكد من وجود إعدادات الشركة
        if not CompanySettings.objects.exists():
            try:
                CompanySettings.objects.create(
                    company_name='FinsPilot',
                    currency='JOD',
                )
                print("تم إنشاء إعدادات الشركة الافتراضية")
            except Exception as e:
                print(f"خطأ في إنشاء إعدادات الشركة: {e}")
                
    except Exception as e:
        # في حالة حدوث خطأ، لا نريد أن يتوقف النظام
        print(f"خطأ في إعداد البيانات الأساسية للنظام: {e}")


# استدعاء دالة الإعداد عند تحميل النظام
try:
    from django.db import connection
    # التحقق من وجود الجداول قبل تشغيل الإعداد
    if 'core_documentsquence' in connection.introspection.table_names():
        setup_initial_system_data()
except Exception:
    pass  # تجاهل الأخطاء عند التحميل


# ===============================
# Product Signals
# ===============================

@receiver(post_save, sender='products.Product')
def product_post_save(sender, instance, created, **kwargs):
    """تسجيل إنشاء أو تحديث المنتج"""
    user = get_current_user()
    request = get_current_request()
    
    if created:
        product_type = "خدمة" if hasattr(instance, 'product_type') and instance.product_type == 'service' else "منتج مادي"
        description = f'تم إنشاء {product_type} جديد: {instance.name} (كود: {instance.code})'
        log_activity(user, 'CREATE', instance, description, request)
    else:
        # التحقق من التغييرات المهمة
        old_instance = sender.objects.filter(pk=instance.pk).first()
        if old_instance:
            changes = []
            if hasattr(instance, '_state') and hasattr(instance._state, 'fields_cache'):
                # فحص التغييرات في الحقول المهمة
                important_fields = ['name', 'product_type', 'sale_price', 'is_active']
                for field in important_fields:
                    if hasattr(old_instance, field) and hasattr(instance, field):
                        old_value = getattr(old_instance, field)
                        new_value = getattr(instance, field)
                        if old_value != new_value:
                            field_name_ar = {
                                'name': 'الاسم',
                                'sale_price': 'سعر البيع', 
                                'is_active': 'حالة النشاط'
                            }.get(field, field)
                            changes.append(f'{field_name_ar}: {old_value} → {new_value}')
            
            if changes:
                description = f'تم تحديث المنتج: {instance.name} - التغييرات: {", ".join(changes)}'
            else:
                description = f'تم تحديث المنتج: {instance.name}'
            
            log_activity(user, 'UPDATE', instance, description, request)


@receiver(post_delete, sender='products.Product')
def product_post_delete(sender, instance, **kwargs):
    """تسجيل حذف المنتج"""
    user = get_current_user()
    request = get_current_request()
    
    product_type = "خدمة" if hasattr(instance, 'product_type') and instance.product_type == 'service' else "منتج مادي"
    description = f'تم حذف {product_type}: {instance.name} (كود: {instance.code})'
    log_activity(user, 'DELETE', instance, description, request)


@receiver(post_save, sender='products.Category')
def category_post_save(sender, instance, created, **kwargs):
    """تسجيل إنشاء أو تحديث فئة المنتج"""
    user = get_current_user()
    request = get_current_request()
    
    if created:
        description = f'تم إنشاء فئة منتجات جديدة: {instance.name}'
        log_activity(user, 'CREATE', instance, description, request)
    else:
        description = f'تم تحديث فئة المنتجات: {instance.name}'
        log_activity(user, 'UPDATE', instance, description, request)


@receiver(post_delete, sender='products.Category')
def category_post_delete(sender, instance, **kwargs):
    """تسجيل حذف فئة المنتج"""
    user = get_current_user()
    request = get_current_request()
    
    description = f'تم حذف فئة المنتجات: {instance.name}'
    log_activity(user, 'DELETE', instance, description, request)
