from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .services import JournalService
from .models import Account
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


@receiver(post_save, sender='sales.SalesInvoice')
def create_sales_invoice_journal_entry(sender, instance, created, **kwargs):
    """إنشاء أو تحديث القيد المحاسبي لفاتورة المبيعات عند الإنشاء أو التعديل.

    - عند الإنشاء: نُنشئ قيد المبيعات وCOGS.
    - عند التعديل: نُحدّث القيد الموجود إذا وُجد، أو نُنشئه إذا كان مفقوداً.
    """
    try:
        # البحث عن المستخدم الذي أنشأ/عدّل الفاتورة
        user = getattr(instance, 'created_by', None)
        if created and instance.id:
            # إنشاء القيد عند الإنشاء
            if user:
                JournalService.create_sales_invoice_entry(instance, user)
                JournalService.create_cogs_entry(instance, user)
                logger.info(f"تم إنشاء القيود المحاسبية تلقائياً لفاتورة المبيعات {instance.invoice_number}")
        else:
            # عند التعديل: حدّث القيد الموجود أو أنشئ واحداً إذا كان مفقوداً
            JournalService.update_sales_invoice_entry(instance, user)
            # تحديث/إنشاء قيد COGS إن لزم
            JournalService.create_cogs_entry(instance, user)
            logger.info(f"تم تحديث/التحقق من القيود المحاسبية لفاتورة المبيعات {instance.invoice_number}")
    except Exception as e:
        logger.error(f"خطأ في معالجة القيود المحاسبية لفاتورة المبيعات {instance.invoice_number}: {e}")


@receiver(post_save, sender='purchases.PurchaseInvoice')
def create_purchase_invoice_journal_entry(sender, instance, created, **kwargs):
    """إنشاء قيد محاسبي تلقائياً عند إنشاء فاتورة مشتريات"""
    # ⚠️ تم تعطيل هذه الإشارة لتجنب التداخل مع purchases/signals.py
    # القيود المحاسبية لفواتير المشتريات تُدار من purchases/signals.py
    return
    if created and instance.id:
        try:
            user = getattr(instance, 'created_by', None)
            if user:
                JournalService.create_purchase_invoice_entry(instance, user)
                logger.info(f"تم إنشاء قيد محاسبي تلقائياً لفاتورة المشتريات {instance.invoice_number}")
        except Exception as e:
            logger.error(f"خطأ في إنشاء القيد المحاسبي لفاتورة المشتريات {instance.invoice_number}: {e}")


@receiver(post_save, sender='receipts.PaymentReceipt')
def create_receipt_voucher_journal_entry(sender, instance, created, **kwargs):
    """إنشاء قيد محاسبي تلقائياً عند إنشاء سند قبض"""
    if created and instance.id:
        try:
            user = getattr(instance, 'created_by', None)
            if user:
                JournalService.create_receipt_voucher_entry(instance, user)
                logger.info(f"تم إنشاء قيد محاسبي تلقائياً لسند القبض {instance.receipt_number}")
        except Exception as e:
            logger.error(f"خطأ في إنشاء القيد المحاسبي لسند القبض {instance.receipt_number}: {e}")


@receiver(post_save, sender='payments.PaymentVoucher')
def create_payment_voucher_journal_entry(sender, instance, created, **kwargs):
    """إنشاء قيد محاسبي تلقائياً عند إنشاء سند صرف"""
    if created and instance.id:
        try:
            user = getattr(instance, 'created_by', None)
            if user:
                JournalService.create_payment_voucher_entry(instance, user)
                logger.info(f"تم إنشاء قيد محاسبي تلقائياً لسند الصرف {instance.voucher_number}")
        except Exception as e:
            logger.error(f"خطأ في إنشاء القيد المحاسبي لسند الصرف {instance.voucher_number}: {e}")



@receiver(post_save, sender='purchases.PurchaseReturn')
def create_purchase_return_journal_entry(sender, instance, created, **kwargs):
    """إنشاء قيد محاسبي تلقائياً عند إنشاء مردود مشتريات"""
    # 🔧 تم تعطيل هذه الإشارة لأن القيد يتم إنشاؤه يدوياً في View بعد تحديث المجاميع
    # المشكلة: هذه الإشارة تُنشئ القيد فوراً عند save() قبل إضافة العناصر وتحديث المجاميع
    # الحل: القيد يُنشأ في purchases/views.py -> PurchaseReturnCreateView.form_valid()
    return
    
    if created and instance.id:
        try:
            user = getattr(instance, 'created_by', None)
            if user:
                JournalService.create_purchase_return_entry(instance, user)
                logger.info(f"تم إنشاء قيد محاسبي تلقائياً لمردود المشتريات {instance.return_number}")
        except Exception as e:
            logger.error(f"خطأ في إنشاء القيد المحاسبي لمردود المشتريات {instance.return_number}: {e}")


@receiver(post_save, sender='purchases.PurchaseDebitNote')
def create_purchase_debit_note_journal_entry(sender, instance, created, **kwargs):
    """إنشاء قيد محاسبي تلقائياً عند إنشاء إشعار مدين للمشتريات"""
    if created and instance.id:
        try:
            user = getattr(instance, 'created_by', None)
            if user:
                JournalService.create_purchase_debit_note_entry(instance, user)
                logger.info(f"تم إنشاء قيد محاسبي تلقائياً لإشعار المدين {instance.note_number}")
        except Exception as e:
            logger.error(f"خطأ في إنشاء القيد المحاسبي لإشعار المدين {instance.note_number}: {e}")


