from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from .models import AccountTransaction


@receiver(post_save, sender=AccountTransaction)
def update_customer_supplier_balance(sender, instance, created, **kwargs):
    """تحديث رصيد العميل/المورد عند إنشاء معاملة جديدة"""
    if created:
        try:
            customer_supplier = instance.customer_supplier
            
            # حساب التغيير في الرصيد
            if instance.direction == 'debit':
                # مدين - يزيد من رصيد العميل (دين على العميل)
                customer_supplier.balance += instance.amount
            elif instance.direction == 'credit':
                # دائن - يقلل من رصيد العميل (دفع من العميل)
                customer_supplier.balance -= instance.amount
            
            # استخدام flag لتجنب الفحص التلقائي
            customer_supplier._skip_balance_check = True
            customer_supplier.save(update_fields=['balance'])
            if hasattr(customer_supplier, '_skip_balance_check'):
                delattr(customer_supplier, '_skip_balance_check')
        except Exception as e:
            # تسجيل الخطأ دون إيقاف العملية
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'خطأ في تحديث رصيد العميل/المورد: {e}')


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
def recalculate_balance_and_log_deletion(sender, instance, **kwargs):
    """إعادة حساب رصيد العميل/المورد وتسجيل حذف المعاملة المالية في سجل الأنشطة"""
    try:
        from core.models import AuditLog
        from django.contrib.auth import get_user_model
        from decimal import Decimal
        
        User = get_user_model()
        
        # محاولة الحصول على المستخدم الحالي
        user = User.objects.filter(is_active=True).first()
        
        # إعادة حساب رصيد العميل/المورد من جميع الحركات المتبقية
        customer_supplier = instance.customer_supplier
        old_balance = customer_supplier.balance
        
        # حساب الرصيد الجديد بناءً على جميع الحركات المتبقية
        transactions = AccountTransaction.objects.filter(
            customer_supplier=customer_supplier
        ).order_by('date', 'created_at')
        
        new_balance = Decimal('0')
        for transaction in transactions:
            if transaction.direction == 'debit':
                new_balance += transaction.amount
            else:
                new_balance -= transaction.amount
        
        # تحديث رصيد العميل/المورد
        customer_supplier.balance = new_balance
        customer_supplier.save(update_fields=['balance'])
        
        print(f"✅ تم تحديث رصيد {customer_supplier.name} بعد حذف المعاملة: {old_balance} → {new_balance}")
        
        description = _(
            'تم حذف معاملة %(transaction_type)s رقم %(transaction_number)s '
            'للعميل/المورد %(customer_supplier)s بمبلغ %(amount)s %(direction)s. '
            'الرصيد تم تحديثه من %(old_balance)s إلى %(new_balance)s'
        ) % {
            'transaction_type': instance.get_transaction_type_display(),
            'transaction_number': instance.transaction_number,
            'customer_supplier': instance.customer_supplier.name,
            'amount': instance.amount,
            'direction': instance.get_direction_display(),
            'old_balance': old_balance,
            'new_balance': new_balance
        }
        
        AuditLog.objects.create(
            user=user,
            action_type='delete',
            content_type='AccountTransaction',
            object_id=instance.id,
            description=description,
            ip_address='127.0.0.1'
        )
        
    except Exception as e:
        # تسجيل الخطأ
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'خطأ في إعادة حساب الرصيد بعد حذف المعاملة: {e}')
        import traceback
        traceback.print_exc()
