from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Cashbox, CashboxTransfer
from journal.services import JournalService
from core.signals import log_view_activity
from django.utils.translation import gettext_lazy as _


from .models import CashboxTransaction


@receiver(post_save, sender=Cashbox)
def create_cashbox_account(sender, instance, created, **kwargs):
    """
    إنشاء حساب محاسبي للصندوق عند إنشائه
    متوافق مع IFRS - IAS 7 (بيان التدفقات النقدية)
    """
    if created:
        try:
            # إنشاء حساب الصندوق تلقائياً
            account = JournalService.get_cashbox_account(instance)
            
            print(f"✓ تم إنشاء حساب محاسبي للصندوق: {instance.name} - كود: {account.code}")
            
            # عدم إنشاء قيد افتتاحي إذا كان هناك علم يمنع ذلك
            # (سيتم إنشاء القيد من الـ View مباشرة)
            if hasattr(instance, '_skip_opening_balance_signal') and instance._skip_opening_balance_signal:
                print(f"⚠ تم تخطي إنشاء قيد الرصيد الافتتاحي للصندوق {instance.name} (سيتم الإنشاء من الـ View)")
                return
            
        except Exception as e:
            print(f"❌ خطأ في إنشاء حساب الصندوق {instance.name}: {e}")


@receiver(post_save, sender=CashboxTransaction)
def update_cashbox_balance(sender, instance, created, **kwargs):
    """تحديث رصيد الصندوق عند إنشاء معاملة جديدة"""
    if created:
        try:
            from django.db.models import F
            
            # استخدام F() expression لتحديث الرصيد مباشرة في قاعدة البيانات
            # بدون تشغيل Signals إضافية
            Cashbox.objects.filter(id=instance.cashbox.id).update(
                balance=F('balance') + instance.amount
            )
            
            # تحديث الـ instance للحصول على الرصيد المحدث
            instance.cashbox.refresh_from_db()
            print(f"✓ تم تحديث رصيد الصندوق {instance.cashbox.name}: {instance.cashbox.balance}")
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'خطأ في تحديث رصيد الصندوق: {e}')


@receiver(post_delete, sender=CashboxTransaction)
def update_cashbox_balance_on_delete(sender, instance, **kwargs):
    """تحديث رصيد الصندوق عند حذف معاملة"""
    try:
        from django.db.models import F
        
        # استخدام F() expression لتحديث الرصيد مباشرة في قاعدة البيانات
        # عكس العملية: نطرح المبلغ (سواء كان موجباً أو سالباً)
        Cashbox.objects.filter(id=instance.cashbox.id).update(
            balance=F('balance') - instance.amount
        )
        
        # تحديث الـ instance للحصول على الرصيد المحدث
        instance.cashbox.refresh_from_db()
        print(f"✓ تم تحديث رصيد الصندوق {instance.cashbox.name} بعد الحذف: {instance.cashbox.balance}")
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'خطأ في تحديث رصيد الصندوق عند الحذف: {e}')


@receiver(post_delete, sender=Cashbox)
def delete_cashbox_account(sender, instance, **kwargs):
    """
    حذف أو تعطيل حساب الصندوق عند حذفه
    """
    try:
        from journal.models import Account
        from core.signals import log_activity
        from core.middleware import get_current_user

        # البحث عن الحساب المرتبط بالصندوق
        # الحسابات تُنشأ بأكواد مثل 101xxx
        code = f'101{instance.id:03d}'
        account = Account.objects.filter(code=code).first()

        if account:
            # التحقق من وجود حركات في الحساب
            has_movements = account.journal_lines.exists()

            if has_movements:
                # إذا كان الحساب يحتوي على حركات، عطلها بدلاً من حذفها
                account.is_active = False
                account.save(update_fields=['is_active'])
                
                # تسجيل النشاط
                user = get_current_user()
                if user:
                    log_activity(user, 'UPDATE', account, f'تم تعطيل حساب الصندوق {account.name} (يحتوي على حركات)')
                
                print(f"✓ تم تعطيل حساب {account.code} - {account.name} (يحتوي على حركات)")
            else:
                # إذا لم يكن يحتوي على حركات، احذفه
                account_name = account.name
                
                # تسجيل النشاط قبل الحذف
                user = get_current_user()
                if user:
                    log_activity(user, 'DELETE', account, f'تم حذف حساب الصندوق {account_name}')
                
                account.delete()
                print(f"✓ تم حذف حساب {account.code} - {account.name}")

    except Exception as e:
        print(f"❌ خطأ في حذف/تعطيل حساب الصندوق: {e}")
        import traceback
        traceback.print_exc()