@receiver(post_delete, sender='sales.SalesInvoice')
def delete_sales_invoice_journal_entry(sender, instance, **kwargs):
    """حذف القيد المحاسبي تلقائياً عند حذف فاتورة مبيعات"""
    try:
        JournalService.delete_journal_entry_by_reference('sales_invoice', instance.id)
        logger.info(f"تم حذف القيد المحاسبي لفاتورة المبيعات {instance.invoice_number}")
    except Exception as e:
        logger.error(f"خطأ في حذف القيد المحاسبي لفاتورة المبيعات {instance.invoice_number}: {e}")


@receiver(post_delete, sender='purchases.PurchaseInvoice')
def delete_purchase_invoice_journal_entry(sender, instance, **kwargs):
    """حذف القيد المحاسبي تلقائياً عند حذف فاتورة مشتريات"""
    try:
        JournalService.delete_journal_entry_by_reference('purchase_invoice', instance.id)
        logger.info(f"تم حذف القيد المحاسبي لفاتورة المشتريات {instance.invoice_number}")
    except Exception as e:
        logger.error(f"خطأ في حذف القيد المحاسبي لفاتورة المشتريات {instance.invoice_number}: {e}")


@receiver(post_delete, sender='receipts.PaymentReceipt')
def delete_receipt_voucher_journal_entry(sender, instance, **kwargs):
    """حذف القيد المحاسبي تلقائياً عند حذف سند قبض"""
    try:
        JournalService.delete_journal_entry_by_reference('receipt_voucher', instance.id)
        logger.info(f"تم حذف القيد المحاسبي لسند القبض {instance.receipt_number}")
    except Exception as e:
        logger.error(f"خطأ في حذف القيد المحاسبي لسند القبض {instance.receipt_number}: {e}")


@receiver(post_delete, sender='payments.PaymentVoucher')
def delete_payment_voucher_journal_entry(sender, instance, **kwargs):
    """حذف القيد المحاسبي تلقائياً عند حذف سند صرف"""
    try:
        JournalService.delete_journal_entry_by_reference('payment_voucher', instance.id)
        logger.info(f"تم حذف القيد المحاسبي لسند الصرف {instance.voucher_number}")
    except Exception as e:
        logger.error(f"خطأ في حذف القيد المحاسبي لسند الصرف {instance.voucher_number}: {e}")


@receiver(post_delete, sender='sales.SalesReturn')
def delete_sales_return_journal_entry(sender, instance, **kwargs):
    """حذف القيد المحاسبي تلقائياً عند حذف مردود مبيعات"""
    try:
        JournalService.delete_journal_entry_by_reference('sales_return', instance.id)
        logger.info(f"تم حذف القيد المحاسبي لمردود المبيعات {instance.return_number}")
    except Exception as e:
        logger.error(f"خطأ في حذف القيد المحاسبي لمردود المبيعات {instance.return_number}: {e}")


@receiver(post_delete, sender='purchases.PurchaseReturn')
def delete_purchase_return_journal_entry(sender, instance, **kwargs):
    """حذف القيد المحاسبي تلقائياً عند حذف مردود مشتريات"""
    try:
        JournalService.delete_journal_entry_by_reference('purchase_return', instance.id)
        logger.info(f"تم حذف القيد المحاسبي لمردود المشتريات {instance.return_number}")
    except Exception as e:
        logger.error(f"خطأ في حذف القيد المحاسبي لمردود المشتريات {instance.return_number}: {e}")


@receiver(post_save, sender='banks.BankTransfer')
def create_bank_transfer_journal_entry(sender, instance, created, **kwargs):
    """إنشاء قيد محاسبي تلقائياً عند إنشاء تحويل بنكي"""
    # تم تعطيل هذا الإشارة لأن القيد يتم إنشاؤه يدوياً في banks/views.py
    # لتجنب إنشاء قيدين لنفس التحويل
    return
    if created and instance.id:
        try:
            user = getattr(instance, 'created_by', None)
            if user:
                JournalService.create_bank_transfer_entry(instance, user)
                logger.info(f"تم إنشاء قيد محاسبي تلقائياً للتحويل البنكي {instance.transfer_number}")
        except Exception as e:
            logger.error(f"خطأ في إنشاء القيد المحاسبي للتحويل البنكي {instance.transfer_number}: {e}")


@receiver(post_delete, sender='banks.BankTransfer')
def delete_bank_transfer_journal_entry(sender, instance, **kwargs):
    """حذف القيد المحاسبي تلقائياً عند حذف تحويل بنكي"""
    try:
        JournalService.delete_journal_entry_by_reference('bank_transfer', instance.id)
        logger.info(f"تم حذف القيد المحاسبي للتحويل البنكي {instance.transfer_number}")
    except Exception as e:
        logger.error(f"خطأ في حذف القيد المحاسبي للتحويل البنكي {instance.transfer_number}: {e}")


