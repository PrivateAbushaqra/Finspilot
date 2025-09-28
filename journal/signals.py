from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .services import JournalService
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


@receiver(post_save, sender='sales.SalesInvoice')
def create_sales_invoice_journal_entry(sender, instance, created, **kwargs):
    """إنشاء قيد محاسبي تلقائياً عند إنشاء فاتورة مبيعات"""
    if created and instance.id:
        try:
            # البحث عن المستخدم الذي أنشأ الفاتورة
            user = getattr(instance, 'created_by', None)
            if user:
                # إنشاء قيد الإيرادات
                JournalService.create_sales_invoice_entry(instance, user)
                # إنشاء قيد تكلفة البضاعة المباعة
                JournalService.create_cogs_entry(instance, user)
                logger.info(f"تم إنشاء القيود المحاسبية تلقائياً لفاتورة المبيعات {instance.invoice_number}")
        except Exception as e:
            logger.error(f"خطأ في إنشاء القيود المحاسبية لفاتورة المبيعات {instance.invoice_number}: {e}")


@receiver(post_save, sender='purchases.PurchaseInvoice')
def create_purchase_invoice_journal_entry(sender, instance, created, **kwargs):
    """إنشاء قيد محاسبي تلقائياً عند إنشاء فاتورة مشتريات"""
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
    if created and instance.id and instance.amount:
        try:
            user = getattr(instance, 'created_by', None)
            if user:
                lines_data = []
                # قيد الالتزام: مدين الصندوق/المصروف، دائن الالتزام
                if instance.category and instance.category.account:
                    lines_data = [
                        {
                            'account_id': instance.expense_account.id if instance.expense_account else None,
                            'debit': instance.amount,
                            'credit': 0,
                            'description': f"التزام: {instance.description}"
                        },
                        {
                            'account_id': instance.category.account.id,
                            'debit': 0,
                            'credit': instance.amount,
                            'description': f"التزام: {instance.description}"
                        }
                    ]
                
                if lines_data and all(line['account_id'] is not None for line in lines_data):
                    JournalService.create_journal_entry(
                        entry_date=instance.date,
                        reference_type='liability',
                        reference_id=instance.id,
                        description=f"التزام: {instance.description}",
                        lines_data=lines_data,
                        user=user
                    )
                    logger.info(f"تم إنشاء قيد محاسبي تلقائياً للالتزام {instance.description}")
        except Exception as e:
            logger.error(f"خطأ في إنشاء القيد المحاسبي للالتزام {instance.description}: {e}")


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
    if created and instance.id and instance.amount:
        try:
            user = getattr(instance, 'created_by', None)
            if user:
                lines_data = []
                # قيد الإهلاك: مدين مصروف الإهلاك، دائن مجمع إهلاك الأصل
                if instance.asset and instance.asset.category and instance.asset.category.depreciation_account:
                    lines_data = [
                        {
                            'account_id': instance.asset.category.depreciation_expense_account.id if hasattr(instance.asset.category, 'depreciation_expense_account') and instance.asset.category.depreciation_expense_account else None,
                            'debit': instance.amount,
                            'credit': 0,
                            'description': f"إهلاك {instance.asset.name}"
                        },
                        {
                            'account_id': instance.asset.category.depreciation_account.id,
                            'debit': 0,
                            'credit': instance.amount,
                            'description': f"مجمع إهلاك {instance.asset.name}"
                        }
                    ]
                
                if lines_data and all(line['account_id'] is not None for line in lines_data):
                    JournalService.create_journal_entry(
                        entry_date=instance.date,
                        reference_type='depreciation',
                        reference_id=instance.id,
                        description=f"إهلاك {instance.asset.name}",
                        lines_data=lines_data,
                        user=user
                    )
                    logger.info(f"تم إنشاء قيد محاسبي تلقائياً لإهلاك {instance.asset.name}")
        except Exception as e:
            logger.error(f"خطأ في إنشاء القيد المحاسبي لإهلاك {instance.asset.name if instance.asset else 'غير محدد'}: {e}")


@receiver(post_delete, sender='assets_liabilities.DepreciationEntry')
def delete_depreciation_journal_entry(sender, instance, **kwargs):
    """حذف القيد المحاسبي تلقائياً عند حذف قيد إهلاك"""
    try:
        JournalService.delete_journal_entry_by_reference('depreciation', instance.id)
        logger.info(f"تم حذف القيد المحاسبي لإهلاك {instance.asset.name if instance.asset else 'غير محدد'}")
    except Exception as e:
        logger.error(f"خطأ في حذف القيد المحاسبي لإهلاك {instance.asset.name if instance.asset else 'غير محدد'}: {e}")