@receiver(post_save, sender=CashboxTransfer)
def create_cashbox_transfer_transactions(sender, instance, created, **kwargs):
    """
    إنشاء معاملات الصناديق عند إنشاء تحويل
    متوافق مع IFRS - IAS 7 (بيان التدفقات النقدية)
    """
    if created:
        try:
            if instance.transfer_type == 'cashbox_to_cashbox':
                # تحويل من صندوق إلى صندوق
                # إنشاء معاملة سحب من الصندوق المرسل
                CashboxTransaction.objects.create(
                    cashbox=instance.from_cashbox,
                    transaction_type='transfer_out',
                    date=instance.date,
                    amount=-instance.amount,  # سالب لأنه سحب
                    description=f'تحويل إلى {instance.to_cashbox.name} - رقم التحويل: {instance.transfer_number}',
                    related_transfer=instance,
                    reference_type='transfer',
                    reference_id=instance.id,
                    created_by=instance.created_by
                )
                
                # إنشاء معاملة إيداع في الصندوق المستقبل
                CashboxTransaction.objects.create(
                    cashbox=instance.to_cashbox,
                    transaction_type='transfer_in',
                    date=instance.date,
                    amount=instance.amount,  # موجب لأنه إيداع
                    description=f'تحويل من {instance.from_cashbox.name} - رقم التحويل: {instance.transfer_number}',
                    related_transfer=instance,
                    reference_type='transfer',
                    reference_id=instance.id,
                    created_by=instance.created_by
                )
                
                print(f"✓ تم إنشاء معاملات الصناديق للتحويل {instance.transfer_number}")
                
            elif instance.transfer_type == 'cashbox_to_bank':
                # تحويل من صندوق إلى بنك
                # إنشاء معاملة سحب من الصندوق
                CashboxTransaction.objects.create(
                    cashbox=instance.from_cashbox,
                    transaction_type='withdrawal',
                    date=instance.date,
                    amount=-instance.amount,  # سالب لأنه سحب
                    description=f'سحب للإيداع في {instance.to_bank.name} - رقم التحويل: {instance.transfer_number}',
                    related_transfer=instance,
                    reference_type='transfer',
                    reference_id=instance.id,
                    created_by=instance.created_by
                )
                
                print(f"✓ تم إنشاء معاملة سحب من الصندوق للتحويل {instance.transfer_number}")
                
                # إنشاء معاملة إيداع في البنك
                from banks.models import BankTransaction
                bank_transaction = BankTransaction(
                    bank=instance.to_bank,
                    transaction_type='deposit',
                    amount=instance.amount * instance.exchange_rate,
                    description=f'تحويل من صندوق {instance.from_cashbox.name} - رقم التحويل: {instance.transfer_number}',
                    reference_number=instance.transfer_number,
                    date=instance.date,
                    created_by=instance.created_by
                )
                # تعيين علم لتجنب إنشاء قيد تلقائي من signal (القيد سيُنشأ من JournalService)
                bank_transaction._skip_journal = True
                bank_transaction.save()
                
                print(f"✓ تم إنشاء معاملة إيداع في البنك للتحويل {instance.transfer_number}")
                
            elif instance.transfer_type == 'bank_to_cashbox':
                # تحويل من بنك إلى صندوق
                # إنشاء معاملة سحب من البنك
                from banks.models import BankTransaction
                total_amount = instance.amount + instance.fees
                bank_transaction = BankTransaction(
                    bank=instance.from_bank,
                    transaction_type='withdrawal',
                    amount=total_amount,
                    description=f'تحويل إلى صندوق {instance.to_cashbox.name} - رقم التحويل: {instance.transfer_number}',
                    reference_number=instance.transfer_number,
                    date=instance.date,
                    created_by=instance.created_by
                )
                # تعيين علم لتجنب إنشاء قيد تلقائي من signal (القيد سيُنشأ من JournalService)
                bank_transaction._skip_journal = True
                bank_transaction.save()
                
                print(f"✓ تم إنشاء معاملة سحب من البنك للتحويل {instance.transfer_number}")
                
                # إنشاء معاملة إيداع في الصندوق
                CashboxTransaction.objects.create(
                    cashbox=instance.to_cashbox,
                    transaction_type='deposit',
                    date=instance.date,
                    amount=instance.amount * instance.exchange_rate,  # موجب لأنه إيداع
                    description=f'إيداع من {instance.from_bank.name} - رقم التحويل: {instance.transfer_number}',
                    related_transfer=instance,
                    reference_type='transfer',
                    reference_id=instance.id,
                    created_by=instance.created_by
                )
                
                print(f"✓ تم إنشاء معاملة إيداع في الصندوق للتحويل {instance.transfer_number}")
                
        except Exception as e:
            print(f"❌ خطأ في إنشاء معاملات الصناديق للتحويل {instance.transfer_number}: {e}")
            import traceback
            traceback.print_exc()


@receiver(post_delete, sender=CashboxTransfer)
def delete_cashbox_transfer_transactions(sender, instance, **kwargs):
    """
    حذف معاملات الصناديق عند حذف التحويل
    ⚠️ ملاحظة: Django CASCADE DELETE يحذف المعاملات تلقائياً
    هذا ال Signal فقط للطباعة والتسجيل
    """
    try:
        # ⚠️ لا نحذف المعاملات يدوياً - CASCADE DELETE يفعلها تلقائياً
        # فقط نطبع رسالة للتأكيد
        print(f"✓ تم حذف معاملات الصناديق المرتبطة بالتحويل {instance.transfer_number} (CASCADE DELETE)")
        
    except Exception as e:
        print(f"❌ خطأ في معالجة حذف معاملات الصناديق للتحويل {instance.transfer_number}: {e}")
        import traceback
        traceback.print_exc()