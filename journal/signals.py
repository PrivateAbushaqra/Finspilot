from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .services import JournalService
from .models import Account
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

# استيراد دالة التحقق من حالة الاستعادة
try:
    from backup.restore_context import is_restoring
except ImportError:
    # في حالة عدم توفر الوحدة، نفترض أننا لسنا في وضع الاستعادة
    def is_restoring():
        return False


@receiver(post_save, sender='sales.SalesInvoice')
def create_sales_invoice_journal_entry(sender, instance, created, **kwargs):
    """إنشاء أو تحديث القيد المحاسبي لفاتورة المبيعات عند الإنشاء أو التعديل.

    - عند الإنشاء: نُنشئ قيد المبيعات وCOGS.
    - عند التعديل: نُحدّث القيد الموجود إذا وُجد، أو نُنشئه إذا كان مفقوداً.
    """
    # تجاهل أثناء استعادة النسخة الاحتياطية
    if is_restoring():
        return
    
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
    
    # تجاهل أثناء استعادة النسخة الاحتياطية
    if is_restoring():
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
    # تجاهل أثناء استعادة النسخة الاحتياطية
    if is_restoring():
        return
    
    if created and instance.id:
        try:
            # تجنب إنشاء قيد مكرر في حال كان قد تم إنشاؤه بالفعل من مكان آخر
            from journal.models import JournalEntry
            existing = JournalEntry.objects.filter(
                reference_type='receipt_voucher',
                reference_id=instance.id
            ).exists()

            if existing:
                logger.info(f"تجاوز إنشاء قيد محاسبي لسند القبض {instance.receipt_number} لأن القيد موجود بالفعل")
                return

            user = getattr(instance, 'created_by', None)
            if user:
                JournalService.create_receipt_voucher_entry(instance, user)
                logger.info(f"تم إنشاء قيد محاسبي تلقائياً لسند القبض {instance.receipt_number}")
        except Exception as e:
            logger.error(f"خطأ في إنشاء القيد المحاسبي لسند القبض {instance.receipt_number}: {e}")


@receiver(post_save, sender='payments.PaymentVoucher')
def create_payment_voucher_journal_entry(sender, instance, created, **kwargs):
    """إنشاء قيد محاسبي تلقائياً عند إنشاء سند صرف"""
    # تجاهل أثناء استعادة النسخة الاحتياطية
    if is_restoring():
        return
    
    if created and instance.id:
        try:
            # تجنب إنشاء قيد مكرر في حال كان قد تم إنشاؤه بالفعل من مكان آخر
            from journal.models import JournalEntry
            existing = JournalEntry.objects.filter(
                reference_type='payment_voucher',
                reference_id=instance.id
            ).exists()

            if existing:
                logger.info(f"تجاوز إنشاء قيد محاسبي لسند الصرف {instance.voucher_number} لأن القيد موجود بالفعل")
                return

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
    
    # تجاهل أثناء استعادة النسخة الاحتياطية
    if is_restoring():
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
    # تجاهل أثناء استعادة النسخة الاحتياطية
    if is_restoring():
        return
    
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
    # تجاهل أثناء استعادة النسخة الاحتياطية
    if is_restoring():
        return
    
    try:
        JournalService.delete_journal_entry_by_reference('sales_invoice', instance.id)
        logger.info(f"تم حذف القيد المحاسبي لفاتورة المبيعات {instance.invoice_number}")
    except Exception as e:
        logger.error(f"خطأ في حذف القيد المحاسبي لفاتورة المبيعات {instance.invoice_number}: {e}")


@receiver(post_delete, sender='purchases.PurchaseInvoice')
def delete_purchase_invoice_journal_entry(sender, instance, **kwargs):
    """حذف القيد المحاسبي تلقائياً عند حذف فاتورة مشتريات"""
    # تجاهل أثناء استعادة النسخة الاحتياطية
    if is_restoring():
        return
    
    try:
        JournalService.delete_journal_entry_by_reference('purchase_invoice', instance.id)
        logger.info(f"تم حذف القيد المحاسبي لفاتورة المشتريات {instance.invoice_number}")
    except Exception as e:
        logger.error(f"خطأ في حذف القيد المحاسبي لفاتورة المشتريات {instance.invoice_number}: {e}")


