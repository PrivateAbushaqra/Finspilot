from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
from .models import SalesInvoice


@receiver(post_save, sender=SalesInvoice)
def create_cashbox_transaction_for_sales(sender, instance, created, **kwargs):
    """إنشاء معاملة صندوق تلقائياً عند إنشاء فاتورة مبيعات نقدية"""
    try:
        from cashboxes.models import CashboxTransaction
        from core.models import AuditLog
        
        # التحقق من أن الفاتورة جديدة ونقدية
        if created and instance.payment_type == 'cash' and instance.total_amount > 0:
            # تحديد الصندوق المناسب
            cashbox = None
            
            # إذا كان المستخدم من نوع pos_user، استخدم صندوقه الخاص
            if instance.created_by.user_type == 'pos_user':
                from cashboxes.models import Cashbox
                cashbox = Cashbox.objects.filter(responsible_user=instance.created_by).first()
                
                # إذا لم يكن له صندوق، إنشاء واحد تلقائياً
                if not cashbox:
                    # اسم الصندوق = اسم المستخدم
                    cashbox_name = instance.created_by.username
                    
                    # الحصول على العملة الأساسية
                    from core.models import CompanySettings
                    company_settings = CompanySettings.get_settings()
                    currency = 'JOD'
                    if company_settings and company_settings.currency:
                        currency = company_settings.currency
                    
                    cashbox = Cashbox.objects.create(
                        name=cashbox_name,
                        description=_('صندوق مستخدم نقطة البيع: %(full_name)s') % {
                            'full_name': instance.created_by.get_full_name() or instance.created_by.username
                        },
                        balance=Decimal('0.000'),
                        currency=currency,
                        location=_('نقطة البيع - %(username)s') % {'username': instance.created_by.username},
                        responsible_user=instance.created_by,
                        is_active=True
                    )
                    
                    # تسجيل إنشاء الصندوق في سجل الأنشطة
                    try:
                        AuditLog.objects.create(
                            user=instance.created_by,
                            action='create',
                            model_name='Cashbox',
                            object_id=cashbox.id,
                            object_repr=str(cashbox),
                            description=_('تم إنشاء صندوق تلقائياً لمستخدم نقطة البيع: %(username)s') % {'username': instance.created_by.username},
                            ip_address='127.0.0.1'
                        )
                    except Exception as log_error:
                        print(f"خطأ في تسجيل نشاط إنشاء الصندوق: {log_error}")
            
            # إذا لم يتم تحديد صندوق، استخدم الصندوق الرئيسي أو إنشاء واحد
            if not cashbox:
                from cashboxes.models import Cashbox
                cashbox = Cashbox.objects.filter(name__icontains='رئيسي', is_active=True).first()
                if not cashbox:
                    cashbox = Cashbox.objects.filter(is_active=True).first()
                if not cashbox:
                    # إنشاء صندوق رئيسي افتراضي
                    cashbox = Cashbox.objects.create(
                        name='الصندوق الرئيسي',
                        description='الصندوق الرئيسي للمبيعات النقدية',
                        balance=0,
                        location='المكتب الرئيسي',
                        is_active=True
                    )
            
            # ربط الفاتورة بالصندوق
            if cashbox and not instance.cashbox:
                instance.cashbox = cashbox
                instance.save(update_fields=['cashbox'])
            
            # إنشاء معاملة إيداع في الصندوق
            if cashbox:
                # CashboxTransaction model does not have reference_type/reference_id fields
                # (we avoid adding DB fields for now). Store invoice identity in the description
                transaction = CashboxTransaction.objects.create(
                    cashbox=cashbox,
                    transaction_type='deposit',
                    amount=instance.total_amount,
                    date=instance.date,
                    description=f'مبيعات نقدية - فاتورة رقم {instance.invoice_number}',
                    created_by=instance.created_by
                )
                
                # تحديث رصيد الصندوق
                cashbox.balance += instance.total_amount
                cashbox.save(update_fields=['balance'])
                
                # تسجيل النشاط في سجل الأنشطة
                try:
                    AuditLog.objects.create(
                        user=instance.created_by,
                        action='create',
                        model_name='CashboxTransaction',
                        object_id=transaction.id,
                        object_repr=str(transaction),
                        description=_('تم إيداع %(amount)s في الصندوق %(cashbox)s من فاتورة مبيعات رقم %(invoice)s') % {
                            'amount': instance.total_amount,
                            'cashbox': cashbox.name,
                            'invoice': instance.invoice_number
                        },
                        ip_address='127.0.0.1'
                    )
                except Exception as log_error:
                    print(f"خطأ في تسجيل نشاط معاملة الصندوق: {log_error}")
                
                print(f"تم إيداع {instance.total_amount} في {cashbox.name} من فاتورة {instance.invoice_number}")
                
    except Exception as e:
        print(f"خطأ في إنشاء معاملة الصندوق لفاتورة {instance.invoice_number}: {e}")
        # لا نوقف عملية إنشاء الفاتورة في حالة فشل إنشاء معاملة الصندوق
        pass


@receiver(post_save, sender=SalesInvoice)
def update_cashbox_transaction_on_invoice_change(sender, instance, created, **kwargs):
    """تحديث معاملة الصندوق عند تعديل الفاتورة"""
    try:
        from cashboxes.models import CashboxTransaction
        
        # إذا لم تكن الفاتورة جديدة وكانت نقدية
        if not created and instance.payment_type == 'cash':
            # البحث عن المعاملة المرتبطة بالفاتورة: نطابق وصف المعاملة الذي يحتوي رقم الفاتورة
            try:
                transaction = CashboxTransaction.objects.filter(
                    transaction_type='deposit',
                    description__icontains=str(instance.invoice_number)
                ).first()
            except Exception:
                transaction = None
            
            if transaction:
                # حساب الفرق في المبلغ
                amount_difference = instance.total_amount - transaction.amount
                
                if amount_difference != 0:
                    # تحديث مبلغ المعاملة
                    transaction.amount = instance.total_amount
                    transaction.description = f'مبيعات نقدية - فاتورة رقم {instance.invoice_number} (محدثة)'
                    transaction.save()
                    
                    # تحديث رصيد الصندوق
                    if transaction.cashbox:
                        transaction.cashbox.balance += amount_difference
                        transaction.cashbox.save(update_fields=['balance'])
                        
                        print(f"تم تحديث معاملة الصندوق للفاتورة {instance.invoice_number}")
                        
    except Exception as e:
        print(f"خطأ في تحديث معاملة الصندوق للفاتورة {instance.invoice_number}: {e}")
        pass
