"""
Signals for Payment Vouchers
معالجة الإشارات التلقائية لسندات الصرف
"""
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.db import transaction as db_transaction
from django.db import models
from decimal import Decimal

from .models import PaymentVoucher


@receiver(post_save, sender=PaymentVoucher)
def create_cashbox_transaction_on_payment(sender, instance, created, **kwargs):
    """
    إنشاء حركة صندوق تلقائياً عند إنشاء سند صرف نقدي
    Create cashbox transaction automatically when cash payment voucher is created
    """
    # تطبيق فقط عند الإنشاء الجديد
    if created and instance.payment_type == 'cash' and instance.cashbox:
        from cashboxes.models import CashboxTransaction
        
        # التحقق من عدم وجود حركة مسبقاً
        existing = CashboxTransaction.objects.filter(
            reference_type='payment',
            reference_id=instance.id
        ).exists()
        
        if not existing:
            CashboxTransaction.objects.create(
                cashbox=instance.cashbox,
                transaction_type='withdrawal',
                amount=-instance.amount,  # المبلغ سالب للسحب
                description=f'سند صرف {instance.voucher_number} - {instance.beneficiary_display}',
                date=instance.date,
                reference_type='payment',
                reference_id=instance.id,
                created_by=instance.created_by
            )
            print(f"✓ تم إنشاء حركة صندوق لسند الصرف {instance.voucher_number}")


@receiver(post_save, sender=PaymentVoucher)
def update_supplier_balance_on_payment(sender, instance, created, **kwargs):
    """
    تحديث رصيد المورد تلقائياً عند إنشاء أو تعديل سند صرف
    Update supplier balance automatically when payment voucher is created or modified
    
    IFRS Compliance:
    - IAS 32: Financial Instruments Presentation
    - IFRS 9: Financial Instruments (Recognition and Measurement)
    """
    # تجنب التحديث المتكرر
    if getattr(instance, '_skip_balance_update', False):
        return
    
    # تحديث الرصيد فقط للموردين
    if instance.supplier and instance.voucher_type == 'supplier':
        with db_transaction.atomic():
            supplier = instance.supplier
            
            # حساب رصيد المورد من جميع الحركات
            # Supplier payments decrease liability (debit)
            from purchases.models import PurchaseInvoice
            from .models import PaymentVoucher
            
            # إجمالي المشتريات (دائن - تزيد الذمم الدائنة)
            total_purchases = PurchaseInvoice.objects.filter(
                supplier=supplier
            ).aggregate(
                total=models.Sum('total_amount')
            )['total'] or Decimal('0.000')
            
            # إجمالي المدفوعات (مدين - تقلل الذمم الدائنة)
            total_payments = PaymentVoucher.objects.filter(
                supplier=supplier,
                voucher_type='supplier',
                is_reversed=False
            ).aggregate(
                total=models.Sum('amount')
            )['total'] or Decimal('0.000')
            
            # الرصيد = المشتريات - المدفوعات
            # Positive balance = we owe supplier (credit balance)
            new_balance = total_purchases - total_payments
            
            # تحديث رصيد المورد
            if supplier.balance != new_balance:
                supplier._skip_signal = True  # تجنب تفعيل إشارة التحديث في نموذج المورد
                supplier.balance = new_balance
                supplier.save(update_fields=['balance'])
                supplier._skip_signal = False
                
                print(f"✓ تم تحديث رصيد المورد {supplier.name}: {new_balance}")


@receiver(post_delete, sender=PaymentVoucher)
def update_supplier_balance_on_payment_delete(sender, instance, **kwargs):
    """
    تحديث رصيد المورد عند حذف سند صرف
    Update supplier balance when payment voucher is deleted
    """
    if instance.supplier and instance.voucher_type == 'supplier':
        with db_transaction.atomic():
            supplier = instance.supplier
            
            # إعادة حساب رصيد المورد
            from purchases.models import PurchaseInvoice
            from .models import PaymentVoucher
            
            total_purchases = PurchaseInvoice.objects.filter(
                supplier=supplier
            ).aggregate(
                total=models.Sum('total_amount')
            )['total'] or Decimal('0.000')
            
            total_payments = PaymentVoucher.objects.filter(
                supplier=supplier,
                voucher_type='supplier',
                is_reversed=False
            ).exclude(id=instance.id).aggregate(  # استثناء السند المحذوف
                total=models.Sum('amount')
            )['total'] or Decimal('0.000')
            
            new_balance = total_purchases - total_payments
            
            supplier._skip_signal = True
            supplier.balance = new_balance
            supplier.save(update_fields=['balance'])
            supplier._skip_signal = False
            
            print(f"✓ تم تحديث رصيد المورد بعد الحذف {supplier.name}: {new_balance}")