@receiver(post_delete, sender='receipts.PaymentReceipt')
def delete_receipt_voucher_journal_entry(sender, instance, **kwargs):
    """حذف القيد المحاسبي تلقائياً عند حذف سند قبض"""
    # تجاهل أثناء استعادة النسخة الاحتياطية
    if is_restoring():
        return
    
    try:
        JournalService.delete_journal_entry_by_reference('receipt_voucher', instance.id)
        logger.info(f"تم حذف القيد المحاسبي لسند القبض {instance.receipt_number}")
    except Exception as e:
        logger.error(f"خطأ في حذف القيد المحاسبي لسند القبض {instance.receipt_number}: {e}")


@receiver(post_delete, sender='payments.PaymentVoucher')
def delete_payment_voucher_journal_entry(sender, instance, **kwargs):
    """حذف القيد المحاسبي تلقائياً عند حذف سند صرف"""
    # تجاهل أثناء استعادة النسخة الاحتياطية
    if is_restoring():
        return
    
    try:
        JournalService.delete_journal_entry_by_reference('payment_voucher', instance.id)
        logger.info(f"تم حذف القيد المحاسبي لسند الصرف {instance.voucher_number}")
    except Exception as e:
        logger.error(f"خطأ في حذف القيد المحاسبي لسند الصرف {instance.voucher_number}: {e}")


@receiver(post_delete, sender='sales.SalesReturn')
def delete_sales_return_journal_entry(sender, instance, **kwargs):
    """حذف القيد المحاسبي تلقائياً عند حذف مردود مبيعات"""
    # تجاهل أثناء استعادة النسخة الاحتياطية
    if is_restoring():
        return
    
    try:
        JournalService.delete_journal_entry_by_reference('sales_return', instance.id)
        logger.info(f"تم حذف القيد المحاسبي لمردود المبيعات {instance.return_number}")
    except Exception as e:
        logger.error(f"خطأ في حذف القيد المحاسبي لمردود المبيعات {instance.return_number}: {e}")


@receiver(post_delete, sender='purchases.PurchaseReturn')
def delete_purchase_return_journal_entry(sender, instance, **kwargs):
    """حذف القيد المحاسبي تلقائياً عند حذف مردود مشتريات"""
    # تجاهل أثناء استعادة النسخة الاحتياطية
    if is_restoring():
        return
    
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
    
    # تجاهل أثناء استعادة النسخة الاحتياطية
    if is_restoring():
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
    # تجاهل أثناء استعادة النسخة الاحتياطية
    if is_restoring():
        return
    
    try:
        JournalService.delete_journal_entry_by_reference('bank_transfer', instance.id)
        logger.info(f"تم حذف القيد المحاسبي للتحويل البنكي {instance.transfer_number}")
    except Exception as e:
        logger.error(f"خطأ في حذف القيد المحاسبي للتحويل البنكي {instance.transfer_number}: {e}")


# إشارات الإيرادات والمصروفات
@receiver(post_save, sender='revenues_expenses.RevenueExpenseEntry')
def create_revenue_expense_journal_entry(sender, instance, created, **kwargs):
    """إنشاء قيد محاسبي تلقائياً عند إنشاء قيد إيراد أو مصروف"""
    # تجاهل أثناء استعادة النسخة الاحتياطية
    if is_restoring():
        return
    
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
    # تجاهل أثناء استعادة النسخة الاحتياطية
    if is_restoring():
        return
    
    try:
        JournalService.delete_journal_entry_by_reference('revenue_expense', instance.id)
        logger.info(f"تم حذف القيد المحاسبي لقيد الإيراد/المصروف {instance.id}")
    except Exception as e:
        logger.error(f"خطأ في حذف القيد المحاسبي لقيد الإيراد/المصروف {instance.id}: {e}")