# إشارات الإيرادات والمصروفات
@receiver(post_save, sender='revenues_expenses.RevenueExpenseEntry')
def create_revenue_expense_journal_entry(sender, instance, created, **kwargs):
    """إنشاء قيد محاسبي تلقائياً عند إنشاء قيد إيراد أو مصروف"""
    if created and instance.id:
        try:
            user = getattr(instance, 'created_by', None)
            if user:
                # استخدام JournalService العام لإنشاء القيد
                lines_data = []
                if instance.type == 'revenue':
                    # قيد الإيراد: مدين الصندوق/البنك، دائن الإيراد
                    lines_data = [
                        {
                            'account_id': instance.account.id if instance.account else None,
                            'debit': instance.amount,
                            'credit': 0,
                            'description': instance.description
                        },
                        {
                            'account_id': instance.category.account.id if instance.category and instance.category.account else None,
                            'debit': 0,
                            'credit': instance.amount,
                            'description': instance.description
                        }
                    ]
                else:  # expense
                    # قيد المصروف: مدين المصروف، دائن الصندوق/البنك
                    lines_data = [
                        {
                            'account_id': instance.category.account.id if instance.category and instance.category.account else None,
                            'debit': instance.amount,
                            'credit': 0,
                            'description': instance.description
                        },
                        {
                            'account_id': instance.account.id if instance.account else None,
                            'debit': 0,
                            'credit': instance.amount,
                            'description': instance.description
                        }
                    ]
                
                if lines_data and all(line['account_id'] is not None for line in lines_data):
                    JournalService.create_journal_entry(
                        entry_date=instance.date,
                        reference_type='revenue_expense',
                        reference_id=instance.id,
                        description=f"{instance.get_type_display()}: {instance.description}",
                        lines_data=lines_data,
                        user=user
                    )
                    logger.info(f"تم إنشاء قيد محاسبي تلقائياً لقيد الإيراد/المصروف {instance.id}")
        except Exception as e:
            logger.error(f"خطأ في إنشاء القيد المحاسبي لقيد الإيراد/المصروف {instance.id}: {e}")


@receiver(post_delete, sender='revenues_expenses.RevenueExpenseEntry')
def delete_revenue_expense_journal_entry(sender, instance, **kwargs):
    """حذف القيد المحاسبي تلقائياً عند حذف قيد إيراد أو مصروف"""
    try:
        JournalService.delete_journal_entry_by_reference('revenue_expense', instance.id)
        logger.info(f"تم حذف القيد المحاسبي لقيد الإيراد/المصروف {instance.id}")
    except Exception as e:
        logger.error(f"خطأ في حذف القيد المحاسبي لقيد الإيراد/المصروف {instance.id}: {e}")


# إشارات الأصول
@receiver(post_save, sender='assets_liabilities.Asset')
def create_asset_journal_entry(sender, instance, created, **kwargs):
    """إنشاء قيد محاسبي تلقائياً عند إنشاء أصل جديد"""
    if created and instance.id and instance.purchase_cost:
        try:
            user = getattr(instance, 'created_by', None)
            if user:
                lines_data = []
                # قيد شراء الأصل: مدين الأصل، دائن الصندوق/البنك
                # يمكن تفعيل هذا لاحقاً عند ربط الحسابات
                logger.info(f"تم إنشاء أصل جديد: {instance.name} بقيمة {instance.purchase_cost}")
                
                # lines_data = [
                #     {
                #         'account_id': asset_account_id,
                #         'debit': instance.purchase_cost,
                #         'credit': 0,
                #         'description': f"شراء أصل: {instance.name}"
                #     },
                #     {
                #         'account_id': cash_account_id,
                #         'debit': 0,
                #         'credit': instance.purchase_cost,
                #         'description': f"دفع ثمن أصل: {instance.name}"
                #     }
                # ]
                
                # JournalService.create_journal_entry(
                #     reference_type='asset',
                #     reference_id=instance.id,
                #     description=f"شراء أصل: {instance.name}",
                #     lines_data=lines_data,
                #     user=user
                # )
        except Exception as e:
            logger.error(f"خطأ في إنشاء القيد المحاسبي لشراء الأصل {instance.name}: {e}")


@receiver(post_delete, sender='assets_liabilities.Asset')
def delete_asset_journal_entry(sender, instance, **kwargs):
    """حذف القيد المحاسبي تلقائياً عند حذف أصل"""
    try:
        JournalService.delete_journal_entry_by_reference('asset_purchase', instance.id)
        logger.info(f"تم حذف القيد المحاسبي للأصل {instance.name}")
    except Exception as e:
        logger.error(f"خطأ في حذف القيد المحاسبي للأصل {instance.name}: {e}")


# إشارات الخصوم
@receiver(post_save, sender='assets_liabilities.Liability')
def create_liability_journal_entry(sender, instance, created, **kwargs):
    """إنشاء قيد محاسبي تلقائياً عند إنشاء التزام جديد"""
    if created and instance.id and instance.original_amount:
        try:
            user = getattr(instance, 'created_by', None)
            if user:
                lines_data = []
                # قيد الالتزام: مدين الصندوق/المصروف، دائن الالتزام
                if instance.category and instance.category.account:
                    # افتراضياً دائن الالتزام، مدين النقد
                    cash_account = Account.objects.filter(code__startswith='101', account_type='asset').first()
                    if cash_account:
                        lines_data = [
                            {
                                'account_id': cash_account.id,
                                'debit': instance.original_amount,
                                'credit': 0,
                                'description': f"استلام خصم: {instance.name}"
                            },
                            {
                                'account_id': instance.category.account.id,
                                'debit': 0,
                                'credit': instance.original_amount,
                                'description': f"خصم: {instance.name}"
                            }
                        ]
                
                if lines_data and all(line['account_id'] is not None for line in lines_data):
                    JournalService.create_journal_entry(
                        entry_date=instance.start_date,
                        reference_type='liability',
                        reference_id=instance.id,
                        description=f"خصم: {instance.name}",
                        lines_data=lines_data,
                        user=user
                    )
                    logger.info(f"تم إنشاء قيد محاسبي تلقائياً للخصم {instance.name}")
        except Exception as e:
            logger.error(f"خطأ في إنشاء القيد المحاسبي للخصم {instance.name}: {e}")


