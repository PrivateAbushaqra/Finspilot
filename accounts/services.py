"""
خدمات إدارة الحسابات المالية للعملاء والموردين
"""
from decimal import Decimal
from datetime import date
from .models import AccountTransaction


def create_sales_invoice_transaction(invoice, user):
    """إنشاء حركة حساب لفاتورة مبيعات"""
    # لا نسجل حركة حساب للفواتير النقدية (مدفوعة فوراً)
    # أو للفواتير بدون عميل
    if not invoice.customer or invoice.payment_type == 'cash':
        return None
    
    # فقط الفواتير الآجلة تُسجّل كذمم على العميل
    if invoice.payment_type == 'credit':
        # ذمم - العميل مدين (عليه دين)
        direction = 'debit'
        description = f'فاتورة مبيعات آجلة رقم {invoice.invoice_number}'
    else:
        # أي نوع دفع آخر غير نقدي وآجل
        direction = 'debit'
        description = f'فاتورة مبيعات رقم {invoice.invoice_number}'
    
    return AccountTransaction.create_transaction(
        customer_supplier=invoice.customer,
        transaction_type='sales_invoice',
        direction=direction,
        amount=invoice.total_amount,
        reference_type='sales_invoice',
        reference_id=invoice.id,
        description=description,
        notes=invoice.notes,
        user=user,
        date=invoice.date
    )


def create_purchase_invoice_transaction(invoice, user):
    """إنشاء حركة حساب لفاتورة مشتريات"""
    # لا نسجل حركة حساب للفواتير النقدية (مدفوعة فوراً)
    if invoice.payment_type == 'cash':
        return None
    
    # فقط الفواتير الآجلة تُسجّل كذمم على المورد
    if invoice.payment_type == 'credit':
        # ذمم - المورد دائن (له دين علينا)
        direction = 'credit'
        description = f'فاتورة مشتريات آجلة رقم {invoice.invoice_number}'
    else:
        # أي نوع دفع آخر غير نقدي وآجل
        direction = 'credit'
        description = f'فاتورة مشتريات رقم {invoice.invoice_number}'
    
    return AccountTransaction.create_transaction(
        customer_supplier=invoice.supplier,
        transaction_type='purchase_invoice',
        direction=direction,
        amount=invoice.total_amount,
        reference_type='purchase_invoice',
        reference_id=invoice.id,
        description=description,
        notes=invoice.notes,
        user=user,
        date=invoice.date
    )


def create_sales_return_transaction(sales_return, user):
    """إنشاء حركة حساب لمردود مبيعات"""
    if not sales_return.customer:
        return None  # لا نسجل حركة للعملاء النقديين
    
    # مردود المبيعات يعكس الفاتورة الأصلية
    # إذا كانت الفاتورة الأصلية ذمم -> المردود يقلل الدين على العميل (دائن)
    # إذا كانت الفاتورة الأصلية نقدي -> المردود يزيد رصيد العميل (مدين)
    
    original_invoice = sales_return.original_invoice
    if original_invoice and original_invoice.payment_type == 'credit':
        # الفاتورة الأصلية ذمم -> المردود يقلل الدين
        direction = 'credit'
        description = f'مردود مبيعات ذمم رقم {sales_return.return_number}'
    else:
        # الفاتورة الأصلية نقدي -> المردود يزيد الرصيد
        direction = 'debit'
        description = f'مردود مبيعات نقدي رقم {sales_return.return_number}'
    
    return AccountTransaction.create_transaction(
        customer_supplier=sales_return.customer,
        transaction_type='sales_return',
        direction=direction,
        amount=sales_return.total_amount,
        reference_type='sales_return',
        reference_id=sales_return.id,
        description=description,
        notes=sales_return.notes,
        user=user,
        date=sales_return.date
    )