# إشارات الأصول
@receiver(post_save, sender='assets_liabilities.Asset')
def create_asset_journal_entry(sender, instance, created, **kwargs):
    """إنشاء قيد محاسبي تلقائياً عند إنشاء أصل جديد"""
    # تجاهل أثناء استعادة النسخة الاحتياطية
    if is_restoring():
        return
    
    if created and instance.id and instance.purchase_cost:
        try:
            user = getattr(instance, 'created_by', None)
            if user:
                lines_data = []
                # قيد شراء الأصل: مدين الأصل، دائن الصندوق/البنك
                # يمكن تفعيل هذا لاحقاً عند ربط الحسابات
        except Exception as e:
            logger.error(f"خطأ في إنشاء القيد المحاسبي لشراء الأصل {instance.name}: {e}")


@receiver(post_delete, sender='assets_liabilities.Asset')
def delete_asset_journal_entry(sender, instance, **kwargs):
    """حذف القيد المحاسبي تلقائياً عند حذف أصل"""
    # تجاهل أثناء استعادة النسخة الاحتياطية
    if is_restoring():
        return
    
    try:
        JournalService.delete_journal_entry_by_reference('asset_purchase', instance.id)
        logger.info(f"تم حذف القيد المحاسبي للأصل {instance.name}")
    except Exception as e:
        logger.error(f"خطأ في حذف القيد المحاسبي للأصل {instance.name}: {e}")


# إشارات الخصوم
@receiver(post_save, sender='assets_liabilities.Liability')
def create_liability_journal_entry(sender, instance, created, **kwargs):
    """إنشاء قيد محاسبي تلقائياً عند إنشاء التزام جديد"""
    # تجاهل أثناء استعادة النسخة الاحتياطية
    if is_restoring():
        return
    
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
    # تجاهل أثناء استعادة النسخة الاحتياطية
    if is_restoring():
        return
    
    try:
        JournalService.delete_journal_entry_by_reference('liability', instance.id)
        logger.info(f"تم حذف القيد المحاسبي للالتزام {instance.description}")
    except Exception as e:
        logger.error(f"خطأ في حذف القيد المحاسبي للالتزام {instance.description}: {e}")


# إشارات الإهلاك
@receiver(post_save, sender='assets_liabilities.DepreciationEntry')
def create_depreciation_journal_entry(sender, instance, created, **kwargs):
    """إنشاء قيد محاسبي تلقائياً عند إنشاء قيد إهلاك"""
    # تجاهل أثناء استعادة النسخة الاحتياطية
    if is_restoring():
        return
    
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
    # تجاهل أثناء استعادة النسخة الاحتياطية
    if is_restoring():
        return
    
    try:
        JournalService.delete_journal_entry_by_reference('depreciation', instance.id)
        logger.info(f"تم حذف القيد المحاسبي لإهلاك {instance.asset.name if instance.asset else 'غير محدد'}")
    except Exception as e:
        logger.error(f"خطأ في حذف القيد المحاسبي لإهلاك {instance.asset.name if instance.asset else 'غير محدد'}: {e}")


# إشارات تحويلات الصناديق
@receiver(post_save, sender='cashboxes.CashboxTransfer')
def create_cashbox_transfer_journal_entry(sender, instance, created, **kwargs):
    """إنشاء قيد محاسبي تلقائياً عند إنشاء تحويل صندوق"""
    # تجاهل أثناء استعادة النسخة الاحتياطية
    if is_restoring():
        return
    
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
    # تجاهل أثناء استعادة النسخة الاحتياطية
    if is_restoring():
        return
    
    try:
        JournalService.delete_journal_entry_by_reference('cashbox_transfer', instance.id)
        logger.info(f"تم حذف القيد المحاسبي للتحويل {instance.transfer_number}")
    except Exception as e:
        logger.error(f"خطأ في حذف القيد المحاسبي للتحويل {instance.transfer_number}: {e}")


