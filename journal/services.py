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
        if receipt.payment_type == 'cash':
            cash_account = JournalService.get_cash_account()
            lines_data.append({
                'account_id': cash_account.id,
                'debit': receipt.amount,
                'credit': 0,
                'description': f'قبض نقدي - سند رقم {receipt.receipt_number}'
            })
        else:
            # للشيكات - استخدام اسم البنك
            bank_account = JournalService.get_or_create_bank_account(receipt.bank_name)
            lines_data.append({
                'account_id': bank_account.id,
                'debit': receipt.amount,
                'credit': 0,
                'description': f'شيك رقم {receipt.check_number} - سند رقم {receipt.receipt_number}'
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
                'description': f'سند دفع رقم {payment.voucher_number}'
            })
        else:
            expense_account = JournalService.get_or_create_expense_account(payment.expense_type)
            lines_data.append({
                'account_id': expense_account.id,
                'debit': payment.amount,
                'credit': 0,
                'description': f'مصروف - سند رقم {payment.voucher_number}'
            })
        
        # حساب الصندوق أو البنك (دائن)
        if payment.payment_type == 'cash':
            cash_account = JournalService.get_cash_account()
            lines_data.append({
                'account_id': cash_account.id,
                'debit': 0,
                'credit': payment.amount,
                'description': f'دفع نقدي - سند رقم {payment.voucher_number}'
            })
        else:
            bank_account = JournalService.get_or_create_bank_account(payment.bank)
            lines_data.append({
                'account_id': bank_account.id,
                'debit': 0,
                'credit': payment.amount,
                'description': f'دفع بنكي - سند رقم {payment.voucher_number}'
            })
        
        return JournalService.create_journal_entry(
            entry_date=payment.date,
            reference_type='payment_voucher',
            reference_id=payment.id,
            description=f'سند دفع رقم {payment.voucher_number}',
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
    def get_or_create_bank_account(bank_name_or_obj):
        """الحصول على الحساب البنكي أو إنشاؤه"""
        if bank_name_or_obj:
            # إذا كان string (اسم البنك)
            if isinstance(bank_name_or_obj, str):
                bank_name = bank_name_or_obj
                # إنشاء رمز فريد بناءً على hash الاسم
                import hashlib
                name_hash = hashlib.md5(bank_name.encode()).hexdigest()[:4]
                code = f"1020{name_hash}"
                account, created = Account.objects.get_or_create(
                    code=code,
                    defaults={
                        'name': f'البنك - {bank_name}',
                        'account_type': 'asset',
                        'description': f'حساب البنك {bank_name}'
                    }
                )
                return account
            else:
                # إذا كان كائن بنك
                bank = bank_name_or_obj
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
    
    @staticmethod
    def delete_journal_entry_by_reference(reference_type, reference_id):
        """
        حذف القيد المحاسبي حسب نوع العملية ورقمها
        
        Args:
            reference_type: نوع العملية
            reference_id: رقم العملية المرتبطة
        """
        with transaction.atomic():
            entries = JournalEntry.objects.filter(
                reference_type=reference_type,
                reference_id=reference_id
            )
            for entry in entries:
                entry.delete()
    
    @staticmethod
    def get_or_create_checks_in_transit_account():
        """الحصول على حساب شيكات تحت التحصيل أو إنشاؤه"""
        code = "1103"
        account, created = Account.objects.get_or_create(
            code=code,
            defaults={
                'name': 'شيكات تحت التحصيل',
                'account_type': 'asset',
                'description': 'حساب شيكات تحت التحصيل - IFRS 9'
            }
        )
        return account
    
    @staticmethod
    def get_or_create_accounts_receivable_account():
        """الحصول على حساب ذمم مدينة أو إنشاؤه"""
        code = "1104"
        account, created = Account.objects.get_or_create(
            code=code,
            defaults={
                'name': 'ذمم مدينة',
                'account_type': 'asset',
                'description': 'حساب ذمم مدينة - IFRS 9'
            }
        )
        return account
    
    @staticmethod
    def get_or_create_advance_from_customers_account():
        """الحصول على حساب دفعات مقدمة من العملاء أو إنشاؤه"""
        code = "2101"
        account, created = Account.objects.get_or_create(
            code=code,
            defaults={
                'name': 'دفعات مقدمة من العملاء',
                'account_type': 'liability',
                'description': 'حساب دفعات مقدمة من العملاء - IFRS 9'
            }
        )
        return account
    
    @staticmethod
    def create_check_bounced_entry(receipt, collection_date, user=None):
        """إنشاء قيد يومية للشيك المرتد - IFRS 9 متوافق"""
        lines_data = []
        
        # ذمم مدينة (مدين) - زيادة في الأصول
        accounts_receivable = JournalService.get_or_create_accounts_receivable_account()
        lines_data.append({
            'account_id': accounts_receivable.id,
            'debit': receipt.amount,
            'credit': 0,
            'description': f'ارتداد شيك رقم {receipt.check_number} - سند {receipt.receipt_number}'
        })
        
        # شيكات تحت التحصيل (دائن) - نقص في الأصول
        checks_in_transit = JournalService.get_or_create_checks_in_transit_account()
        lines_data.append({
            'account_id': checks_in_transit.id,
            'debit': 0,
            'credit': receipt.amount,
            'description': f'ارتداد شيك رقم {receipt.check_number} - سند {receipt.receipt_number}'
        })
        
        return JournalService.create_journal_entry(
            entry_date=collection_date,
            reference_type='check_bounced',
            reference_id=receipt.id,
            description=f'قيد ارتداد شيك رقم {receipt.check_number} - {receipt.customer.name}',
            lines_data=lines_data,
            user=user
        )
    
    @staticmethod
    def create_check_early_collection_entry(receipt, collection_date, is_invoice_complete=True, user=None):
        """إنشاء قيد يومية للشيك المحصل مبكراً - IFRS 9 متوافق"""
        lines_data = []
        
        if is_invoice_complete:
            # الفاتورة مكتملة - اعتراف طبيعي بالإيراد
            # حساب البنك (مدين)
            bank_account = JournalService.get_or_create_bank_account(receipt.bank_name)
            lines_data.append({
                'account_id': bank_account.id,
                'debit': receipt.amount,
                'credit': 0,
                'description': f'تحصيل مبكر لشيك رقم {receipt.check_number} - سند {receipt.receipt_number}'
            })
            
            # شيكات تحت التحصيل (دائن)
            checks_in_transit = JournalService.get_or_create_checks_in_transit_account()
            lines_data.append({
                'account_id': checks_in_transit.id,
                'debit': 0,
                'credit': receipt.amount,
                'description': f'تحصيل مبكر لشيك رقم {receipt.check_number} - سند {receipt.receipt_number}'
            })
        else:
            # الفاتورة غير مكتملة - تسجيل كدفعة مقدمة
            # دفعات مقدمة من العملاء (مدين)
            advance_account = JournalService.get_or_create_advance_from_customers_account()
            lines_data.append({
                'account_id': advance_account.id,
                'debit': receipt.amount,
                'credit': 0,
                'description': f'دفعة مقدمة - تحصيل مبكر لشيك رقم {receipt.check_number} - سند {receipt.receipt_number}'
            })
            
            # شيكات تحت التحصيل (دائن)
            checks_in_transit = JournalService.get_or_create_checks_in_transit_account()
            lines_data.append({
                'account_id': checks_in_transit.id,
                'debit': 0,
                'credit': receipt.amount,
                'description': f'دفعة مقدمة - تحصيل مبكر لشيك رقم {receipt.check_number} - سند {receipt.receipt_number}'
            })
        
        return JournalService.create_journal_entry(
            entry_date=collection_date,
            reference_type='check_early_collection',
            reference_id=receipt.id,
            description=f'قيد تحصيل مبكر لشيك رقم {receipt.check_number} - {receipt.customer.name}',
            lines_data=lines_data,
            user=user
        )
    
    @staticmethod
    def process_bounced_check_automatically(receipt, bounce_reason, user=None):
        """معالجة الشيك المرتد تلقائياً وفق IFRS 9"""
        from datetime import datetime
        
        # تحديث سبب الارتداد في الشيك
        receipt.bounce_reason = bounce_reason
        receipt.save()
        
        # إنشاء قيد يومية للشيك المرتد
        collection_date = datetime.now().date()
        
        JournalService.create_check_bounced_entry(
            receipt, collection_date, user=user
        )
        
        # إضافة تنبيه في السجل
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f'تم معالجة الشيك المرتد رقم {receipt.check_number} تلقائياً - سبب الارتداد: {bounce_reason}')
        
        return True
    
    @staticmethod
    def process_check_warnings_automatically(receipt, collection_date, user=None):
        """معالجة تحذيرات الشيكات تلقائياً"""
        from datetime import datetime
        
        warnings_processed = []
        
        # فحص التحصيل المبكر
        if collection_date < receipt.check_due_date:
            # البحث عن الفاتورة المرتبطة
            from sales.models import SalesInvoice
            try:
                invoice = SalesInvoice.objects.filter(
                    customer=receipt.customer,
                    total_amount=receipt.amount,
                    date__lte=receipt.check_date
                ).first()
                
                if invoice:
                    # التحقق من حالة الفاتورة
                    is_invoice_complete = getattr(invoice, 'is_completed', True)
                    
                    if not is_invoice_complete:
                        # إنشاء قيد للدفعة المقدمة
                        JournalService.create_check_early_collection_entry(
                            receipt, collection_date, is_invoice_complete=False, user=user
                        )
                        warnings_processed.append("تم إنشاء قيد دفعة مقدمة من العملاء")
                    else:
                        # اعتراف طبيعي بالإيراد
                        JournalService.create_check_early_collection_entry(
                            receipt, collection_date, is_invoice_complete=True, user=user
                        )
                        warnings_processed.append("تم الاعتراف بالإيراد بشكل طبيعي")
                else:
                    # اعتراف طبيعي
                    JournalService.create_check_early_collection_entry(
                        receipt, collection_date, is_invoice_complete=True, user=user
                    )
                    warnings_processed.append("تم الاعتراف بالإيراد بشكل طبيعي")
            except Exception as e:
                print(f"خطأ في البحث عن الفاتورة المرتبطة: {e}")
        
        # فحص التحصيل المتأخر
        elif collection_date > receipt.check_due_date:
            days_late = (collection_date - receipt.check_due_date).days
            warnings_processed.append(f"تم التحصيل بعد {days_late} يوم من تاريخ الاستحقاق")
        
        return warnings_processed
