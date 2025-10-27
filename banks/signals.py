"""
Signals for Bank Accounts and Transactions
معالجة الإشارات التلقائية للحسابات البنكية والمعاملات
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from decimal import Decimal

from .models import BankTransaction, BankAccount, BankTransfer
from journal.services import JournalService
from core.signals import log_activity
from core.middleware import get_current_user
from journal.models import Account


@receiver(post_save, sender=BankTransaction)
def update_bank_balance_on_transaction(sender, instance, created, **kwargs):
    """
    تحديث رصيد البنك تلقائياً عند إنشاء معاملة بنكية
    Update bank balance automatically when bank transaction is created
    """
    if created and instance.bank:
        # تجاهل تحديث الرصيد لجميع المعاملات الافتتاحية
        # الرصيد الافتتاحي يتم تعيينه مباشرة في النموذج
        if instance.is_opening_balance:
            print(f"DEBUG: تجاهل تحديث الرصيد للمعاملة الافتتاحية {instance.id}")
            return

        # تجاهل أيضاً المعاملات التي تم إنشاؤها كجزء من إنشاء حساب بنكي
        # هذه المعاملات تكون للقيود المحاسبية وليس للمعاملات الفعلية
        if hasattr(instance, '_skip_balance_update') and instance._skip_balance_update:
            print(f"DEBUG: تجاهل تحديث الرصيد للمعاملة {instance.id} (تم تعيين _skip_balance_update)")
            return

        bank = instance.bank

        print(f"  DEBUG: رصيد البنك قبل التحديث: {bank.balance}, المبلغ: {instance.amount}")

        # تحديث الرصيد حسب نوع المعاملة
        amount = Decimal(str(instance.amount))  # تحويل إلى Decimal
        if instance.transaction_type == 'withdrawal':
            # سحب: نطرح المبلغ
            bank.balance -= amount
        else:  # deposit
            # إيداع: نضيف المبلغ
            bank.balance += amount

        print(f"  DEBUG: رصيد البنك بعد الحساب: {bank.balance}")
        bank.save(update_fields=['balance'])
        print(f"✓ تم تحديث رصيد البنك {bank.name}: {bank.balance}")

        # تسجيل النشاط في سجل الأنشطة
        user = get_current_user()
        if user:
            log_activity(
                user,
                'UPDATE',
                bank,
                f'تحديث رصيد البنك تلقائياً بسبب معاملة بنكية: {instance.get_transaction_type_display()} {instance.amount} - الرصيد الجديد: {bank.balance}'
            )

        # التحقق من الحفظ
        bank.refresh_from_db()
        print(f"  DEBUG: رصيد البنك بعد refresh: {bank.balance}")


@receiver(post_delete, sender=BankTransaction)
def update_bank_balance_on_transaction_delete(sender, instance, **kwargs):
    """
    تحديث رصيد البنك عند حذف معاملة بنكية
    Update bank balance when bank transaction is deleted
    """
    if instance.bank:
        # لا تحديث الرصيد للمعاملات الافتتاحية لأنها تمثل الرصيد الافتتاحي نفسه
        if instance.is_opening_balance:
            print(f"DEBUG: تجاهل تحديث الرصيد عند حذف المعاملة الافتتاحية {instance.id}")
            return

        old_balance = instance.bank.balance
        bank = instance.bank

        # عكس التأثير على الرصيد
        amount = Decimal(str(instance.amount))  # تحويل إلى Decimal
        if instance.transaction_type == 'withdrawal':
            # كان سحب (تم طرح المبلغ)، نعكسه (نضيف المبلغ)
            bank.balance += amount
        else:  # deposit
            # كان إيداع (تم إضافة المبلغ)، نعكسه (نطرح المبلغ)
            bank.balance -= amount

        bank.save(update_fields=['balance'])
        print(f"✓ تم تحديث رصيد البنك بعد الحذف {bank.name}: {bank.balance}")

        # تسجيل النشاط في سجل الأنشطة
        user = get_current_user()
        if user:
            log_activity(
                user,
                'DELETE',
                instance,
                f"حذف معاملة بنكية: {instance.description} - المبلغ: {instance.amount}"
            )


@receiver(post_save, sender=BankTransaction)
def create_bank_transaction_journal_entry(sender, instance, created, **kwargs):
    """إنشاء قيد محاسبي عند إنشاء معاملة بنكية"""
    if created:
        # تجاهل جميع المعاملات الافتتاحية - لا تنشئ قيود لها
        if instance.is_opening_balance:
            print(f"DEBUG: تجاهل إنشاء قيد للمعاملة الافتتاحية {instance.id}")
            return

        # تجاهل المعاملات التي تم إنشاؤها كجزء من إنشاء حساب بنكي
        if hasattr(instance, '_skip_journal') and instance._skip_journal:
            print(f"DEBUG: تجاهل إنشاء القيد التلقائي للمعاملة البنكية {getattr(instance, 'reference_number', '')} بسبب _skip_journal")
            return

        # التحقق من عدم وجود قيد محاسبي بالفعل لهذه المعاملة لتجنب التكرار
        from journal.models import JournalEntry
        existing_entry = JournalEntry.objects.filter(
            reference_type='bank_transaction',
            reference_id=instance.id
        ).exists()

        if existing_entry:
            print(f"⚠ تم العثور على قيد محاسبي موجود بالفعل للمعاملة البنكية {instance.id}، تم تخطي الإنشاء")
            return

        # تحقق إضافي: إذا كانت المعاملة مرتبطة بتحويل بنكي، لا تنشئ قيد
        # لأن التحويل البنكي ينشئ قيده الخاص
        if instance.reference_number:
            from .models import BankTransfer
            # تحقق إذا كان reference_number هو رقم تحويل بنكي
            if BankTransfer.objects.filter(transfer_number=instance.reference_number).exists():
                print(f"DEBUG: تخطي إنشاء القيد للمعاملة البنكية {instance.reference_number} لأنها جزء من تحويل بنكي")
                return

        try:
            bank_account = JournalService.get_or_create_bank_account(instance.bank)
            lines_data = []
            if instance.transaction_type == 'deposit':
                # إيداع: مدين البنك، دائن حساب الإيراد أو النقد
                capital_account = Account.objects.filter(code='301').first()
                if not capital_account:
                    capital_account = Account.objects.create(
                        code='301',
                        name='رأس المال',
                        account_type='equity'
                    )

                lines_data = [
                    {
                        'account_id': bank_account.id,
                        'debit': instance.amount,
                        'credit': 0,
                        'description': f'إيداع في {instance.bank.name}: {instance.description}'
                    },
                    {
                        'account_id': capital_account.id,
                        'debit': 0,
                        'credit': instance.amount,
                        'description': f'إيداع في {instance.bank.name}: {instance.description}'
                    }
                ]
            elif instance.transaction_type == 'withdrawal':
                # سحب: دائن البنك، مدين حساب المصروف
                expense_account = Account.objects.filter(code='6010').first()
                if not expense_account:
                    expense_account = Account.objects.create(
                        code='6010',
                        name='مصروفات متنوعة',
                        account_type='expense',
                        description='حساب المصروفات المتنوعة'
                    )

                lines_data = [
                    {
                        'account_id': expense_account.id,
                        'debit': instance.amount,
                        'credit': 0,
                        'description': f'سحب من {instance.bank.name}: {instance.description}'
                    },
                    {
                        'account_id': bank_account.id,
                        'debit': 0,
                        'credit': instance.amount,
                        'description': f'سحب من {instance.bank.name}: {instance.description}'
                    }
                ]

            if lines_data:
                # الحصول على مستخدم افتراضي إذا لم يكن محدد
                if not hasattr(instance, 'created_by') or not instance.created_by:
                    from users.models import User
                    default_user = User.objects.filter(is_superuser=True).first()
                    if not default_user:
                        default_user = User.objects.filter(is_active=True).first()
                else:
                    default_user = instance.created_by

                JournalService.create_journal_entry(
                    entry_date=instance.date,
                    reference_type='bank_transaction',
                    description=f'معاملة بنكية: {instance.get_transaction_type_display()} - {instance.description}',
                    lines_data=lines_data,
                    reference_id=instance.id,
                    user=default_user
                )
        except Exception as e:
            print(f"خطأ في إنشاء قيد المعاملة البنكية: {e}")


@receiver(post_delete, sender=BankAccount)
def delete_bank_account(sender, instance, **kwargs):
    """
    حذف أو تعطيل حساب البنك عند حذفه
    """
    try:
        from journal.models import Account
        from journal.services import JournalService
        from core.signals import log_activity
        from core.middleware import get_current_user

        # البحث عن الحساب المرتبط بالحساب البنكي
        account = JournalService.get_or_create_bank_account(instance)

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
                    log_activity(user, 'UPDATE', account, f'تم تعطيل حساب البنك {account.name} (يحتوي على حركات)')

                print(f"✓ تم تعطيل حساب {account.code} - {account.name} (يحتوي على حركات)")
            else:
                # إذا لم يكن يحتوي على حركات، احذفه
                account_name = account.name

                # تسجيل النشاط قبل الحذف
                user = get_current_user()
                if user:
                    log_activity(user, 'DELETE', account, f'تم حذف حساب البنك {account_name}')

                account.delete()
                print(f"✓ تم حذف حساب {account.code} - {account.name}")

    except Exception as e:
        print(f"❌ خطأ في حذف/تعطيل حساب البنك: {e}")
        import traceback
        traceback.print_exc()


@receiver(post_delete, sender=BankTransfer)
def delete_bank_transfer_journal_entry(sender, instance, **kwargs):
    """
    حذف القيد المحاسبي عند حذف تحويل بنكي
    Delete journal entry when bank transfer is deleted
    """
    try:
        from journal.services import JournalService

        # حذف القيد المحاسبي المرتبط بالتحويل
        JournalService.delete_journal_entry_by_reference('bank_transfer', instance.id)

        print(f"✓ تم حذف القيد المحاسبي للتحويل البنكي {instance.transfer_number}")

    except Exception as e:
        print(f"❌ خطأ في حذف القيد المحاسبي للتحويل البنكي {instance.transfer_number}: {e}")
        import traceback
        traceback.print_exc()


@receiver(post_save, sender=BankAccount)
def create_bank_account_opening_balance_entry(sender, instance, created, **kwargs):
    """إنشاء قيد محاسبي للرصيد الافتتاحي عند إنشاء حساب بنكي - متوافق مع IFRS"""
    
    # التحقق من أن هذا حساب جديد وليس تحديث
    if not created:
        return
    
    # التحقق من وجود رصيد افتتاحي
    if not instance.initial_balance or instance.initial_balance == 0:
        return
    
    # التحقق من وجود علم لتعطيل Signal (لتجنب التكرار عند الإنشاء من View)
    if hasattr(instance, '_skip_opening_balance_signal') and instance._skip_opening_balance_signal:
        print(f"DEBUG: تخطي Signal للحساب {instance.name} - سيتم إنشاء القيد من View")
        return

    if created and instance.initial_balance and instance.initial_balance != 0:
        # التحقق من عدم وجود قيد افتتاحي بالفعل لتجنب التكرار المطلق
        from journal.models import JournalEntry
        existing_entry = JournalEntry.objects.filter(
            reference_type='bank_initial',
            reference_id=instance.id
        ).exists()

        if existing_entry:
            print(f"⚠ تم العثور على قيد افتتاحي موجود بالفعل للحساب {instance.name}، تم تخطي الإنشاء")
            return

        try:
            from journal.services import JournalService
            from journal.models import Account
            from decimal import Decimal
            
            # إنشاء الحساب الفرعي في journal.Account
            bank_account_obj = JournalService.get_or_create_bank_account(instance)
            
            # الحصول على حساب رأس المال (IFRS: IAS 1 - Opening balance is equity)
            capital_account = Account.objects.filter(code='301').first()
            
            if not capital_account:
                print(f"⚠ حساب رأس المال (301) غير موجود - لا يمكن إنشاء قيد الرصيد الافتتاحي")
                return
            
            if bank_account_obj and instance.initial_balance > 0:
                lines_data = [
                    {
                        'account_id': bank_account_obj.id,
                        'debit': instance.initial_balance,
                        'credit': Decimal('0'),
                        'description': f'رصيد افتتاحي: {instance.name}'
                    },
                    {
                        'account_id': capital_account.id,
                        'debit': Decimal('0'),
                        'credit': instance.initial_balance,
                        'description': f'رصيد افتتاحي - مساهمة رأس المال - {instance.name}'
                    }
                ]
                
                # الحصول على تاريخ الإنشاء
                try:
                    entry_date = instance.created_at.date()
                except Exception:
                    from django.utils import timezone
                    entry_date = timezone.now().date()
                
                # إنشاء القيد المحاسبي
                journal_entry = JournalService.create_journal_entry(
                    entry_date=entry_date,
                    description=f'رصيد افتتاحي - حساب بنكي: {instance.name}',
                    reference_type='bank_initial',
                    reference_id=instance.id,
                    lines_data=lines_data,
                    user=instance.created_by
                )
                
                print(f"✓ تم إنشاء قيد الرصيد الافتتاحي {journal_entry.entry_number} للحساب {instance.name} بقيمة {instance.initial_balance}")
                
                # تسجيل النشاط
                user = get_current_user() or instance.created_by
                if user:
                    log_activity(user, 'CREATE', journal_entry, f'إنشاء قيد رصيد افتتاحي للحساب البنكي {instance.name} بقيمة {instance.initial_balance}')

        except Exception as e:
            print(f"❌ خطأ في إنشاء القيد الافتتاحي للحساب {instance.name}: {e}")
            import traceback
            traceback.print_exc()