@receiver(post_delete, sender='assets_liabilities.Liability')
def delete_liability_journal_entry(sender, instance, **kwargs):
    """حذف القيد المحاسبي تلقائياً عند حذف التزام"""
    try:
        JournalService.delete_journal_entry_by_reference('liability', instance.id)
        logger.info(f"تم حذف القيد المحاسبي للالتزام {instance.description}")
    except Exception as e:
        logger.error(f"خطأ في حذف القيد المحاسبي للالتزام {instance.description}: {e}")


# إشارات الإهلاك
@receiver(post_save, sender='assets_liabilities.DepreciationEntry')
def create_depreciation_journal_entry(sender, instance, created, **kwargs):
    """إنشاء قيد محاسبي تلقائياً عند إنشاء قيد إهلاك"""
    if created and instance.id and instance.depreciation_amount:
        try:
            user = getattr(instance, 'created_by', None)
            if user:
                lines_data = []
                # قيد الإهلاك: مدين مصروف الإهلاك، دائن مجمع إهلاك الأصل
                if instance.asset and instance.asset.category and hasattr(instance.asset.category, 'accumulated_depreciation_account') and instance.asset.category.accumulated_depreciation_account:
                    lines_data = [
                        {
                            'account_id': instance.asset.category.depreciation_expense_account.id if hasattr(instance.asset.category, 'depreciation_expense_account') and instance.asset.category.depreciation_expense_account else None,
                            'debit': instance.depreciation_amount,
                            'credit': 0,
                            'description': f"إهلاك {instance.asset.name}"
                        },
                        {
                            'account_id': instance.asset.category.accumulated_depreciation_account.id,
                            'debit': 0,
                            'credit': instance.depreciation_amount,
                            'description': f"مجمع إهلاك {instance.asset.name}"
                        }
                    ]
                
                if lines_data and all(line['account_id'] is not None for line in lines_data):
                    JournalService.create_journal_entry(
                        entry_date=instance.depreciation_date,
                        reference_type='asset_depreciation',
                        reference_id=instance.id,
                        description=f"إهلاك الأصل {instance.asset.name}",
                        lines_data=lines_data,
                        user=user
                    )
                    logger.info(f"تم إنشاء قيد محاسبي تلقائياً لإهلاك الأصل {instance.asset.name}")
        except Exception as e:
            logger.error(f"خطأ في إنشاء القيد المحاسبي لإهلاك الأصل {instance.asset.name}: {e}")


@receiver(post_delete, sender='assets_liabilities.DepreciationEntry')
def delete_depreciation_journal_entry(sender, instance, **kwargs):
    """حذف القيد المحاسبي تلقائياً عند حذف قيد إهلاك"""
    try:
        JournalService.delete_journal_entry_by_reference('depreciation', instance.id)
        logger.info(f"تم حذف القيد المحاسبي لإهلاك {instance.asset.name if instance.asset else 'غير محدد'}")
    except Exception as e:
        logger.error(f"خطأ في حذف القيد المحاسبي لإهلاك {instance.asset.name if instance.asset else 'غير محدد'}: {e}")


# إشارات تحويلات الصناديق
@receiver(post_save, sender='cashboxes.CashboxTransfer')
def create_cashbox_transfer_journal_entry(sender, instance, created, **kwargs):
    """إنشاء قيد محاسبي تلقائياً عند إنشاء تحويل صندوق"""
    if created and instance.id:
        try:
            user = getattr(instance, 'created_by', None)
            if user:
                journal_entry = JournalService.create_cashbox_transfer_entry(instance, user)
                if journal_entry:
                    logger.info(f"تم إنشاء قيد محاسبي تلقائياً للتحويل {instance.transfer_number}: {journal_entry.entry_number}")
                    
                    # تسجيل في audit log
                    try:
                        from core.models import AuditLog
                        AuditLog.objects.create(
                            user=user,
                            action_type='create',
                            content_type='JournalEntry',
                            object_id=journal_entry.pk,
                            description=f'إنشاء قيد تحويل تلقائياً: {journal_entry.entry_number} للتحويل {instance.transfer_number}'
                        )
                    except Exception as audit_error:
                        logger.error(f"خطأ في تسجيل إنشاء قيد التحويل في audit log: {audit_error}")
                else:
                    logger.warning(f"لم يتم إنشاء قيد محاسبي للتحويل {instance.transfer_number}")
        except Exception as e:
            logger.error(f"خطأ في إنشاء القيد المحاسبي للتحويل {instance.transfer_number}: {e}")


@receiver(post_delete, sender='cashboxes.CashboxTransfer')
def delete_cashbox_transfer_journal_entry(sender, instance, **kwargs):
    """حذف القيد المحاسبي تلقائياً عند حذف تحويل صندوق"""
    try:
        JournalService.delete_journal_entry_by_reference('cashbox_transfer', instance.id)
        logger.info(f"تم حذف القيد المحاسبي للتحويل {instance.transfer_number}")
    except Exception as e:
        logger.error(f"خطأ في حذف القيد المحاسبي للتحويل {instance.transfer_number}: {e}")