@receiver(post_save, sender='journal.JournalLine')
@receiver(post_save, sender='journal.JournalLine')
def update_account_balance_on_save(sender, instance, **kwargs):
    """تحديث رصيد الحساب عند حفظ بند قيد محاسبي"""
    if is_restoring():
        return
    
    try:
        # 1. تحديث الحساب المباشر فقط (استدعاء الدالة الآمنة في models.py)
        instance.account.update_account_balance()
        
        # 2. تحديث رصيد الأب (تحديث آمن يمنع استهلاك الذاكرة)
        if instance.account.parent:
            # تحديث الحقل مباشرة في قاعدة البيانات بدون إعادة استدعاء get_balance()
            # سنقوم فقط بتصفير الرصيد أو تحديثه عبر منطق خارجي إن لزم الأمر لاحقاً
            # لتجنب الـ Recursion والـ SIGKILL تماماً:
            parent = instance.account.parent
            Account.objects.filter(pk=parent.pk).update(balance=parent.get_balance(as_of_date=None))
            
            logger.info(f"تم تحديث رصيد الحساب الرئيسي {parent.code} بنجاح.")

        # 3. العمليات الأخرى
        create_cashbox_bank_transaction(instance)
        sync_cashbox_or_bank_balance(instance.account)
        
    except Exception as e:
        logger.error(f"خطأ في تحديث رصيد الحساب {instance.account.code}: {e}")


@receiver(post_delete, sender='journal.JournalLine')
def update_account_balance_on_delete(sender, instance, **kwargs):
    """تحديث رصيد الحساب عند حذف بند قيد محاسبي"""
    # تجاهل أثناء استعادة النسخة الاحتياطية
    if is_restoring():
        return
    
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
        
        # التحقق إذا كان حساب بنك (يبدأ بـ 102)
        elif journal_line.account.code.startswith('102'):
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
        
        # تجاهل القيود التي تم إنشاء معاملاتها يدوياً أو الافتتاحية
        # متوافق مع IFRS - الرصيد الافتتاحي لا يعتبر معاملة
        ignored_reference_types = ['cashbox_transfer', 'bank_transfer', 'bank_initial', 'cashbox_initial', 'bank_adjustment', 'cashbox_adjustment']
        if hasattr(journal_line.journal_entry, 'reference_type') and journal_line.journal_entry.reference_type in ignored_reference_types:
            logger.debug(f"تجاهل إنشاء معاملة صندوق من القيد {journal_line.journal_entry.entry_number} - النوع: {journal_line.journal_entry.reference_type} (تم إنشاء المعاملة يدوياً أو قيد افتتاحي)")
            return
        
        # تجاهل القيود الافتتاحية (IFRS - Opening Balance is equity, not a transaction)
        if 'رصيد افتتاحي' in journal_line.journal_entry.description or 'Opening Balance' in journal_line.journal_entry.description:
            logger.debug(f"تجاهل إنشاء معاملة صندوق من القيد {journal_line.journal_entry.entry_number} - الوصف: {journal_line.journal_entry.description} (قيد رصيد افتتاحي)")
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
        
        # تجاهل القيود التي تم إنشاء معاملاتها يدوياً أو الافتتاحية
        # متوافق مع IFRS - الرصيد الافتتاحي لا يعتبر معاملة بنكية
        ignored_reference_types = ['cashbox_transfer', 'bank_transfer', 'bank_initial', 'bank_adjustment', 'bank_transaction']
        if hasattr(journal_line.journal_entry, 'reference_type') and journal_line.journal_entry.reference_type in ignored_reference_types:
            logger.debug(f"تجاهل إنشاء معاملة بنك من القيد {journal_line.journal_entry.entry_number} - النوع: {journal_line.journal_entry.reference_type} (تم إنشاء المعاملة يدوياً أو قيد افتتاحي)")
            return
        
        # تجاهل القيود التي تحتوي على كلمة "تحويل" في الوصف
        if 'تحويل' in journal_line.journal_entry.description:
            logger.debug(f"تجاهل إنشاء معاملة بنك من القيد {journal_line.journal_entry.entry_number} - الوصف: {journal_line.journal_entry.description} (قيد تحويل)")
            return
        
        # تجاهل القيود التي تم إنشاؤها تلقائياً من معاملات بنكية
        if 'معاملة بنكية' in journal_line.journal_entry.description:
            logger.debug(f"تجاهل إنشاء معاملة بنك من القيد {journal_line.journal_entry.entry_number} - الوصف: {journal_line.journal_entry.description} (تم إنشاء القيد من معاملة بنكية)")
            return
        
        # تجاهل القيود الافتتاحية (IFRS - Opening Balance is equity, not a transaction)
        if 'رصيد افتتاحي' in journal_line.journal_entry.description or 'Opening Balance' in journal_line.journal_entry.description:
            logger.debug(f"تجاهل إنشاء معاملة بنك من القيد {journal_line.journal_entry.entry_number} - الوصف: {journal_line.journal_entry.description} (قيد رصيد افتتاحي)")
            return
        
        # التحقق من أن الحساب مرتبط بحساب بنكي
        if journal_line.account.code.startswith('102') and journal_line.account.bank_account:
            bank = journal_line.account.bank_account
            
            # تحديد نوع الحركة بناءً على المدين/الدائن
            if journal_line.debit > 0:
                # مدين - إيداع أو تحويل وارد
                transaction_type = 'deposit'
                amount = journal_line.debit
            elif journal_line.credit > 0:
                # دائن - سحب أو تحويل صادر
                transaction_type = 'withdrawal'
                amount = journal_line.credit
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
                
        else:
            logger.debug(f"الحساب {journal_line.account.code} ليس حساب بنك أو غير مرتبط بحساب بنكي")
                
    except Exception as e:
        logger.error(f"خطأ في إنشاء حركة البنك: {e}")