def create_purchase_return_transaction(purchase_return, user):
    """إنشاء حركة حساب لمردود مشتريات"""
    # مردود المشتريات يعكس الفاتورة الأصلية
    # إذا كانت الفاتورة الأصلية ذمم -> المردود يقلل الدين للمورد (مدين)
    # إذا كانت الفاتورة الأصلية نقدي -> المردود يقلل رصيد المورد (دائن)
    
    original_invoice = purchase_return.original_invoice
    if original_invoice and original_invoice.payment_type == 'credit':
        # الفاتورة الأصلية ذمم -> المردود يقلل الدين للمورد
        direction = 'debit'
        description = f'مردود مشتريات ذمم رقم {purchase_return.return_number}'
    else:
        # الفاتورة الأصلية نقدي -> المردود يقلل الرصيد
        direction = 'credit'
        description = f'مردود مشتريات نقدي رقم {purchase_return.return_number}'
    
    return AccountTransaction.create_transaction(
        customer_supplier=purchase_return.supplier,
        transaction_type='purchase_return',
        direction=direction,
        amount=purchase_return.total_amount,
        reference_type='purchase_return',
        reference_id=purchase_return.id,
        description=description,
        notes=purchase_return.notes,
        user=user,
        date=purchase_return.date
    )


def delete_transaction_by_reference(reference_type, reference_id):
    """حذف الحركة المرتبطة بمرجع معين"""
    try:
        transaction = AccountTransaction.objects.get(
            reference_type=reference_type,
            reference_id=reference_id
        )
        
        # حفظ بيانات العميل/المورد للتحديث
        customer_supplier = transaction.customer_supplier
        transaction.delete()
        
        # إعادة حساب رصيد العميل/المورد
        recalculate_customer_supplier_balance(customer_supplier)
        
        return True
    except AccountTransaction.DoesNotExist:
        return False


def recalculate_customer_supplier_balance(customer_supplier):
    """إعادة حساب رصيد العميل/المورد بناءً على جميع الحركات"""
    transactions = AccountTransaction.objects.filter(
        customer_supplier=customer_supplier
    ).order_by('date', 'created_at')
    
    new_balance = Decimal('0')
    for transaction in transactions:
        if transaction.direction == 'debit':
            new_balance += transaction.amount
        else:
            new_balance -= transaction.amount
    
    # تحديث رصيد العميل/المورد
    customer_supplier.balance = new_balance
    customer_supplier.save()


def get_customer_supplier_statement(customer_supplier, date_from=None, date_to=None):
    """الحصول على كشف حساب العميل/المورد"""
    transactions = AccountTransaction.objects.filter(
        customer_supplier=customer_supplier
    )
    
    if date_from:
        transactions = transactions.filter(date__gte=date_from)
    if date_to:
        transactions = transactions.filter(date__lte=date_to)
    
    transactions = transactions.order_by('date', 'created_at')
    
    # حساب الرصيد الجاري
    running_balance = Decimal('0')
    statement_data = []
    
    for transaction in transactions:
        if transaction.direction == 'debit':
            running_balance += transaction.amount
        else:
            running_balance -= transaction.amount
        
        statement_data.append({
            'transaction': transaction,
            'running_balance': running_balance
        })
    
    return {
        'transactions': statement_data,
        'opening_balance': Decimal('0'),  # يمكن تحسينه لاحقاً
        'closing_balance': running_balance,
        'total_debit': sum(t.amount for t in transactions if t.direction == 'debit'),
        'total_credit': sum(t.amount for t in transactions if t.direction == 'credit'),
    }


def create_payment_transaction(customer_supplier, amount, direction, description, notes='', user=None):
    """إنشاء حركة دفعة"""
    return AccountTransaction.create_transaction(
        customer_supplier=customer_supplier,
        transaction_type='payment',
        direction=direction,
        amount=amount,
        description=description,
        notes=notes,
        user=user
    )


def create_adjustment_transaction(customer_supplier, amount, direction, description, notes='', user=None):
    """إنشاء حركة تسوية"""
    return AccountTransaction.create_transaction(
        customer_supplier=customer_supplier,
        transaction_type='adjustment',
        direction=direction,
        amount=amount,
        description=description,
        notes=notes,
        user=user
    )
