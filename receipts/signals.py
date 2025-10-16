"""
Signals for Payment Receipts
معالجة الإشارات التلقائية لسندات القبض
"""
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.db import transaction as db_transaction
from django.db import models
from decimal import Decimal

from .models import PaymentReceipt


@receiver(post_save, sender=PaymentReceipt)
def create_cashbox_transaction_on_receipt(sender, instance, created, **kwargs):
    """
    إنشاء حركة صندوق تلقائياً عند إنشاء سند قبض نقدي
    Create cashbox transaction automatically when cash receipt voucher is created
    """
    # تطبيق فقط عند الإنشاء الجديد
    if created and instance.payment_type == 'cash' and instance.cashbox:
        from cashboxes.models import CashboxTransaction
        
        # التحقق من عدم وجود حركة مسبقاً
        existing = CashboxTransaction.objects.filter(
            reference_type='receipt',
            reference_id=instance.id
        ).exists()
        
        if not existing:
            CashboxTransaction.objects.create(
                cashbox=instance.cashbox,
                transaction_type='deposit',
                amount=instance.amount,
                description=f'سند قبض {instance.receipt_number} - {instance.customer.name}',
                date=instance.date,
                reference_type='receipt',
                reference_id=instance.id,
                created_by=instance.created_by
            )
            print(f"✓ تم إنشاء حركة صندوق لسند القبض {instance.receipt_number}")


@receiver(post_save, sender=PaymentReceipt)
def create_bank_transaction_on_receipt(sender, instance, created, **kwargs):
    """
    إنشاء حركة بنكية تلقائياً عند إنشاء سند قبض بتحويل بنكي
    """
    if created and instance.payment_type == 'bank_transfer' and instance.bank_account:
        from banks.models import BankTransaction
        
        # التحقق من عدم وجود حركة مسبقاً
        existing = BankTransaction.objects.filter(
            reference_number=instance.bank_transfer_reference
        ).exists()
        
        if not existing:
            BankTransaction.objects.create(
                bank=instance.bank_account,
                transaction_type='deposit',
                date=instance.bank_transfer_date if instance.bank_transfer_date else instance.date,
                amount=instance.amount,
                reference_number=instance.bank_transfer_reference,
                description=f'سند قبض {instance.receipt_number} - {instance.customer.name}',
                created_by=instance.created_by
            )
            print(f"✓ تم إنشاء حركة بنكية لسند القبض {instance.receipt_number}")


@receiver(post_save, sender=PaymentReceipt)
def create_account_transaction_on_receipt(sender, instance, created, **kwargs):
    """
    إنشاء حركة حساب للعميل تلقائياً عند إنشاء سند قبض
    """
    if created:
        from accounts.models import AccountTransaction
        
        # التحقق من عدم وجود حركة مسبقاً
        existing = AccountTransaction.objects.filter(
            reference_type='receipt',
            reference_id=instance.id
        ).exists()
        
        if not existing:
            AccountTransaction.create_transaction(
                customer_supplier=instance.customer,
                transaction_type='receipt',
                direction='credit',  # دائن - يقلل من رصيد العميل
                amount=instance.amount,
                reference_type='receipt',
                reference_id=instance.id,
                description=f'سند قبض رقم {instance.receipt_number}',
                notes=f'نوع الدفع: {instance.get_payment_type_display()}',
                user=instance.created_by,
                date=instance.date
            )
            print(f"✓ تم إنشاء حركة حساب لسند القبض {instance.receipt_number}")


@receiver(post_save, sender=PaymentReceipt)
def update_customer_balance_on_receipt(sender, instance, created, **kwargs):
    """
    تحديث رصيد العميل تلقائياً عند إنشاء أو تعديل سند قبض
    Update customer balance automatically when receipt voucher is created or modified
    
    IFRS Compliance:
    - IAS 32: Financial Instruments Presentation
    - IFRS 9: Financial Instruments (Recognition and Measurement)
    """
    # تجنب التحديث المتكرر
    if getattr(instance, '_skip_balance_update', False):
        return
    
    # تحديث الرصيد للعملاء فقط
    if instance.customer:
        with db_transaction.atomic():
            customer = instance.customer
            
            # حساب رصيد العميل من جميع الحركات
            from sales.models import SalesInvoice
            from .models import PaymentReceipt
            
            # إجمالي المبيعات (مدين - تزيد الذمم المدينة)
            total_sales = SalesInvoice.objects.filter(
                customer=customer
            ).aggregate(
                total=models.Sum('total_amount')
            )['total'] or Decimal('0.000')
            
            # إجمالي المقبوضات (دائن - تقلل الذمم المدينة)
            total_receipts = PaymentReceipt.objects.filter(
                customer=customer,
                is_reversed=False
            ).aggregate(
                total=models.Sum('amount')
            )['total'] or Decimal('0.000')
            
            # الرصيد = المبيعات - المقبوضات
            # Positive balance = customer owes us (debit balance)
            new_balance = total_sales - total_receipts
            
            # تحديث رصيد العميل
            if customer.balance != new_balance:
                customer._skip_signal = True  # تجنب تفعيل إشارة التحديث في نموذج العميل
                customer.balance = new_balance
                customer.save(update_fields=['balance'])
                customer._skip_signal = False
                
                print(f"✓ تم تحديث رصيد العميل {customer.name}: {new_balance}")


