from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from .models import AccountTransaction


@receiver(post_save, sender=AccountTransaction)
def log_account_transaction_activity(sender, instance, created, **kwargs):
    """تسجيل إنشاء أو تعديل المعاملات المالية في سجل الأنشطة"""
    try:
        from core.models import AuditLog
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        
        # الحصول على المستخدم من instance أو النظام
        user = getattr(instance, 'created_by', None)
        if not user:
            # محاولة الحصول على المستخدم الحالي من context
            # في هذه الحالة سنستخدم المستخدم الأول كبديل
            user = User.objects.filter(is_active=True).first()
        
        if created:
            action_type = 'create'
            description = _(
                'تم إنشاء معاملة %(transaction_type)s جديدة رقم %(transaction_number)s '
                'للعميل/المورد %(customer_supplier)s بمبلغ %(amount)s %(direction)s'
            ) % {
                'transaction_type': instance.get_transaction_type_display(),
                'transaction_number': instance.transaction_number,
                'customer_supplier': instance.customer_supplier.name,
                'amount': instance.amount,
                'direction': instance.get_direction_display()
            }
        else:
            action_type = 'update'
            description = _(
                'تم تعديل معاملة %(transaction_type)s رقم %(transaction_number)s '
                'للعميل/المورد %(customer_supplier)s'
            ) % {
                'transaction_type': instance.get_transaction_type_display(),
                'transaction_number': instance.transaction_number,
                'customer_supplier': instance.customer_supplier.name
            }
        
        AuditLog.objects.create(
            user=user,
            action_type=action_type,
            content_type='AccountTransaction',
            object_id=instance.id,
            description=description,
            ip_address='127.0.0.1'  # افتراضي للعمليات الداخلية
        )
        
    except Exception:
        # تجاهل أخطاء تسجيل الأنشطة لتجنب التأثير على العملية الأساسية
        pass


@receiver(post_delete, sender=AccountTransaction)
def log_account_transaction_deletion(sender, instance, **kwargs):
    """تسجيل حذف المعاملات المالية في سجل الأنشطة"""
    try:
        from core.models import AuditLog
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        
        # محاولة الحصول على المستخدم الحالي
        user = User.objects.filter(is_active=True).first()
        
        description = _(
            'تم حذف معاملة %(transaction_type)s رقم %(transaction_number)s '
            'للعميل/المورد %(customer_supplier)s بمبلغ %(amount)s %(direction)s'
        ) % {
            'transaction_type': instance.get_transaction_type_display(),
            'transaction_number': instance.transaction_number,
            'customer_supplier': instance.customer_supplier.name,
            'amount': instance.amount,
            'direction': instance.get_direction_display()
        }
        
        AuditLog.objects.create(
            user=user,
            action_type='delete',
            content_type='AccountTransaction',
            object_id=instance.id,
            description=description,
            ip_address='127.0.0.1'
        )
        
    except Exception:
        # تجاهل أخطاء تسجيل الأنشطة
        pass