# إشارات تحديث أرصدة الحسابات
@receiver(post_save, sender='journal.JournalLine')
def update_account_balance_on_save(sender, instance, **kwargs):
    """تحديث رصيد الحساب عند حفظ بند قيد محاسبي"""
    try:
        old_balance = instance.account.balance
        instance.account.update_account_balance()
        new_balance = instance.account.balance
        
        logger.info(f"تم تحديث رصيد الحساب {instance.account.code} - {instance.account.name}: من {old_balance} إلى {new_balance}")
        
        # تسجيل في audit log
        try:
            from core.models import AuditLog
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            # محاولة الحصول على مستخدم النظام أو المستخدم الحالي
            system_user = User.objects.filter(is_superuser=True).first()
            if system_user:
                AuditLog.objects.create(
                    user=system_user,
                    action_type='update',
                    content_type='Account',
                    object_id=instance.account.pk,
                    description=f'تحديث رصيد الحساب {instance.account.code} - {instance.account.name}: من {old_balance} إلى {new_balance} (بسبب قيد رقم {instance.journal_entry.entry_number})'
                )
        except Exception as audit_error:
            logger.error(f"خطأ في تسجيل تحديث الرصيد في audit log: {audit_error}")
        
        # تحديث رصيد الحساب الرئيسي إذا كان موجوداً
        if instance.account.parent:
            old_parent_balance = instance.account.parent.balance
            instance.account.parent.update_account_balance()
            new_parent_balance = instance.account.parent.balance
            logger.info(f"تم تحديث رصيد الحساب الرئيسي {instance.account.parent.code} - {instance.account.parent.name}: من {old_parent_balance} إلى {new_parent_balance}")
            
            # تسجيل في audit log للحساب الرئيسي
            try:
                AuditLog.objects.create(
                    user=system_user,
                    action_type='update',
                    content_type='Account',
                    object_id=instance.account.parent.pk,
                    description=f'تحديث رصيد الحساب الرئيسي {instance.account.parent.code} - {instance.account.parent.name}: من {old_parent_balance} إلى {new_parent_balance} (بسبب تحديث حساب فرعي {instance.account.code})'
                )
            except Exception as audit_error:
                logger.error(f"خطأ في تسجيل تحديث رصيد الحساب الرئيسي في audit log: {audit_error}")
        
        # تحديث رصيد الحساب الرئيسي إذا كان موجوداً
        if instance.account.parent:
            old_parent_balance = instance.account.parent.balance
            instance.account.parent.update_account_balance()
            new_parent_balance = instance.account.parent.balance
            logger.info(f"تم تحديث رصيد الحساب الرئيسي {instance.account.parent.code} - {instance.account.parent.name} بعد الحذف: من {old_parent_balance} إلى {new_parent_balance}")
            
            # تسجيل في audit log للحساب الرئيسي
            try:
                AuditLog.objects.create(
                    user=system_user,
                    action_type='update',
                    content_type='Account',
                    object_id=instance.account.parent.pk,
                    description=f'تحديث رصيد الحساب الرئيسي بعد حذف بند قيد: {instance.account.parent.code} - {instance.account.parent.name}: من {old_parent_balance} إلى {new_parent_balance} (بسبب حذف من حساب فرعي {instance.account.code})'
                )
            except Exception as audit_error:
                logger.error(f"خطأ في تسجيل تحديث رصيد الحساب الرئيسي في audit log: {audit_error}")
        
        # مزامنة رصيد الصندوق أو البنك إذا كان الحساب مرتبطاً بهم
        
    except Exception as e:
        logger.error(f"خطأ في تحديث رصيد الحساب {instance.account.code}: {e}")


@receiver(post_delete, sender='journal.JournalLine')
def update_account_balance_on_delete(sender, instance, **kwargs):
    """تحديث رصيد الحساب عند حذف بند قيد محاسبي"""
    try:
        old_balance = instance.account.balance
        instance.account.update_account_balance()
        new_balance = instance.account.balance
        
        logger.info(f"تم تحديث رصيد الحساب {instance.account.code} - {instance.account.name} بعد الحذف: من {old_balance} إلى {new_balance}")
        
        # تسجيل في audit log
        try:
            from core.models import AuditLog
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            # محاولة الحصول على مستخدم النظام
            system_user = User.objects.filter(is_superuser=True).first()
            if system_user:
                AuditLog.objects.create(
                    user=system_user,
                    action_type='update',
                    content_type='Account',
                    object_id=instance.account.pk,
                    description=f'تحديث رصيد الحساب بعد حذف بند قيد: {instance.account.code} - {instance.account.name}: من {old_balance} إلى {new_balance}'
                )
        except Exception as audit_error:
            logger.error(f"خطأ في تسجيل تحديث الرصيد في audit log: {audit_error}")
        
        # مزامنة رصيد الصندوق أو البنك إذا كان الحساب مرتبطاً بهم
        logger.debug(f"استدعاء مزامنة رصيد الصندوق/البنك لحساب {instance.account.code} بعد حذف البند")
        sync_cashbox_or_bank_balance(instance.account)
        
    except Exception as e:
        logger.error(f"خطأ في تحديث رصيد الحساب {instance.account.code}: {e}")