@receiver(post_delete, sender=PaymentReceipt)
def update_customer_balance_on_receipt_delete(sender, instance, **kwargs):
    """
    تحديث رصيد العميل عند حذف سند قبض
    Update customer balance when receipt voucher is deleted
    """
    if instance.customer:
        with db_transaction.atomic():
            customer = instance.customer
            
            # إعادة حساب رصيد العميل
            from sales.models import SalesInvoice
            from .models import PaymentReceipt
            
            total_sales = SalesInvoice.objects.filter(
                customer=customer
            ).aggregate(
                total=models.Sum('total_amount')
            )['total'] or Decimal('0.000')
            
            total_receipts = PaymentReceipt.objects.filter(
                customer=customer,
                is_reversed=False
            ).exclude(id=instance.id).aggregate(  # استثناء السند المحذوف
                total=models.Sum('amount')
            )['total'] or Decimal('0.000')
            
            new_balance = total_sales - total_receipts
            
            customer._skip_signal = True
            customer.balance = new_balance
            customer.save(update_fields=['balance'])
            customer._skip_signal = False
            
            print(f"✓ تم تحديث رصيد العميل بعد الحذف {customer.name}: {new_balance}")


@receiver(pre_save, sender=PaymentReceipt)
def handle_receipt_reversal(sender, instance, **kwargs):
    """
    معالجة عكس سند القبض - إنشاء حركة صندوق عكسية
    Handle receipt voucher reversal - create reverse cashbox transaction
    
    IFRS Compliance:
    - IAS 8: Accounting Policies, Changes in Accounting Estimates and Errors
    - IAS 1: Presentation of Financial Statements (Correction of errors)
    """
    # التحقق من أن السند موجود مسبقاً (ليس جديداً)
    if instance.pk:
        try:
            # الحصول على النسخة القديمة من قاعدة البيانات
            old_instance = PaymentReceipt.objects.get(pk=instance.pk)
            
            # التحقق من أن السند تم عكسه للتو (من False إلى True)
            if not old_instance.is_reversed and instance.is_reversed:
                # عكس حركة الصندوق للمقبوضات النقدية فقط
                if instance.payment_type == 'cash' and instance.cashbox:
                    from cashboxes.models import CashboxTransaction
                    from django.utils import timezone
                    
                    # البحث عن حركة الصندوق الأصلية
                    original_transaction = CashboxTransaction.objects.filter(
                        reference_type='receipt',
                        reference_id=instance.id,
                        transaction_type='deposit'
                    ).first()
                    
                    if original_transaction:
                        # إنشاء حركة عكسية (سحب)
                        CashboxTransaction.objects.create(
                            cashbox=instance.cashbox,
                            transaction_type='withdrawal',
                            amount=original_transaction.amount,
                            description=f'عكس سند قبض {instance.receipt_number} - {instance.reversal_reason or "بدون سبب"}',
                            date=timezone.now().date(),
                            reference_type='receipt_reversal',
                            reference_id=instance.id,
                            created_by=instance.reversed_by or instance.created_by
                        )
                        print(f"✓ تم إنشاء حركة صندوق عكسية لسند القبض {instance.receipt_number}")
                
                # عكس حركة البنك للتحويلات البنكية
                elif instance.payment_type == 'bank_transfer' and instance.bank_account:
                    from banks.models import BankTransaction
                    from django.utils import timezone
                    
                    # البحث عن حركة البنك الأصلية
                    original_transaction = BankTransaction.objects.filter(
                        reference_number__in=[instance.bank_transfer_reference, instance.receipt_number],
                        transaction_type='deposit'
                    ).first()
                    
                    if original_transaction:
                        # إنشاء حركة بنك عكسية
                        BankTransaction.objects.create(
                            bank=instance.bank_account,
                            transaction_type='withdrawal',
                            amount=original_transaction.amount,
                            description=f'عكس سند قبض {instance.receipt_number} - {instance.reversal_reason or "بدون سبب"}',
                            reference_number=f'REV-{instance.receipt_number}',
                            date=timezone.now().date(),
                            created_by=instance.reversed_by or instance.created_by
                        )
                        print(f"✓ تم إنشاء حركة بنك عكسية لسند القبض {instance.receipt_number}")
                
        except PaymentReceipt.DoesNotExist:
            pass
        except Exception as e:
            print(f"خطأ في معالجة عكس سند القبض: {e}")
