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
            
            # التحقق من أن القيد ليس صفرياً
            if total_debit == 0 and total_credit == 0:
                print(f"تجاهل إنشاء قيد صفري للعملية {reference_type} - {reference_id}")
                return None
            
            # التحقق من توازن القيد
            if total_debit != total_credit:
                raise ValueError(_('مجموع المدين يجب أن يساوي مجموع الدائن'))
            
            # إنشاء القيد
            # ملاحظة: entry_type موجود في قاعدة البيانات كـ NOT NULL
            # لكنه ليس في النموذج، لذا نضيفه يدوياً
            entry_type_value = 'daily'  # القيمة الافتراضية
            
            journal_entry = JournalEntry.objects.create(
                entry_date=entry_date,
                reference_id=reference_id,
                description=description,
                total_amount=total_debit,
                created_by=user if user else None,  # يمكن أن يكون None إذا لم يتم تمرير user
                entry_type=entry_type_value  # إضافة entry_type المفقود
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
    @staticmethod
    def create_warehouse_transfer_entry(transfer, user=None):
        """إنشاء قيد محاسبي لتحويل المستودعات"""
        # التحقق من عدم وجود قيد سابق لهذا التحويل
        existing_entry = JournalEntry.objects.filter(
            reference_id=transfer.id
        ).first()
        
        if existing_entry:
            print(f"قيد التحويل موجود بالفعل للتحويل {transfer.transfer_number}: {existing_entry.entry_number}")
            return existing_entry
        
        # التحويلات المخزنية لا تحتاج عادةً إلى قيود محاسبية لأن البضائع لا تزال في المخزون
        # لكن يمكن إنشاء قيد لأغراض التتبع أو تسجيل التكاليف
        
        # حساب إجمالي التكلفة
        total_cost = sum(item.total_cost for item in transfer.items.all())
        
        if total_cost == 0:
            print(f"تجاهل إنشاء قيد للتحويل {transfer.transfer_number} - إجمالي التكلفة صفر")
            return None
        
        # إنشاء قيد لتسجيل حركة المخزون (اختياري - لأغراض التتبع)
        # هذا القيد يسجل انتقال التكلفة من مستودع إلى آخر
        lines_data = [
            {
                'account_id': JournalService.get_inventory_account().id,
                'debit': total_cost,
                'credit': 0,
                'description': f'تحويل مخزون من {transfer.from_warehouse.name} إلى {transfer.to_warehouse.name}'
            },
            {
                'account_id': JournalService.get_inventory_account().id,
                'debit': 0,
                'credit': total_cost,
                'description': f'استلام مخزون من {transfer.from_warehouse.name} إلى {transfer.to_warehouse.name}'
            }
        ]
        
        journal_entry = JournalService.create_journal_entry(
            entry_date=transfer.date,
            reference_type='warehouse_transfer',
            reference_id=transfer.id,
            description=f'تحويل مخزون رقم {transfer.transfer_number} من {transfer.from_warehouse.name} إلى {transfer.to_warehouse.name}',
            lines_data=lines_data,
            user=user
        )
        
        return journal_entry
    
    @staticmethod
    def create_sales_invoice_entry(invoice, user=None):
        """إنشاء قيد فاتورة المبيعات"""
        # التحقق من صحة بيانات الفاتورة
        if not invoice or invoice.total_amount <= 0:
            print(f"تجاهل إنشاء قيد لفاتورة {invoice.invoice_number if invoice else 'غير محدد'} - إجمالي صفر أو سالب")
            return None
        
        # التحقق من صحة البيانات المطلوبة
        if not hasattr(invoice, 'subtotal') or invoice.subtotal < 0:
            print(f"تجاهل إنشاء قيد لفاتورة {invoice.invoice_number} - subtotal غير صحيح")
            return None
        
        if not hasattr(invoice, 'payment_type'):
            print(f"تجاهل إنشاء قيد لفاتورة {invoice.invoice_number} - نوع الدفع غير محدد")
            return None
        
        # التحقق من عدم وجود قيد سابق لهذه الفاتورة
        existing_entry = JournalEntry.objects.filter(
            reference_type='sales_invoice',
            reference_id=invoice.id
        ).first()
        
        if existing_entry:
            print(f"قيد المبيعات موجود بالفعل للفاتورة {invoice.invoice_number}: {existing_entry.entry_number}")
            return existing_entry
        
        lines_data = []
        
        # تحديد الحساب المدين حسب نوع الدفع
        if invoice.payment_type == 'cash':
            # البيع النقدي: حساب النقد/الصندوق (مدين)
            cash_account = JournalService.get_cash_account()
            lines_data.append({
                'account_id': cash_account.id,
                'debit': invoice.total_amount,
                'credit': 0,
                'description': f'نقد - فاتورة مبيعات رقم {invoice.invoice_number}'
            })
        else:
            # البيع الآجل: حساب العميل (مدين)
            customer_account = JournalService.get_or_create_customer_account(invoice.customer)
            lines_data.append({
                'account_id': customer_account.id,
                'debit': invoice.total_amount,
                'credit': 0,
                'description': f'فاتورة مبيعات رقم {invoice.invoice_number}'
            })
        
        # حساب المبيعات والضريبة والخصم
        sales_account = JournalService.get_sales_account()
        
        # التحقق من نوع الضريبة
        is_inclusive_tax = getattr(invoice, 'inclusive_tax', True)  # افتراضياً شاملة
        
        # حساب المبيعات (دائن)
        # المبيعات تساوي الـ subtotal مطروحاً منه أي خصم مبيعات
        sales_amount = invoice.subtotal
        if hasattr(invoice, 'discount_amount') and invoice.discount_amount:
            try:
                sales_amount = Decimal(sales_amount) - Decimal(invoice.discount_amount)
            except Exception:
                sales_amount = invoice.subtotal
        
        lines_data.append({
            'account_id': sales_account.id,
            'debit': 0,
            'credit': sales_amount,
            'description': f'مبيعات - فاتورة رقم {invoice.invoice_number}'
        })
        
        # حساب الضريبة إذا وجدت (دائن)
        if invoice.tax_amount > 0:
            tax_account = JournalService.get_tax_payable_account()
            lines_data.append({
                'account_id': tax_account.id,
                'debit': 0,
                'credit': invoice.tax_amount,
                'description': f'ضريبة مبيعات - فاتورة رقم {invoice.invoice_number}'
            })
        
        # حساب الخصم إذا وجد (مدين - مصروف على البائع)
        # ملاحظة: لا نضيف سطر خصم منفصل هنا لأننا ندرجه ضمن حساب المبيعات (sales_amount)
        
        return JournalService.create_journal_entry(
            entry_date=invoice.date,
            reference_type='sales_invoice',
            reference_id=invoice.id,
            description=f'فاتورة مبيعات رقم {invoice.invoice_number} - {invoice.customer.name if invoice.customer else "نقدي"}',
            lines_data=lines_data,
            user=user
        )
    
    @staticmethod
    def update_sales_invoice_entry(invoice, user=None):
        """تحديث قيد فاتورة المبيعات الموجود"""
        # التحقق من صحة بيانات الفاتورة
        if not invoice or invoice.total_amount <= 0:
            print(f"تجاهل تحديث قيد لفاتورة {invoice.invoice_number if invoice else 'غير محدد'} - إجمالي صفر أو سالب")
            return None
        
        # البحث عن القيد الموجود
        existing_entry = JournalEntry.objects.filter(
            reference_type='sales_invoice',
            reference_id=invoice.id
        ).first()
        
        if not existing_entry:
            print(f"لا يوجد قيد موجود للفاتورة {invoice.invoice_number} - سيتم إنشاء قيد جديد")
            return JournalService.create_sales_invoice_entry(invoice, user)
        
        # تحديث تاريخ القيد ووصفه
        existing_entry.entry_date = invoice.date
        existing_entry.description = f'فاتورة مبيعات رقم {invoice.invoice_number} - {invoice.customer.name if invoice.customer else "نقدي"}'
        existing_entry.total_amount = invoice.total_amount
        existing_entry.save()
        
        # حذف البنود القديمة
        existing_entry.lines.all().delete()
        
        # إنشاء بنود جديدة
        lines_data = []
        
        # تحديد الحساب المدين حسب نوع الدفع
        if invoice.payment_type == 'cash':
            # البيع النقدي: حساب النقد/الصندوق (مدين)
            cash_account = JournalService.get_cash_account()
            lines_data.append({
                'account_id': cash_account.id,
                'debit': invoice.total_amount,
                'credit': 0,
                'description': f'نقد - فاتورة مبيعات رقم {invoice.invoice_number}'
            })
        else:
            # البيع الآجل: حساب العميل (مدين)
            customer_account = JournalService.get_or_create_customer_account(invoice.customer)
            lines_data.append({
                'account_id': customer_account.id,
                'debit': invoice.total_amount,
                'credit': 0,
                'description': f'فاتورة مبيعات رقم {invoice.invoice_number}'
            })
        
        # حساب المبيعات والضريبة والخصم
        sales_account = JournalService.get_sales_account()
        
        # التحقق من نوع الضريبة
        is_inclusive_tax = getattr(invoice, 'inclusive_tax', True)  # افتراضياً شاملة
        
        # حساب المبيعات (دائن)
        # المبيعات تساوي الـ subtotal مطروحاً منه أي خصم مبيعات
        sales_amount = invoice.subtotal
        if hasattr(invoice, 'discount_amount') and invoice.discount_amount:
            try:
                sales_amount = Decimal(sales_amount) - Decimal(invoice.discount_amount)
            except Exception:
                sales_amount = invoice.subtotal
        
        lines_data.append({
            'account_id': sales_account.id,
            'debit': 0,
            'credit': sales_amount,
            'description': f'مبيعات - فاتورة رقم {invoice.invoice_number}'
        })
        
        # حساب الضريبة إذا وجدت (دائن)
        if invoice.tax_amount > 0:
            tax_account = JournalService.get_tax_payable_account()
            lines_data.append({
                'account_id': tax_account.id,
                'debit': 0,
                'credit': invoice.tax_amount,
                'description': f'ضريبة مبيعات - فاتورة رقم {invoice.invoice_number}'
            })
        
        # حساب الخصم إذا وجد (مدين - مصروف على البائع)
        # ملاحظة: لا نضيف سطر خصم منفصل هنا لأن المبلغ تم خصمه من sales_amount أعلاه
        
        # إنشاء بنود القيد الجديدة
        for line_data in lines_data:
            JournalLine.objects.create(
                journal_entry=existing_entry,
                account_id=line_data['account_id'],
                debit=Decimal(str(line_data.get('debit', 0))),
                credit=Decimal(str(line_data.get('credit', 0))),
                line_description=line_data.get('description', '')
            )
        
        print(f"تم تحديث قيد المبيعات {existing_entry.entry_number} للفاتورة {invoice.invoice_number}")
        return existing_entry
    
    @staticmethod
    def create_cogs_entry(invoice, user=None):
        """إنشاء قيد تكلفة البضاعة المباعة"""
        # التحقق من عدم وجود قيد COGS سابق لهذه الفاتورة
        existing_cogs = JournalEntry.objects.filter(
            reference_type='sales_invoice_cogs',
            reference_id=invoice.id
        ).first()
        
        if existing_cogs:
            print(f"قيد COGS موجود بالفعل للفاتورة {invoice.invoice_number}: {existing_cogs.entry_number}")
            return existing_cogs
        
        from inventory.models import InventoryMovement
        from decimal import Decimal
        
        # حساب إجمالي تكلفة البضاعة المباعة من حركات المخزون
        movements = InventoryMovement.objects.filter(
            reference_type='sales_invoice',
            reference_id=invoice.id,
            movement_type='out'
        )
        
        total_cogs = Decimal('0')
        for movement in movements:
            total_cogs += movement.total_cost
        
        if total_cogs <= 0:
            return None  # لا يوجد تكلفة للتسجيل
        
        lines_data = []
        
        # حساب تكلفة البضاعة المباعة (مدين)
        cogs_account = JournalService.get_cogs_account()
        lines_data.append({
            'account_id': cogs_account.id,
            'debit': total_cogs,
            'credit': 0,
            'description': f'تكلفة البضاعة المباعة - فاتورة رقم {invoice.invoice_number}'
        })
        
        # حساب المخزون (دائن)
        inventory_account = JournalService.get_warehouse_account(invoice.warehouse)
        lines_data.append({
            'account_id': inventory_account.id,
            'debit': 0,
            'credit': total_cogs,
            'description': f'انقاص المخزون - فاتورة رقم {invoice.invoice_number}'
        })
        
        return JournalService.create_journal_entry(
            entry_date=invoice.date,
            reference_type='sales_invoice_cogs',
            reference_id=invoice.id,
            description=f'تكلفة البضاعة المباعة - فاتورة مبيعات رقم {invoice.invoice_number}',
            lines_data=lines_data,
            user=user
        )
    
    @staticmethod
    @staticmethod
    def create_purchase_invoice_entry(invoice, user=None):
        """إنشاء قيد فاتورة المشتريات"""
        print(f"DEBUG: Line 376 create_purchase_invoice_entry called for invoice {invoice.invoice_number if invoice else 'None'}")
        # التحقق من صحة بيانات الفاتورة
        if not invoice or invoice.total_amount <= 0:
            print(f"تجاهل إنشاء قيد لفاتورة مشتريات {invoice.invoice_number if invoice else 'غير محدد'} - إجمالي صفر أو سالب")
            return None
        
        # التحقق من صحة البيانات المطلوبة
        if not hasattr(invoice, 'subtotal') or invoice.subtotal < 0:
            print(f"تجاهل إنشاء قيد لفاتورة مشتريات {invoice.invoice_number} - subtotal غير صحيح")
            return None
        
        lines_data = []
        
        # حساب المخزون (مدين) - بقيمة المشتريات
        inventory_account = JournalService.get_warehouse_account(invoice.warehouse)
        lines_data.append({
            'account_id': inventory_account.id,
            'debit': invoice.subtotal,
            'credit': 0,
            'description': f'زيادة المخزون - فاتورة مشتريات رقم {invoice.invoice_number}'
        })
        
        # حساب الضريبة إذا وجدت (مدين)
        if invoice.tax_amount > 0:
            tax_account = JournalService.get_tax_receivable_account()
            lines_data.append({
                'account_id': tax_account.id,
                'debit': invoice.tax_amount,
                'credit': 0,
                'description': f'ضريبة مشتريات - فاتورة رقم {invoice.invoice_number}'
            })
        
        # حسب نوع الدفع أو طريقة الدفع
        if invoice.payment_type == 'cash' or invoice.payment_method == 'cash':
            # للدفع النقدي: دائن للصندوق أو البنك
            cash_account = JournalService.get_cash_account()
            lines_data.append({
                'account_id': cash_account.id,
                'debit': 0,
                'credit': invoice.total_amount,
                'description': f'دفع نقدي لفاتورة مشتريات رقم {invoice.invoice_number}'
            })
        elif invoice.payment_type == 'credit' or invoice.payment_method == 'credit':
            # للدفع الائتماني: دائن للمورد
            supplier_account = JournalService.get_or_create_supplier_account(invoice.supplier)
            lines_data.append({
                'account_id': supplier_account.id,
                'debit': 0,
                'credit': invoice.total_amount,
                'description': f'فاتورة مشتريات رقم {invoice.invoice_number}'
            })
        elif invoice.payment_method == 'check':
            # للدفع بالشيك: دائن لحساب البنك
            bank_account = JournalService.get_or_create_bank_account(invoice.bank_account)
            lines_data.append({
                'account_id': bank_account.id,
                'debit': 0,
                'credit': invoice.total_amount,
                'description': f'دفع شيك لفاتورة مشتريات رقم {invoice.invoice_number}'
            })
        elif invoice.payment_method == 'transfer':
            # للحوالة البنكية: دائن لحساب البنك
            bank_account = JournalService.get_or_create_bank_account(invoice.bank_account)
            lines_data.append({
                'account_id': bank_account.id,
                'debit': 0,
                'credit': invoice.total_amount,
                'description': f'حوالة بنكية لفاتورة مشتريات رقم {invoice.invoice_number}'
            })
        else:
            # افتراضياً اذا لم يتم تحديد طريقة دفع: دائن للمورد (ذمم)
            supplier_account = JournalService.get_or_create_supplier_account(invoice.supplier)
            lines_data.append({
                'account_id': supplier_account.id,
                'debit': 0,
                'credit': invoice.total_amount,
                'description': f'فاتورة مشتريات رقم {invoice.invoice_number}'
            })
        
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
        elif receipt.payment_type == 'bank_transfer':
            # للتحويل البنكي - استخدام الحساب البنكي المحدد
            if receipt.bank_account:
                bank_account = JournalService.get_or_create_bank_account_by_name(
                    receipt.bank_account.name,
                    receipt.bank_account.bank_name
                )
                lines_data.append({
                    'account_id': bank_account.id,
                    'debit': receipt.amount,
                    'credit': 0,
                    'description': f'تحويل بنكي رقم {receipt.bank_transfer_reference} - سند رقم {receipt.receipt_number}'
                })
            else:
                # في حالة عدم وجود حساب بنكي، استخدم حساب عام
                bank_account = JournalService.get_cash_account()
                lines_data.append({
                    'account_id': bank_account.id,
                    'debit': receipt.amount,
                    'credit': 0,
                    'description': f'تحويل بنكي - سند رقم {receipt.receipt_number}'
                })
        else:  # check
            # للشيكات - استخدام حساب شيكات تحت التحصيل
            checks_account = JournalService.get_or_create_checks_in_transit_account()
            lines_data.append({
                'account_id': checks_account.id,
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
            # للمصروفات الأخرى - استخدام حساب مصروفات عام
            expense_account = JournalService.get_or_create_expense_account('other')
            lines_data.append({
                'account_id': expense_account.id,
                'debit': payment.amount,
                'credit': 0,
                'description': f'مصروف - سند رقم {payment.voucher_number}'
            })
        
        # حساب الصندوق أو البنك (دائن)
        if payment.payment_type == 'cash':
            if payment.cashbox:
                cashbox_account = JournalService.get_cashbox_account(payment.cashbox)
                lines_data.append({
                    'account_id': cashbox_account.id,
                    'debit': 0,
                    'credit': payment.amount,
                    'description': f'دفع نقدي من {payment.cashbox.name} - سند رقم {payment.voucher_number}'
                })
            else:
                # في حالة عدم وجود صندوق محدد - استخدام الصندوق العام
                cash_account = JournalService.get_cash_account()
                lines_data.append({
                    'account_id': cash_account.id,
                    'debit': 0,
                    'credit': payment.amount,
                    'description': f'دفع نقدي - سند رقم {payment.voucher_number}'
                })
        elif payment.payment_type == 'bank_transfer':
            # للتحويل البنكي
            if payment.bank:
                bank_account = JournalService.get_bank_account(payment.bank)
                lines_data.append({
                    'account_id': bank_account.id,
                    'debit': 0,
                    'credit': payment.amount,
                    'description': f'تحويل بنكي من {payment.bank.name} - سند رقم {payment.voucher_number}'
                })
            else:
                # في حالة عدم وجود بنك محدد - استخدام حساب بنك عام
                bank_account = JournalService.get_bank_account()
                lines_data.append({
                    'account_id': bank_account.id,
                    'debit': 0,
                    'credit': payment.amount,
                    'description': f'تحويل بنكي - سند رقم {payment.voucher_number}'
                })
        
        return JournalService.create_journal_entry(
            date=payment.date,
            reference_type='payment_voucher',
            reference_id=payment.id,
            description=f'قيد سند الصرف رقم {payment.voucher_number}',
            lines_data=lines_data,
            user=user
        )
    
    @staticmethod
    def create_bank_transfer_entry(transfer, user=None):
        """إنشاء قيد محاسبي لتحويل بنكي"""
        # التحقق من عدم وجود قيد سابق لهذا التحويل
        existing_entry = JournalEntry.objects.filter(
            reference_type='bank_transfer',
            reference_id=transfer.id
        ).first()
        
        if existing_entry:
            print(f"قيد التحويل موجود بالفعل للتحويل {transfer.transfer_number}: {existing_entry.entry_number}")
            return existing_entry
        
        # الحصول على الحسابات المحاسبية للحسابات البنكية
        from_account_obj = JournalService.get_or_create_bank_account(transfer.from_account)
        to_account_obj = JournalService.get_or_create_bank_account(transfer.to_account)
        
        # القيد: مدين لحساب البنك المستقبل، دائن لحساب البنك المرسل
        lines_data = [
            {
                'account_id': to_account_obj.id,
                'debit': transfer.amount,
                'credit': Decimal('0'),
                'description': f'تحويل من {transfer.from_account.name} إلى {transfer.to_account.name} - رقم التحويل: {transfer.transfer_number}'
            },
            {
                'account_id': from_account_obj.id,
                'debit': Decimal('0'),
                'credit': transfer.amount,
                'description': f'تحويل إلى {transfer.to_account.name} من {transfer.from_account.name} - رقم التحويل: {transfer.transfer_number}'
            }
        ]
        
        # إذا كانت هناك رسوم، أضف قيدًا للرسوم
        if transfer.fees > 0:
            # الرسوم تُخصم من الحساب المرسل
            expense_account = JournalService.get_or_create_expense_account('bank_fees')
            lines_data.append({
                'account_id': expense_account.id,
                'debit': transfer.fees,
                'credit': Decimal('0'),
                'description': f'رسوم تحويل بنكي - رقم التحويل: {transfer.transfer_number}'
            })
            # تعديل الدائن للحساب المرسل ليشمل الرسوم
            lines_data[1]['credit'] = transfer.amount + transfer.fees
        
        return JournalService.create_journal_entry(
            entry_date=transfer.date,
            reference_type='bank_transfer',
            reference_id=transfer.id,
            description=f'تحويل بنكي من {transfer.from_account.name} إلى {transfer.to_account.name} - رقم التحويل: {transfer.transfer_number}',
            lines_data=lines_data,
            user=user
        )
    
    @staticmethod
    def create_bank_opening_balance_entry(bank_account, opening_transaction, user=None):
        """
        إنشاء قيد محاسبي للرصيد الافتتاحي للحساب البنكي
        
        حسب IFRS:
        - الرصيد الافتتاحي يمثل أصلاً (النقد في البنك)
        - يجب أن يقابله حساب حقوق الملكية (رأس المال أو الأرباح المحتجزة)
        
        القيد:
        - إذا كان الرصيد موجب (مدين): مدين البنك / دائن رأس المال
        - إذا كان الرصيد سالب (دائن - سحب على المكشوف): مدين رأس المال / دائن البنك
        
        Args:
            bank_account: كائن BankAccount
            opening_transaction: كائن BankTransaction للرصيد الافتتاحي
            user: المستخدم الذي أنشأ القيد
        
        Returns:
            JournalEntry: القيد المحاسبي المنشأ
        """
        # التحقق من عدم وجود قيد سابق
        existing_entry = JournalEntry.objects.filter(
            reference_type='bank_opening_balance',
            reference_id=opening_transaction.id
        ).first()
        
        if existing_entry:
            print(f"⚠ قيد الرصيد الافتتاحي موجود بالفعل للحساب {bank_account.name}: {existing_entry.entry_number}")
            return existing_entry
        
        # الحصول على الحساب المحاسبي للبنك
        bank_account_obj = JournalService.get_or_create_bank_account(bank_account)
        
        # الحصول على حساب رأس المال أو الأرباح المحتجزة
        # نبحث عن حساب رأس المال (3xxx)
        capital_account = Account.objects.filter(code__startswith='301').first()
        if not capital_account:
            # إنشاء حساب رأس المال إذا لم يكن موجوداً
            capital_account = Account.objects.create(
                code='30101',
                name='رأس المال',
                account_type='equity',
                description='حساب رأس المال - حقوق الملكية'
            )
            print(f"✓ تم إنشاء حساب رأس المال: {capital_account.code} - {capital_account.name}")
        
        # تحديد اتجاه القيد بناءً على قيمة الرصيد الافتتاحي
        amount = abs(bank_account.initial_balance)
        
        if bank_account.initial_balance > 0:
            # رصيد افتتاحي موجب (مدين)
            # مدين: البنك / دائن: رأس المال
            lines_data = [
                {
                    'account_id': bank_account_obj.id,
                    'debit': amount,
                    'credit': Decimal('0'),
                    'description': f'رصيد افتتاحي - {bank_account.name}'
                },
                {
                    'account_id': capital_account.id,
                    'debit': Decimal('0'),
                    'credit': amount,
                    'description': f'رصيد افتتاحي - {bank_account.name}'
                }
            ]
        else:
            # رصيد افتتاحي سالب (دائن - سحب على المكشوف)
            # مدين: رأس المال / دائن: البنك
            lines_data = [
                {
                    'account_id': capital_account.id,
                    'debit': amount,
                    'credit': Decimal('0'),
                    'description': f'رصيد افتتاحي (سحب على المكشوف) - {bank_account.name}'
                },
                {
                    'account_id': bank_account_obj.id,
                    'debit': Decimal('0'),
                    'credit': amount,
                    'description': f'رصيد افتتاحي (سحب على المكشوف) - {bank_account.name}'
                }
            ]
        
        try:
            journal_entry = JournalService.create_journal_entry(
                entry_date=opening_transaction.date,
                reference_type='bank_opening_balance',
                reference_id=opening_transaction.id,
                description=f'رصيد افتتاحي للحساب البنكي: {bank_account.name} - {amount} {bank_account.currency}',
                lines_data=lines_data,
                user=user
            )
            
            print(f"✓ تم إنشاء قيد الرصيد الافتتاحي للحساب {bank_account.name}: {journal_entry.entry_number}")
            return journal_entry
            
        except Exception as e:
            print(f"❌ خطأ في إنشاء قيد الرصيد الافتتاحي للحساب {bank_account.name}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
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
    def get_sales_discount_account():
        """الحصول على حساب خصم المبيعات"""
        account, created = Account.objects.get_or_create(
            code='4020',
            defaults={
                'name': 'خصم المبيعات',
                'account_type': 'expense',
                'description': 'حساب خصم المبيعات'
            }
        )
        return account
    
    @staticmethod
    def get_cashbox_account(cashbox):
        """الحصول على حساب الصندوق"""
        account, created = Account.objects.get_or_create(
            code=f'101{cashbox.id:03d}',
            defaults={
                'name': f'صندوق - {cashbox.name}',
                'account_type': 'asset',
                'description': f'حساب الصندوق {cashbox.name}'
            }
        )
        return account
    
    @staticmethod
    def create_cashbox_transfer_entry(transfer, user=None):
        """إنشاء قيد تحويل الصناديق"""
        # التحقق من عدم وجود قيد سابق لهذا التحويل
        existing_entry = JournalEntry.objects.filter(
            reference_type='cashbox_transfer',
            reference_id=transfer.id
        ).first()
        
        if existing_entry:
            print(f"قيد التحويل موجود بالفعل للتحويل {transfer.transfer_number}: {existing_entry.entry_number}")
            return existing_entry
        
        lines_data = []
        
        if transfer.transfer_type == 'cashbox_to_cashbox':
            # تحويل من صندوق إلى صندوق
            from_account = JournalService.get_cashbox_account(transfer.from_cashbox)
            to_account = JournalService.get_cashbox_account(transfer.to_cashbox)
            
            # المدين: الصندوق المستقبل
            lines_data.append({
                'account_id': to_account.id,
                'debit': transfer.amount,
                'credit': 0,
                'description': f'تحويل من {transfer.from_cashbox.name} إلى {transfer.to_cashbox.name}'
            })
            
            # الدائن: الصندوق المرسل
            lines_data.append({
                'account_id': from_account.id,
                'debit': 0,
                'credit': transfer.amount,
                'description': f'تحويل إلى {transfer.to_cashbox.name}'
            })
        
        elif transfer.transfer_type == 'cashbox_to_bank':
            # تحويل من صندوق إلى بنك
            from_account = JournalService.get_cashbox_account(transfer.from_cashbox)
            to_account = JournalService.get_bank_account(transfer.to_bank)
            
            # المدين: حساب البنك
            lines_data.append({
                'account_id': to_account.id,
                'debit': transfer.amount,
                'credit': 0,
                'description': f'إيداع من {transfer.from_cashbox.name} إلى {transfer.to_bank.name}'
            })
            
            # الدائن: الصندوق
            lines_data.append({
                'account_id': from_account.id,
                'debit': 0,
                'credit': transfer.amount,
                'description': f'سحب للإيداع في {transfer.to_bank.name}'
            })
        
        elif transfer.transfer_type == 'bank_to_cashbox':
            # تحويل من بنك إلى صندوق
            from_account = JournalService.get_bank_account(transfer.from_bank)
            to_account = JournalService.get_cashbox_account(transfer.to_cashbox)
            
            # المدين: الصندوق
            lines_data.append({
                'account_id': to_account.id,
                'debit': transfer.amount,
                'credit': 0,
                'description': f'سحب من {transfer.from_bank.name} إلى {transfer.to_cashbox.name}'
            })
            
            # الدائن: حساب البنك
            lines_data.append({
                'account_id': from_account.id,
                'debit': 0,
                'credit': transfer.amount,
                'description': f'سحب للصندوق {transfer.to_cashbox.name}'
            })
        
        # إنشاء القيد
        return JournalService.create_journal_entry(
            entry_date=transfer.date,
            reference_type='cashbox_transfer',
            description=f'تحويل الصناديق: {transfer.transfer_number}',
            lines_data=lines_data,
            reference_id=transfer.id,
            user=user
        )
    
    @staticmethod
    def get_tax_payable_account():
        """الحصول على حساب ضريبة مستحقة الدفع"""
        # أولاً، التأكد من وجود الحساب الرئيسي
        parent_account, created = Account.objects.get_or_create(
            code='2030',
            defaults={
                'name': 'الضرائب المستحقة الدفع',
                'account_type': 'liability',
                'description': 'حساب رئيسي للضرائب المستحقة الدفع'
            }
        )
        
        # إنشاء حساب فرعي لضريبة القيمة المضافة
        vat_code = '203001'
        vat_account, created = Account.objects.get_or_create(
            code=vat_code,
            defaults={
                'name': 'ضريبة القيمة المضافة مستحقة الدفع',
                'account_type': 'liability',
                'parent': parent_account,
                'description': 'ضريبة القيمة المضافة على المبيعات'
            }
        )
        return vat_account
    
    @staticmethod
    def get_tax_receivable_account():
        """الحصول على حساب ضريبة القيمة المضافة المدخلة"""
        account, created = Account.objects.get_or_create(
            code='1070',
            defaults={
                'name': 'ضريبة القيمة المضافة مدخلة',
                'account_type': 'asset',
                'description': 'ضريبة القيمة المضافة المدخلة من المشتريات'
            }
        )
        return account
    
    @staticmethod
    def get_inventory_account():
        """الحصول على حساب المخزون العام"""
        account, created = Account.objects.get_or_create(
            code='1020',
            defaults={
                'name': 'المخزون العام',
                'account_type': 'asset',
                'description': 'حساب المخزون السلعي العام'
            }
        )
        return account
    
    @staticmethod
    def get_warehouse_account(warehouse):
        """الحصول على حساب المستودع"""
        if not warehouse:
            return JournalService.get_inventory_account()
        
        code = f"1201{warehouse.id:04d}"
        account, created = Account.objects.get_or_create(
            code=code,
            defaults={
                'name': f'مستودع - {warehouse.name}',
                'account_type': 'asset',
                'parent': Account.objects.filter(code='1201').first(),
                'description': f'حساب المستودع {warehouse.name}'
            }
        )
        return account
    
    @staticmethod
    def get_cogs_account():
        """الحصول على حساب تكلفة البضاعة المباعة"""
        account, created = Account.objects.get_or_create(
            code='5001',
            defaults={
                'name': 'تكلفة البضاعة المباعة',
                'account_type': 'expense',
                'description': 'تكلفة البضاعة المباعة (COGS)'
            }
        )
        return account
    
    @staticmethod
    def get_purchases_account():
        """الحصول على حساب المشتريات"""
        account, created = Account.objects.get_or_create(
            code='5000',
            defaults={
                'name': 'المشتريات',
                'account_type': 'expense',
                'description': 'حساب المشتريات'
            }
        )
        return account
    
    @staticmethod
    def get_or_create_customer_account(customer):
        """الحصول على حساب العميل أو إنشاؤه"""
        code = f"1301{customer.id:04d}"
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
        code = f"2101{supplier.id:04d}"
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
                        'description': f'حساب البنك {bank.name}',
                        'bank_account': bank
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
    def get_bank_account(bank=None):
        """
        الحصول على الحساب المحاسبي للبنك
        إذا تم تمرير كائن بنك، يتم الحصول على حسابه المحدد
        وإلا يتم إرجاع الحساب النقدي العام
        """
        if bank:
            return JournalService.get_or_create_bank_account(bank)
        else:
            # إرجاع حساب نقدي عام في حالة عدم وجود بنك محدد
            return JournalService.get_cash_account()


    @staticmethod
    def create_sales_return_entry(sales_return, user=None):
        """إنشاء قيد مردود المبيعات"""
        lines_data = []
        
        # حساب المبيعات (مدين) - تخفيض المبيعات
        sales_account = JournalService.get_sales_account()
        lines_data.append({
            'account_id': sales_account.id,
            'debit': sales_return.subtotal,
            'credit': 0,
            'description': f'مردود مبيعات - تخفيض مبيعات رقم {sales_return.return_number}'
        })
        
        # حساب الضريبة إذا وجدت (مدين) - تخفيض الضريبة
        if sales_return.tax_amount > 0:
            tax_account = JournalService.get_tax_payable_account()
            lines_data.append({
                'account_id': tax_account.id,
                'debit': sales_return.tax_amount,
                'credit': 0,
                'description': f'مردود مبيعات - تخفيض ضريبة رقم {sales_return.return_number}'
            })
        
        # دائماً دائن لحساب العميل (مردود المبيعات يعني استرداد المبلغ للعميل)
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
    def create_sales_return_cogs_entry(sales_return, user=None):
        """إنشاء قيد تكلفة البضاعة المسترجعة (عكس COGS)"""
        from inventory.models import InventoryMovement
        from decimal import Decimal
        
        # حساب إجمالي تكلفة البضاعة المسترجعة من حركات المخزون
        movements = InventoryMovement.objects.filter(
            reference_type='sales_return',
            reference_id=sales_return.id,
            movement_type='in'
        )
        
        total_cogs = Decimal('0')
        for movement in movements:
            total_cogs += movement.total_cost
        
        if total_cogs <= 0:
            return None  # لا يوجد تكلفة للتسجيل
        
        lines_data = []
        
        # حساب المخزون (مدين) - زيادة المخزون
        inventory_account = JournalService.get_inventory_account()
        lines_data.append({
            'account_id': inventory_account.id,
            'debit': total_cogs,
            'credit': 0,
            'description': f'زيادة المخزون - مردود مبيعات رقم {sales_return.return_number}'
        })
        
        # حساب تكلفة البضاعة المباعة (دائن) - تخفيض COGS
        cogs_account = JournalService.get_cogs_account()
        lines_data.append({
            'account_id': cogs_account.id,
            'debit': 0,
            'credit': total_cogs,
            'description': f'تخفيض تكلفة البضاعة المباعة - مردود رقم {sales_return.return_number}'
        })
        
        return JournalService.create_journal_entry(
            entry_date=sales_return.date,
            reference_type='sales_return_cogs',
            reference_id=sales_return.id,
            description=f'تكلفة البضاعة المسترجعة - مردود مبيعات رقم {sales_return.return_number}',
            lines_data=lines_data,
            user=user
        )
    
    @staticmethod
    def create_purchase_return_entry(purchase_return, user=None):
        """إنشاء قيد مردود المشتريات"""
        lines_data = []
        
        # حساب المورد (مدين) - تخفيض الذمم الدائنة
        supplier_account = JournalService.get_or_create_supplier_account(purchase_return.supplier)
        lines_data.append({
            'account_id': supplier_account.id,
            'debit': purchase_return.total_amount,
            'credit': 0,
            'description': f'مردود مشتريات رقم {purchase_return.return_number}'
        })
        
        # حساب المشتريات (دائن) - تخفيض المشتريات
        purchases_account = JournalService.get_purchases_account()
        lines_data.append({
            'account_id': purchases_account.id,
            'debit': 0,
            'credit': purchase_return.subtotal,
            'description': f'مردود مشتريات - تخفيض مشتريات رقم {purchase_return.return_number}'
        })
        
        # حساب الضريبة إذا وجدت (دائن) - تخفيض الضريبة
        if purchase_return.tax_amount > 0:
            tax_account = JournalService.get_tax_receivable_account()
            lines_data.append({
                'account_id': tax_account.id,
                'debit': 0,
                'credit': purchase_return.tax_amount,
                'description': f'مردود مشتريات - تخفيض ضريبة رقم {purchase_return.return_number}'
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
    def create_purchase_invoice_entry(invoice, user=None):
        """إنشاء قيد محاسبي لفاتورة المشتريات"""
        try:
            # التحقق من وجود عناصر في الفاتورة
            if not invoice.items.exists():
                print(f"تجاهل إنشاء قيد لفاتورة المشتريات {invoice.invoice_number} - لا توجد عناصر")
                return None
            
            # حساب إجمالي الفاتورة من العناصر مباشرة لضمان الدقة
            from decimal import Decimal
            subtotal = Decimal('0')
            tax_amount = Decimal('0')
            total_amount = Decimal('0')
            
            for item in invoice.items.all():
                subtotal += item.quantity * item.unit_price
                tax_amount += item.tax_amount
                total_amount += item.total_amount
            
            if total_amount <= 0:
                print(f"تجاهل إنشاء قيد لفاتورة المشتريات {invoice.invoice_number} - المبلغ المحسوب صفر أو سالب")
                return None
            
            lines_data = []
            
            # إذا كانت الفاتورة نقدية
            if invoice.payment_type == 'cash':
                # حساب الصندوق (مدين)
                if invoice.cashbox:
                    cash_account = invoice.cashbox.account
                else:
                    # حساب الصندوق الافتراضي
                    cash_account = JournalService.get_cash_account()
                
                lines_data.append({
                    'account_id': cash_account.id,
                    'debit': total_amount,
                    'credit': 0,
                    'description': f'مشتريات نقدية - فاتورة {invoice.invoice_number}'
                })
            
            # إذا كانت الفاتورة بالائتمان
            elif invoice.payment_type == 'credit':
                # حساب المورد (دائن)
                supplier_account = JournalService.get_or_create_supplier_account(invoice.supplier)
                lines_data.append({
                    'account_id': supplier_account.id,
                    'debit': 0,
                    'credit': total_amount,
                    'description': f'مشتريات بالائتمان - فاتورة {invoice.invoice_number}'
                })
            
            # حساب المشتريات (مدين) - لجميع أنواع الفواتير
            purchases_account = JournalService.get_purchases_account()
            lines_data.append({
                'account_id': purchases_account.id,
                'debit': subtotal,
                'credit': 0,
                'description': f'مشتريات - فاتورة {invoice.invoice_number}'
            })
            
            # حساب ضريبة القيمة المضافة المدخلة (مدين) - إذا كانت هناك ضريبة
            if tax_amount > 0:
                vat_input_account = JournalService.get_tax_receivable_account()
                lines_data.append({
                    'account_id': vat_input_account.id,
                    'debit': tax_amount,
                    'credit': 0,
                    'description': f'ضريبة القيمة المضافة المدخلة - فاتورة {invoice.invoice_number}'
                })
            
            # إنشاء القيد المحاسبي
            # استخدام user نظام إذا لم يتم تمرير user
            if not user:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                user = User.objects.filter(username='system').first()
                if not user:
                    # إنشاء user نظام إذا لم يكن موجوداً
                    user = User.objects.create_user(
                        username='system',
                        email='system@finspilot.com',
                        first_name='System',
                        last_name='User'
                    )
            
            return JournalService.create_journal_entry(
                entry_date=invoice.date,
                reference_type='purchase_invoice',
                reference_id=invoice.id,
                description=f'قيد فاتورة مشتريات رقم {invoice.invoice_number} - {invoice.supplier.name}',
                lines_data=lines_data,
                user=user
            )
            
        except Exception as e:
            print(f"خطأ في إنشاء قيد فاتورة المشتريات {invoice.invoice_number}: {e}")
            import traceback
            traceback.print_exc()
            raise e
    
    @staticmethod
    def delete_journal_entry_by_reference(reference_type, reference_id):
        """حذف قيد محاسبي بناءً على نوع المرجع ومعرفه"""
        try:
            entry = JournalEntry.objects.filter(
                reference_type=reference_type,
                reference_id=reference_id
            ).first()
            
            if entry:
                # تسجيل في audit log قبل الحذف
                try:
                    from core.signals import log_activity
                    from core.middleware import get_current_user
                    
                    user = get_current_user()
                    if user:
                        log_activity(
                            user,
                            'DELETE',
                            entry,
                            f'حذف قيد محاسبي: {entry.entry_number} - {entry.description}'
                        )
                except Exception as log_error:
                    print(f"خطأ في تسجيل النشاط: {log_error}")
                
                # حذف القيد
                entry.delete()
                print(f"تم حذف القيد المحاسبي: {entry.entry_number}")
                return True
            else:
                print(f"لم يتم العثور على قيد محاسبي للمرجع: {reference_type} - {reference_id}")
                return False
                
        except Exception as e:
            print(f"خطأ في حذف القيد المحاسبي: {e}")
            import traceback
            traceback.print_exc()
            return False