def create_cashbox_bank_transaction(journal_line):
    """
    إنشاء حركة صندوق أو بنك عند إنشاء بند قيد محاسبي يؤثر عليها
    """
    try:
        logger.debug(f"فحص إنشاء حركة للحساب {journal_line.account.code} - {journal_line.account.name}")
        
        # التحقق إذا كان حساب صندوق (يبدأ بـ 101)
        if journal_line.account.code.startswith('101'):
            create_cashbox_transaction_from_journal_line(journal_line)
        
        # التحقق إذا كان حساب بنك (يبدأ بـ 1101)
        elif journal_line.account.code.startswith('1101'):
            create_bank_transaction_from_journal_line(journal_line)
        else:
            logger.debug(f"الحساب {journal_line.account.code} ليس حساب صندوق أو بنك")
            
    except Exception as e:
        logger.error(f"خطأ في إنشاء حركة الصندوق/البنك للحساب {journal_line.account.code}: {e}")


def create_cashbox_transaction_from_journal_line(journal_line):
    """
    إنشاء حركة صندوق من بند القيد المحاسبي
    """
    try:
        from cashboxes.models import Cashbox, CashboxTransaction
        
        # تجاهل القيود التي تم إنشاء معاملاتها يدوياً
        ignored_reference_types = ['cashbox_initial', 'cashbox_adjustment', 'transfer']
        if journal_line.journal_entry.reference_type in ignored_reference_types:
            logger.debug(f"تجاهل إنشاء معاملة صندوق من القيد {journal_line.journal_entry.entry_number} - النوع: {journal_line.journal_entry.reference_type} (تم إنشاء المعاملة يدوياً)")
            return
        
        # استخراج رقم الصندوق من كود الحساب
        if journal_line.account.code.startswith('101'):
            try:
                cashbox_id = int(journal_line.account.code[3:])
                cashbox = Cashbox.objects.get(id=cashbox_id)
                
                # تحديد نوع الحركة بناءً على المدين/الدائن
                if journal_line.debit > 0:
                    # مدين - إيداع أو تحويل وارد
                    transaction_type = 'deposit'
                    amount = journal_line.debit
                elif journal_line.credit > 0:
                    # دائن - سحب أو تحويل صادر
                    transaction_type = 'withdrawal'
                    amount = -journal_line.credit
                else:
                    logger.debug(f"بند القيد بدون مبلغ للحساب {journal_line.account.code}")
                    return
                
                # التحقق من عدم وجود حركة مكررة
                existing_transaction = CashboxTransaction.objects.filter(
                    cashbox=cashbox,
                    reference_type='journal_entry',
                    reference_id=journal_line.journal_entry.id,
                    date=journal_line.journal_entry.entry_date
                ).first()
                
                if existing_transaction:
                    logger.debug(f"حركة الصندوق موجودة بالفعل للقيد {journal_line.journal_entry.entry_number}")
                    return
                
                # إنشاء الحركة
                CashboxTransaction.objects.create(
                    cashbox=cashbox,
                    transaction_type=transaction_type,
                    date=journal_line.journal_entry.entry_date,
                    amount=amount,
                    description=f"قيد رقم {journal_line.journal_entry.entry_number}: {journal_line.line_description or journal_line.journal_entry.description}",
                    reference_type='journal_entry',
                    reference_id=journal_line.journal_entry.id,
                    created_by=journal_line.journal_entry.created_by
                )
                
                logger.info(f"تم إنشاء حركة صندوق للقيد {journal_line.journal_entry.entry_number}: {cashbox.name} - {amount}")
                
                # تسجيل في audit log
                try:
                    from core.models import AuditLog
                    from django.contrib.auth import get_user_model
                    User = get_user_model()
                    
                    system_user = User.objects.filter(is_superuser=True).first()
                    if system_user:
                        AuditLog.objects.create(
                            user=system_user,
                            action_type='create',
                            content_type='CashboxTransaction',
                            object_id=cashbox.id,
                            description=f'إنشاء حركة صندوق تلقائياً من قيد {journal_line.journal_entry.entry_number}: {cashbox.name}'
                        )
                except Exception as audit_error:
                    logger.error(f"خطأ في تسجيل إنشاء حركة الصندوق في audit log: {audit_error}")
                    
            except (ValueError, Cashbox.DoesNotExist) as e:
                logger.warning(f"لم يتم العثور على الصندوق المرتبط بحساب {journal_line.account.code}: {e}")
                
    except Exception as e:
        logger.error(f"خطأ في إنشاء حركة الصندوق: {e}")