def sync_cashbox_balance_from_account(account):
    """
    مزامنة رصيد الصندوق مع رصيد حسابه المحاسبي
    ⚠️ ملاحظة: تم تعطيل التحديث التلقائي لأن CashboxTransaction هو مصدر الحقيقة
    هذه الدالة الآن تُستخدم فقط للمراقبة والتنبيه
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
            # مراقبة التطابق فقط - لا تحديث تلقائي
            # CashboxTransaction هو مصدر الحقيقة للأرصدة
            old_balance = cashbox.balance
            new_balance = account.balance
            
            if old_balance != new_balance:
                # ⚠️ تحذير فقط - لا تحديث تلقائي
                logger.warning(f"⚠️ عدم تطابق: رصيد الصندوق '{cashbox.name}' ({old_balance}) != رصيد الحساب ({new_balance})")
                # ⚠️ لا نقوم بالتحديث - المعاملات هي مصدر الحقيقة
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
        
        if account.code.startswith('102'):
            # البحث عن الحساب البنكي المرتبط مباشرة من الحقل
            bank_account = account.bank_account
            
            if not bank_account:
                # إذا لم يكن مرتبط، حاول البحث بالاسم كطريقة احتياطية
                logger.debug(f'الحساب {account.code} غير مرتبط بحساب بنكي، محاولة البحث بالاسم')
                account_name_parts = account.name.split('-')
                bank_name = account_name_parts[0].strip()
                
                if bank_name.startswith('البنك'):
                    bank_name = bank_name[5:].strip()
                
                bank_account = BankAccount.objects.filter(
                    name__icontains=bank_name
                ).first()
                
                if not bank_account and len(account_name_parts) > 1:
                    bank_account = BankAccount.objects.filter(
                        name__icontains=account_name_parts[-1].strip()
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
        
        # التحقق إذا كان حساب بنك (يبدأ بـ 102)
        elif account.code.startswith('102'):
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
    # تجاهل أثناء استعادة النسخة الاحتياطية
    if is_restoring():
        return
    
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
    # تجاهل أثناء استعادة النسخة الاحتياطية
    if is_restoring():
        return
    
    try:
        from core.signals import log_activity
        from core.middleware import get_current_user

        user = get_current_user()
        if user:
            log_activity(user, 'DELETE', instance, f'تم حذف حساب محاسبي: {instance.name} ({instance.code})')
    except Exception as e:
        logger.error(f"خطأ في تسجيل حذف الحساب {instance.code}: {e}")


@receiver(post_save, sender='journal.JournalEntry')
def create_bank_transfer_from_journal_entry(sender, instance, created, **kwargs):
    """
    إنشاء BankTransfer تلقائياً عند إنشاء قيد محاسبي يمثل تحويلاً بين حسابات بنكية
    """
    # تجاهل أثناء استعادة النسخة الاحتياطية
    if is_restoring():
        return
    
    if not created:
        return  # فقط للقيود الجديدة

    try:
        from banks.models import BankTransfer
        # تجاهل القيود التي تم إنشاؤها تلقائياً من معاملات بنكية أو تحويلات
        if instance.bank_transfer or instance.cashbox_transfer:
            logger.debug(f"تجاهل إنشاء BankTransfer من القيد {instance.entry_number}")
            return

        # التحقق من أن القيد يحتوي على حسابين بنكيين فقط (تحويل بين بنكين)
        bank_lines = []
        for line in instance.lines.all():
            if line.account.code.startswith('102') and line.account.bank_account:
                bank_lines.append(line)

        # يجب أن يكون هناك حسابان بنكيان فقط
        if len(bank_lines) != 2:
            return

        # التحقق من أن أحدهما مدين والآخر دائن (تحويل)
        debit_bank = None
        credit_bank = None
        amount = 0

        for line in bank_lines:
            if line.debit > 0:
                debit_bank = line.account.bank_account
                amount = line.debit
            elif line.credit > 0:
                credit_bank = line.account.bank_account

        if not debit_bank or not credit_bank or debit_bank == credit_bank:
            return

        # التحقق من عدم وجود BankTransfer مكرر
        existing_transfer = BankTransfer.objects.filter(
            from_account=credit_bank,  # الحساب الدائن هو المرسل
            to_account=debit_bank,     # الحساب المدين هو المستقبل
            amount=amount,
            date=instance.entry_date
        ).first()

        if existing_transfer:
            logger.debug(f"BankTransfer موجود بالفعل للقيد {instance.entry_number}")
            return

        # إنشاء BankTransfer
        from core.models import DocumentSequence
        from django.contrib.auth import get_user_model
        User = get_user_model()

        try:
            # الحصول على تسلسل التحويلات البنكية
            sequence = DocumentSequence.objects.get(document_type='bank_transfer')
            transfer_number = sequence.get_next_number()
        except DocumentSequence.DoesNotExist:
            logger.warning(f"تسلسل التحويلات البنكية غير موجود، تخطي إنشاء BankTransfer للقيد {instance.entry_number}")
            return

        # الحصول على المستخدم (افتراضياً superuser إذا لم يكن محدد)
        user = instance.created_by
        if not user:
            user = User.objects.filter(is_superuser=True).first()
            if not user:
                user = User.objects.filter(is_active=True).first()

        if not user:
            logger.warning(f"لا يمكن العثور على مستخدم لإنشاء BankTransfer للقيد {instance.entry_number}")
            return

        # إنشاء BankTransfer
        transfer = BankTransfer.objects.create(
            transfer_number=transfer_number,
            date=instance.entry_date,
            from_account=credit_bank,  # الحساب الدائن هو المرسل
            to_account=debit_bank,     # الحساب المدين هو المستقبل
            amount=amount,
            description=f"تحويل من قيد {instance.entry_number}: {instance.description}",
            created_by=user
        )

        logger.info(f"تم إنشاء BankTransfer تلقائياً من القيد {instance.entry_number}: {transfer.transfer_number}")

        # تسجيل في audit log
        try:
            from core.models import AuditLog
            system_user = User.objects.filter(is_superuser=True).first()
            if system_user:
                AuditLog.objects.create(
                    user=system_user,
                    action_type='create',
                    content_type='BankTransfer',
                    object_id=transfer.id,
                    description=f'إنشاء تحويل بنكي تلقائياً من قيد {instance.entry_number}: {transfer.transfer_number}'
                )
        except Exception as audit_error:
            logger.error(f"خطأ في تسجيل إنشاء BankTransfer في audit log: {audit_error}")

    except Exception as e:
        logger.error(f"خطأ في إنشاء BankTransfer من القيد {instance.entry_number}: {e}")