@receiver(pre_save, sender=PaymentVoucher)
def handle_payment_reversal(sender, instance, **kwargs):
    """
    معالجة عكس سند الصرف - إنشاء حركة صندوق عكسية
    Handle payment voucher reversal - create reverse cashbox transaction
    
    IFRS Compliance:
    - IAS 8: Accounting Policies, Changes in Accounting Estimates and Errors
    - IAS 1: Presentation of Financial Statements (Correction of errors)
    """
    # التحقق من أن السند موجود مسبقاً (ليس جديداً)
    if instance.pk:
        try:
            # الحصول على النسخة القديمة من قاعدة البيانات
            old_instance = PaymentVoucher.objects.get(pk=instance.pk)
            
            # التحقق من أن السند تم عكسه للتو (من False إلى True)
            if not old_instance.is_reversed and instance.is_reversed:
                # عكس حركة الصندوق للمدفوعات النقدية فقط
                if instance.payment_type == 'cash' and instance.cashbox:
                    from cashboxes.models import CashboxTransaction
                    from django.utils import timezone
                    
                    # البحث عن حركة الصندوق الأصلية
                    original_transaction = CashboxTransaction.objects.filter(
                        reference_type='payment',
                        reference_id=instance.id,
                        transaction_type='withdrawal'
                    ).first()
                    
                    if original_transaction:
                        # إنشاء حركة عكسية (إيداع)
                        CashboxTransaction.objects.create(
                            cashbox=instance.cashbox,
                            transaction_type='deposit',
                            amount=abs(original_transaction.amount),  # المبلغ موجب للإيداع
                            description=f'عكس سند صرف {instance.voucher_number} - {instance.reversal_reason or "بدون سبب"}',
                            date=timezone.now().date(),
                            reference_type='payment_reversal',
                            reference_id=instance.id,
                            created_by=instance.reversed_by or instance.created_by
                        )
                        print(f"✓ تم إنشاء حركة صندوق عكسية لسند الصرف {instance.voucher_number}")
                
                # عكس حركة البنك للتحويلات البنكية
                elif instance.payment_type == 'bank_transfer' and instance.bank:
                    from banks.models import BankTransaction
                    from django.utils import timezone
                    
                    # البحث عن حركة البنك الأصلية
                    original_transaction = BankTransaction.objects.filter(
                        reference_number__in=[instance.bank_reference, instance.voucher_number],
                        transaction_type='withdrawal'
                    ).first()
                    
                    if original_transaction:
                        # إنشاء حركة بنك عكسية
                        BankTransaction.objects.create(
                            bank=instance.bank,
                            transaction_type='deposit',
                            amount=original_transaction.amount,
                            description=f'عكس سند صرف {instance.voucher_number} - {instance.reversal_reason or "بدون سبب"}',
                            reference_number=f'REV-{instance.voucher_number}',
                            date=timezone.now().date(),
                            created_by=instance.reversed_by or instance.created_by
                        )
                        print(f"✓ تم إنشاء حركة بنك عكسية لسند الصرف {instance.voucher_number}")
                
        except PaymentVoucher.DoesNotExist:
            # السند غير موجود - ربما تم حذفه
            pass
        except Exception as e:
            print(f"خطأ في معالجة عكس سند الصرف {instance.voucher_number}: {e}")


@receiver(post_save, sender=PaymentVoucher)
def create_account_transaction_on_payment(sender, instance, created, **kwargs):
    """
    إنشاء حركة حساب للمورد تلقائياً عند إنشاء سند صرف
    Create account transaction for supplier automatically when payment voucher is created
    
    IFRS Compliance:
    - IFRS 7: Financial Instruments: Disclosures
    - IAS 24: Related Party Disclosures
    """
    # تطبيق فقط عند الإنشاء الجديد وللموردين
    if created and instance.supplier and instance.voucher_type == 'supplier':
        try:
            from accounts.models import AccountTransaction
            import uuid
            
            # التحقق من عدم وجود حركة مسبقاً
            existing = AccountTransaction.objects.filter(
                reference_type='payment',
                reference_id=instance.id
            ).exists()
            
            if not existing:
                # توليد رقم الحركة
                transaction_number = f"PAY-{uuid.uuid4().hex[:8].upper()}"
                
                # حساب الرصيد السابق
                last_transaction = AccountTransaction.objects.filter(
                    customer_supplier=instance.supplier
                ).order_by('-created_at').first()
                
                previous_balance = last_transaction.balance_after if last_transaction else Decimal('0.000')
                
                # إنشاء حركة مدينة للمورد (تقليل الذمم الدائنة)
                new_balance = previous_balance - instance.amount
                
                AccountTransaction.objects.create(
                    transaction_number=transaction_number,
                    date=instance.date,
                    customer_supplier=instance.supplier,
                    transaction_type='payment',
                    direction='debit',  # مدين - تقليل الذمم الدائنة
                    amount=instance.amount,
                    reference_type='payment',
                    reference_id=instance.id,
                    description=f'سند صرف رقم {instance.voucher_number}',
                    balance_after=new_balance,
                    created_by=instance.created_by
                )
                print(f"✓ تم إنشاء حركة حساب المورد لسند الصرف {instance.voucher_number}")
        except Exception as e:
            print(f"خطأ في إنشاء حركة حساب المورد: {e}")


@receiver(post_save, sender=PaymentVoucher)
def create_journal_entry_on_payment(sender, instance, created, **kwargs):
    """
    إنشاء قيد محاسبي تلقائياً عند إنشاء سند صرف
    Create journal entry automatically when payment voucher is created
    
    IFRS Compliance:
    - IAS 1: Presentation of Financial Statements
    - IAS 7: Statement of Cash Flows
    - IFRS 7: Financial Instruments: Disclosures
    """
    # تطبيق فقط عند الإنشاء الجديد
    if created:
        try:
            from journal.models import JournalEntry
            
            # التحقق من عدم وجود قيد مسبقاً
            existing = JournalEntry.objects.filter(
                reference_type='payment_voucher',
                reference_id=instance.id
            ).exists()
            
            if not existing:
                from journal.services import JournalService
                
                # إنشاء القيد المحاسبي
                JournalService.create_payment_voucher_entry(instance, instance.created_by)
                print(f"✓ تم إنشاء قيد محاسبي لسند الصرف {instance.voucher_number}")
        except Exception as e:
            print(f"خطأ في إنشاء القيد المحاسبي: {e}")
            import traceback
            traceback.print_exc()