def create_bank_transaction_from_journal_line(journal_line):
    """
    إنشاء حركة بنك من بند القيد المحاسبي
    """
    try:
        from banks.models import BankAccount, BankTransaction
        
        # تجاهل القيود التي تم إنشاء معاملاتها يدوياً
        ignored_reference_types = ['transfer', 'cashbox_transfer', 'bank_transfer']
        if journal_line.journal_entry.reference_type in ignored_reference_types:
            logger.debug(f"تجاهل إنشاء معاملة بنك من القيد {journal_line.journal_entry.entry_number} - النوع: {journal_line.journal_entry.reference_type} (تم إنشاء المعاملة يدوياً)")
            return
        
        # استخراج رقم البنك من كود الحساب
        if journal_line.account.code.startswith('1101'):
            try:
                bank_id = int(journal_line.account.code[4:])  # إزالة '1101'
                bank = BankAccount.objects.get(id=bank_id)
                
                # تحديد نوع الحركة بناءً على المدين/الدائن
                if journal_line.debit > 0:
                    # مدين - إيداع
                    transaction_type = 'deposit'
                    amount = journal_line.debit
                elif journal_line.credit > 0:
                    # دائن - سحب
                    transaction_type = 'withdrawal'
                    amount = -journal_line.credit
                else:
                    logger.debug(f"بند القيد بدون مبلغ للحساب {journal_line.account.code}")
                    return
                
                # التحقق من عدم وجود حركة مكررة
                existing_transaction = BankTransaction.objects.filter(
                    bank=bank,
                    description__icontains=f"قيد رقم {journal_line.journal_entry.entry_number}",
                    date=journal_line.journal_entry.entry_date
                ).first()
                
                if existing_transaction:
                    logger.debug(f"حركة البنك موجودة بالفعل للقيد {journal_line.journal_entry.entry_number}")
                    return
                
                # إنشاء الحركة
                BankTransaction.objects.create(
                    bank=bank,
                    transaction_type=transaction_type,
                    date=journal_line.journal_entry.entry_date,
                    amount=amount,
                    description=f"قيد رقم {journal_line.journal_entry.entry_number}: {journal_line.line_description or journal_line.journal_entry.description}",
                    created_by=journal_line.journal_entry.created_by
                )
                
                logger.info(f"تم إنشاء حركة بنك للقيد {journal_line.journal_entry.entry_number}: {bank.name} - {amount}")
                
                # تسجيل في audit log
                try:
                    from core.models import AuditLog
                    from django.contrib.auth import get_user_model
                    User = get_user_model()
                    
                    system_user = User.objects.filter(is_superuser=True).first()
                    if system_user:
                        AuditLog.objects.create(
                            user=system_user,
                            action_type='create',
                            content_type='BankTransaction',
                            object_id=bank.id,
                            description=f'إنشاء حركة بنك تلقائياً من قيد {journal_line.journal_entry.entry_number}: {bank.name}'
                        )
                except Exception as audit_error:
                    logger.error(f"خطأ في تسجيل إنشاء حركة البنك في audit log: {audit_error}")
                    
            except (ValueError, BankAccount.DoesNotExist) as e:
                logger.warning(f"لم يتم العثور على البنك المرتبط بحساب {journal_line.account.code}: {e}")
                
    except Exception as e:
        logger.error(f"خطأ في إنشاء حركة البنك: {e}")


def sync_cashbox_balance_from_account(account):
    """
    مزامنة رصيد الصندوق مع رصيد حسابه المحاسبي
    """
    try:
        from cashboxes.models import Cashbox
        
        logger.debug(f"بدء مزامنة رصيد الصندوق لحساب {account.code} - {account.name}")
        
        # البحث عن الصندوق المرتبط بهذا الحساب
        # استخدام كود الحساب لاستخراج رقم الصندوق
        cashbox = None
        
        if account.code.startswith('101'):
            try:
                # استخراج رقم الصندوق من الكود (101001 -> 1)
                cashbox_id = int(account.code[3:])  # إزالة '101' والحصول على الرقم
                cashbox = Cashbox.objects.get(id=cashbox_id)
                logger.debug(f"تم العثور على الصندوق {cashbox.name} من كود الحساب {account.code}")
            except (ValueError, Cashbox.DoesNotExist) as e:
                logger.warning(f"فشل استخراج رقم الصندوق من كود {account.code}: {e}")
                # إذا فشل، جرب البحث بالاسم كطريقة احتياطية
                if '1001' in account.name:
                    cashbox = Cashbox.objects.filter(name__icontains='1001').first()
                elif '1002' in account.name:
                    cashbox = Cashbox.objects.filter(name__icontains='1002').first()
                else:
                    # محاولة بحث عام
                    account_name_part = account.name.split('-')[-1].strip() if '-' in account.name else account.name
                    cashbox = Cashbox.objects.filter(name__icontains=account_name_part).first()
        
        if cashbox:
            # تحديث رصيد الصندوق ليطابق رصيد الحساب المحاسبي
            old_balance = cashbox.balance
            new_balance = account.balance
            
            if old_balance != new_balance:
                cashbox.balance = new_balance
                cashbox.save(update_fields=['balance'])
                logger.info(f"✅ تم مزامنة رصيد الصندوق '{cashbox.name}' من {old_balance} إلى {new_balance}")
                
                # تسجيل في audit log
                try:
                    from core.models import AuditLog
                    from django.contrib.auth import get_user_model
                    User = get_user_model()
                    
                    system_user = User.objects.filter(is_superuser=True).first()
                    if system_user:
                        AuditLog.objects.create(
                            user=system_user,
                            action_type='update',
                            content_type='Cashbox',
                            object_id=cashbox.pk,
                            description=f'مزامنة رصيد الصندوق {cashbox.name}: من {old_balance} إلى {new_balance} (من حساب {account.code})'
                        )
                except Exception as audit_error:
                    logger.error(f"خطأ في تسجيل مزامنة رصيد الصندوق في audit log: {audit_error}")
            else:
                logger.debug(f"رصيد الصندوق '{cashbox.name}' متطابق مع حسابه ({new_balance})")
        else:
            logger.warning(f"لم يتم العثور على صندوق مرتبط بحساب {account.code} - {account.name}")
    
    except Exception as e:
        logger.error(f"خطأ في مزامنة رصيد الصندوق: {e}")


