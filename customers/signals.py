"""
إشارات نظام العملاء والموردين
تنشئ القيود المحاسبية تلقائياً عند الإنشاء
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from decimal import Decimal
from .models import CustomerSupplier

@receiver(post_save, sender=CustomerSupplier)
def create_customer_supplier_account(sender, instance, created, **kwargs):
    """
    إنشاء حساب محاسبي للعميل/المورد عند إنشائه
    """
    if not created:
        return

    try:
        from journal.models import Account

        # تحديد الحساب الرئيسي والرمز
        if instance.is_customer:
            parent_code = '1301'  # حسابات العملاء
            code_prefix = '1301'
        elif instance.is_supplier:
            parent_code = '2101'  # حسابات الموردين
            code_prefix = '2101'
        else:
            # إذا كان مشتركاً
            parent_code = '1301'  # افتراضياً تحت العملاء
            code_prefix = '1301'

        parent_account = Account.objects.filter(code=parent_code).first()
        if not parent_account:
            print(f"⚠️ لا يوجد حساب رئيسي {parent_code}")
            return

        # إنشاء رمز فريد للحساب
        code = f"{code_prefix}{instance.id:04d}"

        # التأكد من عدم وجود حساب بنفس الرمز
        if not Account.objects.filter(code=code).exists():
            Account.objects.create(
                code=code,
                name=f'{instance.name}',
                account_type='asset' if instance.is_customer else 'liability',
                parent=parent_account,
                description=f'حساب {"العميل" if instance.is_customer else "المورد"} {instance.name}'
            )

    except Exception as e:
        print(f"خطأ في إنشاء حساب العميل/المورد: {e}")


@receiver(post_save, sender=CustomerSupplier)
def create_opening_balance_journal_entry(sender, instance, created, **kwargs):
    """
    إنشاء قيد محاسبي للرصيد الافتتاحي عند إنشاء عميل/مورد جديد
    """
    
    # فقط عند الإنشاء وليس التحديث
    if not created:
        return
    
    # فقط إذا كان هناك رصيد افتتاحي
    if instance.balance == 0:
        return
    
    try:
        from journal.services import JournalService
        from journal.models import Account
        from django.utils import timezone
        from accounts.models import AccountTransaction
        from django.contrib.auth import get_user_model
        
        # الحصول على المستخدم الذي أنشأ الحساب (إن وجد)
        User = get_user_model()
        creator_user = getattr(instance, '_creator_user', None)
        if not creator_user:
            # استخدام أول مستخدم في النظام كـ fallback
            creator_user = User.objects.first()
        
        if not creator_user:
            print("⚠️ لا يوجد مستخدمين في النظام")
            return
        
        # إنشاء معاملة الرصيد الافتتاحي
        if instance.balance > 0:
            direction = 'debit'
            amount = abs(instance.balance)
        else:
            direction = 'credit'
            amount = abs(instance.balance)
        
        # إنشاء المعاملة إذا لم تكن موجودة
        if not AccountTransaction.objects.filter(
            customer_supplier=instance,
            reference_type='opening_balance'
        ).exists():
            AccountTransaction.objects.create(
                customer_supplier=instance,
                transaction_type='opening_balance',
                reference_type='opening_balance',
                reference_id=instance.id,
                date=timezone.now().date(),
                amount=amount,
                direction=direction,
                description=f'رصيد افتتاحي لـ {instance.name}',
                notes=f'تم إنشاء المعاملة تلقائياً عند إنشاء الحساب',
                created_by=creator_user
            )
        
        # تحديث الرصيد بعد إنشاء المعاملة الافتتاحية
        instance.sync_balance()
        
        # الحصول على الحسابات المحاسبية
        customer_account = None
        supplier_account = None
        
        if instance.is_customer:
            customer_account = Account.objects.filter(code='1301').first()
        if instance.is_supplier:
            supplier_account = Account.objects.filter(code='2101').first()
        
        capital_account = Account.objects.filter(code='301').first()
        
        if not capital_account:
            print(f"⚠️ لا يوجد حساب رأس المال (301)")
            return
        
        # تحديد الحساب المناسب
        if instance.type == 'customer':
            account_obj = customer_account
        elif instance.type == 'supplier':
            account_obj = supplier_account
        elif instance.type == 'both':
            # للحسابات المشتركة، نستخدم حساب العملاء
            account_obj = customer_account
        
        if not account_obj:
            print(f"⚠️ لا يوجد حساب محاسبي للنوع {instance.type}")
            return
        
        # إنشاء القيد المحاسبي فقط إذا لم يكن موجوداً
        from journal.models import JournalEntry
        existing_entry = JournalEntry.objects.filter(
            reference_type='cs_opening',  # استخدام الاسم المختصر
            reference_id=instance.id
        ).first()
        if existing_entry:
            return
        
        lines_data = []
        
        if instance.balance > 0:
            # رصيد موجب = مدين الحساب / دائن رأس المال
            lines_data = [
                {
                    'account_id': account_obj.id,
                    'debit': Decimal(str(abs(instance.balance))),
                    'credit': Decimal('0'),
                    'description': f'رصيد افتتاحي - {instance.get_type_display()}: {instance.name}'
                },
                {
                    'account_id': capital_account.id,
                    'debit': Decimal('0'),
                    'credit': Decimal(str(abs(instance.balance))),
                    'description': 'رأس المال'
                }
            ]
        else:
            # رصيد سالب = دائن الحساب / مدين رأس المال
            lines_data = [
                {
                    'account_id': capital_account.id,
                    'debit': Decimal(str(abs(instance.balance))),
                    'credit': Decimal('0'),
                    'description': 'رأس المال'
                },
                {
                    'account_id': account_obj.id,
                    'debit': Decimal('0'),
                    'credit': Decimal(str(abs(instance.balance))),
                    'description': f'رصيد افتتاحي - {instance.get_type_display()}: {instance.name}'
                }
            ]
        
        # إنشاء القيد
        # ملاحظة: reference_type محدود بـ 20 حرف في قاعدة البيانات
        journal_entry = JournalService.create_journal_entry(
            entry_date=timezone.now().date(),
            description=f'رصيد افتتاحي - {instance.get_type_display()}: {instance.name}',
            reference_type='cs_opening',  # customer_supplier_opening (مختصر)
            reference_id=instance.id,
            lines_data=lines_data,
            user=creator_user
        )
        
    except Exception as e:
        print(f"❌ خطأ في إنشاء القيد المحاسبي للرصيد الافتتاحي: {e}")
        import traceback
        traceback.print_exc()


@receiver(post_delete, sender=CustomerSupplier)
def delete_customer_supplier_account(sender, instance, **kwargs):
    """
    حذف أو تعطيل حساب العميل/المورد عند حذفه
    """
    try:
        from journal.models import Account
        from core.signals import log_activity
        from core.middleware import get_current_user

        # البحث عن الحساب المرتبط بالعميل/المورد
        # الحسابات تُنشأ بأكواد مثل 1301xxxx للعملاء أو 2101xxxx للموردين
        if instance.is_customer:
            code_prefix = '1301'
        elif instance.is_supplier:
            code_prefix = '2101'
        else:
            code_prefix = '1301'  # افتراضي

        code = f"{code_prefix}{instance.id:04d}"
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
                    log_activity(user, 'UPDATE', account, f'تم تعطيل حساب العميل/المورد {account.name} (يحتوي على حركات)')
                
                print(f"✓ تم تعطيل حساب {account.code} - {account.name} (يحتوي على حركات)")
            else:
                # إذا لم يكن يحتوي على حركات، احذفه
                account_name = account.name
                
                # تسجيل النشاط قبل الحذف
                user = get_current_user()
                if user:
                    log_activity(user, 'DELETE', account, f'تم حذف حساب العميل/المورد {account_name}')
                
                account.delete()
                print(f"✓ تم حذف حساب {account.code} - {account_name}")

    except Exception as e:
        print(f"❌ خطأ في حذف/تعطيل حساب العميل/المورد: {e}")
        import traceback
        traceback.print_exc()
