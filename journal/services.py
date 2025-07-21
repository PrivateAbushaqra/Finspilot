from django.db import transaction
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
from datetime import date
from .models import Account, JournalEntry, JournalLine


class JournalService:
    """خدمة إدارة القيود المحاسبية"""
    
    @staticmethod
    def create_journal_entry(entry_date, reference_type, description, lines_data, 
                           reference_id=None, user=None):
        """
        إنشاء قيد محاسبي جديد
        
        Args:
            entry_date: تاريخ القيد
            reference_type: نوع العملية
            description: وصف القيد
            lines_data: قائمة ببيانات البنود [{'account_id': 1, 'debit': 100, 'credit': 0, 'description': '...'}]
            reference_id: رقم العملية المرتبطة
            user: المستخدم الذي أنشأ القيد
        
        Returns:
            JournalEntry: القيد المحاسبي المنشأ
        """
        with transaction.atomic():
            # حساب إجمالي المبلغ
            total_debit = sum(Decimal(str(line.get('debit', 0))) for line in lines_data)
            total_credit = sum(Decimal(str(line.get('credit', 0))) for line in lines_data)
            
            # التحقق من توازن القيد
            if total_debit != total_credit:
                raise ValueError(_('مجموع المدين يجب أن يساوي مجموع الدائن'))
            
            # إنشاء القيد
            journal_entry = JournalEntry.objects.create(
                entry_date=entry_date,
                reference_type=reference_type,
                reference_id=reference_id,
                description=description,
                total_amount=total_debit,
                created_by=user
            )
            
            # إنشاء بنود القيد
            for line_data in lines_data:
                JournalLine.objects.create(
                    journal_entry=journal_entry,
                    account_id=line_data['account_id'],
                    debit=Decimal(str(line_data.get('debit', 0))),
                    credit=Decimal(str(line_data.get('credit', 0))),
                    line_description=line_data.get('description', '')
                )
            
            return journal_entry
    
    @staticmethod
    def create_sales_invoice_entry(invoice, user=None):
        """إنشاء قيد فاتورة المبيعات"""
        lines_data = []
        
        # حساب العميل (مدين)
        customer_account = JournalService.get_or_create_customer_account(invoice.customer)
        lines_data.append({
            'account_id': customer_account.id,
            'debit': invoice.total_amount,
            'credit': 0,
            'description': f'فاتورة مبيعات رقم {invoice.invoice_number}'
        })
        
        # حساب المبيعات (دائن)
        sales_account = JournalService.get_sales_account()
        lines_data.append({
            'account_id': sales_account.id,
            'debit': 0,
            'credit': invoice.subtotal,
            'description': f'مبيعات - فاتورة رقم {invoice.invoice_number}'
        })
        
        # حساب الضريبة إذا وجدت
        if invoice.tax_amount > 0:
            tax_account = JournalService.get_tax_payable_account()
            lines_data.append({
                'account_id': tax_account.id,
                'debit': 0,
                'credit': invoice.tax_amount,
                'description': f'ضريبة مبيعات - فاتورة رقم {invoice.invoice_number}'
            })
        
        return JournalService.create_journal_entry(
            entry_date=invoice.date,
            reference_type='sales_invoice',
            reference_id=invoice.id,
            description=f'فاتورة مبيعات رقم {invoice.invoice_number} - {invoice.customer.name}',
            lines_data=lines_data,
            user=user
        )
    
    @staticmethod
    def create_purchase_invoice_entry(invoice, user=None):
        """إنشاء قيد فاتورة المشتريات"""
        lines_data = []
        
        # حساب المشتريات (مدين)
        purchases_account = JournalService.get_purchases_account()
        lines_data.append({
            'account_id': purchases_account.id,
            'debit': invoice.subtotal,
            'credit': 0,
            'description': f'مشتريات - فاتورة رقم {invoice.invoice_number}'
        })
        
        # حساب الضريبة إذا وجدت
        if invoice.tax_amount > 0:
            tax_account = JournalService.get_tax_receivable_account()
            lines_data.append({
                'account_id': tax_account.id,
                'debit': invoice.tax_amount,
                'credit': 0,
                'description': f'ضريبة مشتريات - فاتورة رقم {invoice.invoice_number}'
            })
        
        # حساب المورد (دائن)
        supplier_account = JournalService.get_or_create_supplier_account(invoice.supplier)
        lines_data.append({
            'account_id': supplier_account.id,
            'debit': 0,
            'credit': invoice.total_amount,
            'description': f'فاتورة مشتريات رقم {invoice.invoice_number}'
        })
        
        return JournalService.create_journal_entry(
            entry_date=invoice.date,
            reference_type='purchase_invoice',
            reference_id=invoice.id,
            description=f'فاتورة مشتريات رقم {invoice.invoice_number} - {invoice.supplier.name}',
            lines_data=lines_data,
            user=user
        )
    
    @staticmethod
    def create_receipt_voucher_entry(receipt, user=None):
        """إنشاء قيد سند القبض"""
        lines_data = []
        
        # حساب الصندوق أو البنك (مدين)
        if receipt.payment_method == 'cash':
            cash_account = JournalService.get_cash_account()
            lines_data.append({
                'account_id': cash_account.id,
                'debit': receipt.amount,
                'credit': 0,
                'description': f'قبض نقدي - سند رقم {receipt.receipt_number}'
            })
        else:
            bank_account = JournalService.get_or_create_bank_account(receipt.bank)
            lines_data.append({
                'account_id': bank_account.id,
                'debit': receipt.amount,
                'credit': 0,
                'description': f'قبض بنكي - سند رقم {receipt.receipt_number}'
            })
        
        # حساب العميل (دائن)
        customer_account = JournalService.get_or_create_customer_account(receipt.customer)
        lines_data.append({
            'account_id': customer_account.id,
            'debit': 0,
            'credit': receipt.amount,
            'description': f'سند قبض رقم {receipt.receipt_number}'
        })
        
        return JournalService.create_journal_entry(
            entry_date=receipt.date,
            reference_type='receipt_voucher',
            reference_id=receipt.id,
            description=f'سند قبض رقم {receipt.receipt_number} - {receipt.customer.name}',
            lines_data=lines_data,
            user=user
        )
    
    @staticmethod
    def create_payment_voucher_entry(payment, user=None):
        """إنشاء قيد سند الصرف"""
        lines_data = []
        
        # حساب المورد أو المصروف (مدين)
        if hasattr(payment, 'supplier') and payment.supplier:
            supplier_account = JournalService.get_or_create_supplier_account(payment.supplier)
            lines_data.append({
                'account_id': supplier_account.id,
                'debit': payment.amount,
                'credit': 0,
                'description': f'سند دفع رقم {payment.payment_number}'
            })
        else:
            expense_account = JournalService.get_or_create_expense_account(payment.expense_type)
            lines_data.append({
                'account_id': expense_account.id,
                'debit': payment.amount,
                'credit': 0,
                'description': f'مصروف - سند رقم {payment.payment_number}'
            })
        
        # حساب الصندوق أو البنك (دائن)
        if payment.payment_method == 'cash':
            cash_account = JournalService.get_cash_account()
            lines_data.append({
                'account_id': cash_account.id,
                'debit': 0,
                'credit': payment.amount,
                'description': f'دفع نقدي - سند رقم {payment.payment_number}'
            })
        else:
            bank_account = JournalService.get_or_create_bank_account(payment.bank)
            lines_data.append({
                'account_id': bank_account.id,
                'debit': 0,
                'credit': payment.amount,
                'description': f'دفع بنكي - سند رقم {payment.payment_number}'
            })
        
        return JournalService.create_journal_entry(
            entry_date=payment.date,
            reference_type='payment_voucher',
            reference_id=payment.id,
            description=f'سند دفع رقم {payment.payment_number}',
            lines_data=lines_data,
            user=user
        )
    
    # دوال مساعدة للحصول على الحسابات أو إنشاؤها
    @staticmethod
    def get_cash_account():
        """الحصول على حساب الصندوق"""
        account, created = Account.objects.get_or_create(
            code='1010',
            defaults={
                'name': 'الصندوق',
                'account_type': 'asset',
                'description': 'حساب الصندوق النقدي'
            }
        )
        return account
    
    @staticmethod
    def get_sales_account():
        """الحصول على حساب المبيعات"""
        account, created = Account.objects.get_or_create(
            code='4010',
            defaults={
                'name': 'المبيعات',
                'account_type': 'sales',
                'description': 'حساب المبيعات'
            }
        )
        return account
    
    @staticmethod
    def get_purchases_account():
        """الحصول على حساب المشتريات"""
        account, created = Account.objects.get_or_create(
            code='5010',
            defaults={
                'name': 'المشتريات',
                'account_type': 'purchases',
                'description': 'حساب المشتريات'
            }
        )
        return account
    
    @staticmethod
    def get_tax_payable_account():
        """الحصول على حساب ضريبة مستحقة الدفع"""
        account, created = Account.objects.get_or_create(
            code='2030',
            defaults={
                'name': 'ضريبة القيمة المضافة مستحقة الدفع',
                'account_type': 'liability',
                'description': 'ضريبة القيمة المضافة على المبيعات'
            }
        )
        return account
    
    @staticmethod
    def get_tax_receivable_account():
        """الحصول على حساب ضريبة مستحقة القبض"""
        account, created = Account.objects.get_or_create(
            code='1070',
            defaults={
                'name': 'ضريبة القيمة المضافة مستحقة القبض',
                'account_type': 'asset',
                'description': 'ضريبة القيمة المضافة على المشتريات'
            }
        )
        return account
    
    @staticmethod
    def get_or_create_customer_account(customer):
        """الحصول على حساب العميل أو إنشاؤه"""
        code = f"1050{customer.id:04d}"
        account, created = Account.objects.get_or_create(
            code=code,
            defaults={
                'name': f'العميل - {customer.name}',
                'account_type': 'asset',
                'description': f'حساب العميل {customer.name}'
            }
        )
        return account
    
    @staticmethod
    def get_or_create_supplier_account(supplier):
        """الحصول على حساب المورد أو إنشاؤه"""
        code = f"2050{supplier.id:04d}"
        account, created = Account.objects.get_or_create(
            code=code,
            defaults={
                'name': f'المورد - {supplier.name}',
                'account_type': 'liability',
                'description': f'حساب المورد {supplier.name}'
            }
        )
        return account
    
    @staticmethod
    def get_or_create_bank_account(bank):
        """الحصول على الحساب البنكي أو إنشاؤه"""
        if bank:
            code = f"1020{bank.id:04d}"
            account, created = Account.objects.get_or_create(
                code=code,
                defaults={
                    'name': f'البنك - {bank.name}',
                    'account_type': 'asset',
                    'description': f'حساب البنك {bank.name}'
                }
            )
            return account
        return JournalService.get_cash_account()
    
    @staticmethod
    def get_or_create_expense_account(expense_type):
        """الحصول على حساب المصروف أو إنشاؤه"""
        code = "6010"  # رمز افتراضي للمصاريف
        account, created = Account.objects.get_or_create(
            code=code,
            defaults={
                'name': 'المصاريف العامة',
                'account_type': 'expense',
                'description': 'حساب المصاريف العامة'
            }
        )
        return account

    @staticmethod
    def create_sales_return_entry(sales_return, user=None):
        """إنشاء قيد مردود المبيعات"""
        lines_data = []
        
        # حساب مردود المبيعات (مدين)
        sales_return_account = JournalService.get_sales_return_account()
        lines_data.append({
            'account_id': sales_return_account.id,
            'debit': sales_return.subtotal,
            'credit': 0,
            'description': f'مردود مبيعات - فاتورة رقم {sales_return.return_number}'
        })
        
        # حساب الضريبة إذا وجدت (مدين)
        if sales_return.tax_amount > 0:
            tax_account = JournalService.get_tax_payable_account()
            lines_data.append({
                'account_id': tax_account.id,
                'debit': sales_return.tax_amount,
                'credit': 0,
                'description': f'ضريبة مردود مبيعات - فاتورة رقم {sales_return.return_number}'
            })
        
        # حساب العميل (دائن)
        customer_account = JournalService.get_or_create_customer_account(sales_return.customer)
        lines_data.append({
            'account_id': customer_account.id,
            'debit': 0,
            'credit': sales_return.total_amount,
            'description': f'مردود مبيعات رقم {sales_return.return_number}'
        })
        
        return JournalService.create_journal_entry(
            entry_date=sales_return.date,
            reference_type='sales_return',
            reference_id=sales_return.id,
            description=f'مردود مبيعات رقم {sales_return.return_number} - {sales_return.customer.name}',
            lines_data=lines_data,
            user=user
        )
    
    @staticmethod
    def create_purchase_return_entry(purchase_return, user=None):
        """إنشاء قيد مردود المشتريات"""
        lines_data = []
        
        # حساب المورد (مدين)
        supplier_account = JournalService.get_or_create_supplier_account(purchase_return.supplier)
        lines_data.append({
            'account_id': supplier_account.id,
            'debit': purchase_return.total_amount,
            'credit': 0,
            'description': f'مردود مشتريات رقم {purchase_return.return_number}'
        })
        
        # حساب مردود المشتريات (دائن)
        purchases_return_account = JournalService.get_purchases_return_account()
        lines_data.append({
            'account_id': purchases_return_account.id,
            'debit': 0,
            'credit': purchase_return.subtotal,
            'description': f'مردود مشتريات - فاتورة رقم {purchase_return.return_number}'
        })
        
        # حساب الضريبة إذا وجدت (دائن)
        if purchase_return.tax_amount > 0:
            tax_account = JournalService.get_tax_receivable_account()
            lines_data.append({
                'account_id': tax_account.id,
                'debit': 0,
                'credit': purchase_return.tax_amount,
                'description': f'ضريبة مردود مشتريات - فاتورة رقم {purchase_return.return_number}'
            })
        
        return JournalService.create_journal_entry(
            entry_date=purchase_return.date,
            reference_type='purchase_return',
            reference_id=purchase_return.id,
            description=f'مردود مشتريات رقم {purchase_return.return_number} - {purchase_return.supplier.name}',
            lines_data=lines_data,
            user=user
        )
    
    @staticmethod
    def get_sales_return_account():
        """الحصول على حساب مردود المبيعات"""
        account, created = Account.objects.get_or_create(
            code='4020',
            defaults={
                'name': 'مردود المبيعات',
                'account_type': 'sales',
                'description': 'حساب مردود المبيعات'
            }
        )
        return account
    
    @staticmethod
    def get_purchases_return_account():
        """الحصول على حساب مردود المشتريات"""
        account, created = Account.objects.get_or_create(
            code='5020',
            defaults={
                'name': 'مردود المشتريات',
                'account_type': 'purchases',
                'description': 'حساب مردود المشتريات'
            }
        )
        return account
    
    @staticmethod
    def delete_journal_entry_by_reference(reference_type, reference_id):
        """حذف القيد المحاسبي المرتبط بمرجع معين"""
        try:
            journal_entry = JournalEntry.objects.get(
                reference_type=reference_type,
                reference_id=reference_id
            )
            journal_entry.delete()
            return True
        except JournalEntry.DoesNotExist:
            return False
        except Exception:
            return False
    
    @staticmethod
    def get_journal_entries_by_type(reference_type, start_date=None, end_date=None):
        """الحصول على القيود حسب النوع والتاريخ"""
        entries = JournalEntry.objects.filter(reference_type=reference_type)
        
        if start_date:
            entries = entries.filter(entry_date__gte=start_date)
        if end_date:
            entries = entries.filter(entry_date__lte=end_date)
        
        return entries.order_by('-entry_date')
    
    @staticmethod
    def update_account_balances():
        """تحديث أرصدة جميع الحسابات"""
        for account in Account.objects.filter(is_active=True):
            account.balance = account.get_balance()
            account.save(update_fields=['balance'])