def sync_bank_balance_from_account(account):
    """
    مزامنة رصيد البنك مع رصيد حسابه المحاسبي
    """
    try:
        from banks.models import BankAccount
        
        logger.debug(f"بدء مزامنة رصيد البنك لحساب {account.code} - {account.name}")
        
        # البحث عن الحساب البنكي المرتبط بهذا الحساب
        bank_account = None
        
        if account.code.startswith('1101'):
            try:
                # استخراج رقم البنك من الكود (11010002 -> 2)
                bank_id = int(account.code[4:])  # إزالة '1101' والحصول على الرقم
                bank_account = BankAccount.objects.get(id=bank_id)
                logger.debug(f"تم العثور على البنك {bank_account.name} من كود الحساب {account.code}")
            except (ValueError, BankAccount.DoesNotExist) as e:
                logger.warning(f"فشل استخراج رقم البنك من كود {account.code}: {e}")
                # محاولة البحث من خلال اسم الحساب كطريقة احتياطية
                account_name_parts = account.name.split('-')
                if len(account_name_parts) >= 2:
                    # محاولة البحث بالاسم الأول
                    bank_account = BankAccount.objects.filter(
                        name__icontains=account_name_parts[0].strip()
                    ).first()
                    
                    if not bank_account:
                        # محاولة البحث باسم البنك
                        bank_account = BankAccount.objects.filter(
                            bank_name__icontains=account_name_parts[-1].strip()
                        ).first()
        
        if bank_account:
            # تحديث رصيد البنك ليطابق رصيد الحساب المحاسبي
            old_balance = bank_account.balance
            new_balance = account.balance
            
            if old_balance != new_balance:
                bank_account.balance = new_balance
                bank_account.save(update_fields=['balance'])
                logger.info(f"✅ تم مزامنة رصيد البنك '{bank_account.name}' من {old_balance} إلى {new_balance}")
                
                # تسجيل في audit log
                try:
                    from core.models import AuditLog
                    from django.contrib.auth import get_user_model
                    User = get_user_model()
                    
                    system_user = User.objects.filter(is_superuser=True).first()
                    if system_user:
                        AuditLog.objects.create(
                            user=system_user,
                            action_type='update',
                            content_type='BankAccount',
                            object_id=bank_account.pk,
                            description=f'مزامنة رصيد البنك {bank_account.name}: من {old_balance} إلى {new_balance} (من حساب {account.code})'
                        )
                except Exception as audit_error:
                    logger.error(f"خطأ في تسجيل مزامنة رصيد البنك في audit log: {audit_error}")
            else:
                logger.debug(f"رصيد البنك '{bank_account.name}' متطابق مع حسابه ({new_balance})")
        else:
            logger.warning(f"لم يتم العثور على بنك مرتبط بحساب {account.code} - {account.name}")
                
    except Exception as e:
        logger.error(f"خطأ في مزامنة رصيد البنك: {e}")


def sync_cashbox_or_bank_balance(account):
    """
    مزامنة رصيد الصندوق أو البنك بناءً على نوع الحساب
    """
    try:
        logger.debug(f"فحص نوع الحساب {account.code} - {account.name}")
        
        # التحقق إذا كان حساب صندوق (يبدأ بـ 101)
        if account.code.startswith('101'):
            logger.debug(f"الحساب {account.code} هو حساب صندوق - بدء المزامنة")
            sync_cashbox_balance_from_account(account)
        
        # التحقق إذا كان حساب بنك (يبدأ بـ 1101)
        elif account.code.startswith('1101'):
            logger.debug(f"الحساب {account.code} هو حساب بنك - بدء المزامنة")
            sync_bank_balance_from_account(account)
        else:
            logger.debug(f"الحساب {account.code} ليس حساب صندوق أو بنك - لا حاجة للمزامنة")
            
    except Exception as e:
        logger.error(f"خطأ في مزامنة رصيد الصندوق/البنك للحساب {account.code}: {e}")


@receiver(post_save, sender=Account)
def log_account_creation(sender, instance, created, **kwargs):
    """
    تسجيل إنشاء أو تحديث الحساب في سجل الأنشطة
    """
    try:
        from core.signals import log_activity
        from core.middleware import get_current_user

        if created:
            # إنشاء حساب جديد
            user = get_current_user()
            if user:
                log_activity(user, 'CREATE', instance, f'تم إنشاء حساب محاسبي جديد: {instance.name} ({instance.code})')
        else:
            # تحديث حساب موجود
            user = get_current_user()
            if user:
                log_activity(user, 'UPDATE', instance, f'تم تحديث حساب محاسبي: {instance.name} ({instance.code})')
    except Exception as e:
        logger.error(f"خطأ في تسجيل نشاط الحساب {instance.code}: {e}")


@receiver(post_delete, sender=Account)
def log_account_deletion(sender, instance, **kwargs):
    """
    تسجيل حذف الحساب في سجل الأنشطة
    """
    try:
        from core.signals import log_activity
        from core.middleware import get_current_user

        user = get_current_user()
        if user:
            log_activity(user, 'DELETE', instance, f'تم حذف حساب محاسبي: {instance.name} ({instance.code})')
    except Exception as e:
        logger.error(f"خطأ في تسجيل حذف الحساب {instance.code}: {e}")
