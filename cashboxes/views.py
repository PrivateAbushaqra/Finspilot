from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone
from django.core.paginator import Paginator
from decimal import Decimal
from django.views.generic import View
from django.utils.decorators import method_decorator
from django.db.models import ProtectedError
from core.models import AuditLog

from .models import Cashbox, CashboxTransfer, CashboxTransaction
from banks.models import BankAccount


def get_transaction_document_url(transaction):
    """الحصول على رابط صفحة تفاصيل المستند للمعاملة"""
    if transaction.reference_type and transaction.reference_id:
        if transaction.reference_type == 'sales_invoice':
            return f'/ar/sales/invoices/{transaction.reference_id}/'
        elif transaction.reference_type == 'purchase_invoice':
            return f'/ar/purchases/invoices/{transaction.reference_id}/'
        elif transaction.reference_type == 'receipt':
            return f'/ar/receipts/{transaction.reference_id}/'
        elif transaction.reference_type == 'payment':
            return f'/ar/payments/{transaction.reference_id}/'
        elif transaction.reference_type == 'transfer':
            return f'/ar/cashboxes/transfers/{transaction.reference_id}/'
    
    if transaction.related_transfer:
        return f'/ar/cashboxes/transfers/{transaction.related_transfer.id}/'
    
    # محاولة البحث عن المستند من الوصف
    doc_num = get_document_number_from_description(transaction.description)
    if doc_num:
        # البحث في الفواتير
        from sales.models import SalesInvoice
        from purchases.models import PurchaseInvoice
        from receipts.models import PaymentReceipt
        from payments.models import PaymentVoucher
        
        # البحث برقم الفاتورة
        try:
            if 'فاتورة' in transaction.description.lower():
                # فاتورة مبيعات
                invoice = SalesInvoice.objects.filter(invoice_number=doc_num).first()
                if invoice:
                    return f'/ar/sales/invoices/{invoice.id}/'
                
                # فاتورة مشتريات
                invoice = PurchaseInvoice.objects.filter(invoice_number=doc_num).first()
                if invoice:
                    return f'/ar/purchases/invoices/{invoice.id}/'
            
            # البحث في السندات
            receipt = PaymentReceipt.objects.filter(receipt_number=doc_num).first()
            if receipt:
                return f'/ar/receipts/{receipt.id}/'
            
            payment = PaymentVoucher.objects.filter(voucher_number=doc_num).first()
            if payment:
                return f'/ar/payments/{payment.id}/'
                
        except Exception:
            pass
    
    return None


def get_document_number_from_description(description):
    """استخراج رقم المستند من الوصف"""
    import re
    if not description:
        return None
    
    # أنماط شائعة لأرقام المستندات
    patterns = [
        r'فاتورة رقم\s*([A-Za-z0-9\-]+)',  # فاتورة رقم INV-001
        r'رقم\s*([A-Za-z0-9\-]+)',  # رقم INV-001
        r'#([A-Za-z0-9\-]+)',  # #INV-001
        r'([A-Za-z]{2,}-[0-9]+)',  # INV-001, REC-001, PAY-001
        r'([A-Za-z]{3,}[0-9]+)',  # INV001, REC001
        r'سند\s+(قبض|دفع|صرف)\s+([A-Za-z0-9\-]+)',  # سند قبض REC-001
        r'([0-9]{3,}-?[0-9]*)',  # أرقام مثل 001, 001-1, 12345
    ]
    
    for pattern in patterns:
        match = re.search(pattern, description)
        if match:
            if 'سند' in pattern:
                result = match.group(2)
            else:
                result = match.group(1)
            
            # تجنب استخراج التواريخ أو المبالغ
            if len(result) >= 3 and not result.startswith(('20', '19')) and not '.' in result:
                return result
    
    return None


@login_required
def cashbox_list(request):
    """قائمة الصناديق"""
    from settings.models import Currency
    from banks.models import BankAccount
    from django.utils import timezone
    
    cashboxes = Cashbox.objects.filter(is_active=True).order_by('name')
    
    # إحصائيات سريعة
    total_balance = sum(cashbox.balance for cashbox in cashboxes)
    
    # العملات المتاحة
    currencies = Currency.objects.filter(is_active=True).order_by('name')
    base_currency = Currency.get_base_currency()
    
    # البيانات المطلوبة للmodal
    banks = BankAccount.objects.filter(is_active=True).order_by('name')
    
    # الحصول على رقم التحويل التالي
    from core.models import DocumentSequence
    next_transfer_number = None
    try:
        sequence = DocumentSequence.objects.get(document_type='cashbox_transfer')
        next_transfer_number = sequence.get_next_number()
    except DocumentSequence.DoesNotExist:
        # في حالة عدم وجود تسلسل، استخدم الطريقة القديمة
        prefix = 'CT'
        date_str = timezone.now().strftime('%Y%m%d')
        
        # البحث عن آخر رقم في نفس اليوم
        last_transfer = CashboxTransfer.objects.filter(
            transfer_number__startswith=f'{prefix}{date_str}'
        ).order_by('-transfer_number').first()
        
        if last_transfer:
            last_number = int(last_transfer.transfer_number[-4:])
            new_number = last_number + 1
        else:
            new_number = 1
        
        next_transfer_number = f'{prefix}{date_str}{new_number:04d}'
    
    context = {
        'cashboxes': cashboxes,
        'total_balance': total_balance,
        'currencies': currencies,
        'base_currency': base_currency,
        'banks': banks,
        'next_transfer_number': next_transfer_number,
        'today': timezone.now().date(),
        'page_title': _('Cashboxes'),
    }
    return render(request, 'cashboxes/cashbox_list.html', context)


@login_required
def cashbox_detail(request, cashbox_id):
    """تفاصيل الصندوق"""
    from settings.models import Currency
    
    cashbox = get_object_or_404(Cashbox, id=cashbox_id)
    
    # الحصول على حركات الصندوق
    transactions = CashboxTransaction.objects.filter(
        cashbox=cashbox
    ).order_by('-date', '-created_at')
    
    # التقسيم لصفحات
    paginator = Paginator(transactions, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # إضافة document_url لكل transaction
    for transaction in page_obj:
        transaction.document_url = get_transaction_document_url(transaction)
    
    # العملات المتاحة
    currencies = Currency.objects.filter(is_active=True).order_by('name')
    
    context = {
        'cashbox': cashbox,
        'transactions': page_obj,
        'currencies': currencies,
        'page_title': f'{_("Cashbox Details")} - {cashbox.name}',
    }
    return render(request, 'cashboxes/cashbox_detail.html', context)


@login_required
def cashbox_create(request):
    """إنشاء صندوق جديد"""
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        initial_balance = request.POST.get('initial_balance', 0)
        currency = request.POST.get('currency', '')
        location = request.POST.get('location', '')
        responsible_user_id = request.POST.get('responsible_user')
        
        if not name:
            messages.error(request, _('Cashbox name is required'))
            return redirect('cashboxes:cashbox_list')
        
        try:
            with transaction.atomic():
                cashbox = Cashbox.objects.create(
                    name=name,
                    description=description,
                    balance=Decimal(initial_balance or 0),
                    currency=currency,
                    location=location,
                    responsible_user_id=responsible_user_id if responsible_user_id else None
                )
                
                # إضافة حركة الرصيد الافتتاحي إذا كان أكبر من صفر
                if Decimal(initial_balance or 0) > 0:
                    CashboxTransaction.objects.create(
                        cashbox=cashbox,
                        transaction_type='initial_balance',
                        date=timezone.now().date(),
                        amount=Decimal(initial_balance),
                        description=_('Opening Balance'),
                        created_by=request.user
                    )
                
                # تسجيل النشاط في سجل الأنشطة
                AuditLog.objects.create(
                    user=request.user,
                    action_type='create',
                    content_type='Cashbox',
                    object_id=cashbox.id,
                    description=f'إنشاء صندوق نقدي جديد: {name}',
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                
                messages.success(request, _('Cashbox created successfully'))
                return redirect('cashboxes:cashbox_detail', cashbox_id=cashbox.id)
        except Exception as e:
            messages.error(request, _('An error occurred while creating the cashbox'))
    
    return redirect('cashboxes:cashbox_list')


@login_required
def cashbox_edit(request, cashbox_id):
    """تعديل الصندوق"""
    cashbox = get_object_or_404(Cashbox, id=cashbox_id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        currency = request.POST.get('currency', '')
        location = request.POST.get('location', '')
        responsible_user_id = request.POST.get('responsible_user')
        
        if not name:
            messages.error(request, _('Cashbox name is required'))
            return redirect('cashboxes:cashbox_detail', cashbox_id=cashbox_id)
        
        try:
            cashbox.name = name
            cashbox.description = description
            cashbox.currency = currency
            cashbox.location = location
            cashbox.responsible_user_id = responsible_user_id if responsible_user_id else None
            cashbox.save()
            
            # تسجيل النشاط في سجل الأنشطة
            AuditLog.objects.create(
                user=request.user,
                action_type='update',
                content_type='Cashbox',
                object_id=cashbox_id,
                description=f'تعديل الصندوق: {name}',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            messages.success(request, _('Cashbox updated successfully'))
            return redirect('cashboxes:cashbox_detail', cashbox_id=cashbox_id)
        except Exception as e:
            messages.error(request, _('An error occurred while updating the cashbox'))
    
    return redirect('cashboxes:cashbox_detail', cashbox_id=cashbox_id)


@login_required
def transfer_create(request):
    """إنشاء تحويل"""
    # التحقق من وجود تسلسل المستندات
    from core.models import DocumentSequence
    try:
        sequence = DocumentSequence.objects.get(document_type='cashbox_transfer')
    except DocumentSequence.DoesNotExist:
        messages.warning(request, _('Warning: Cashbox transfer sequence is not set! Please add the "Cashbox Transfer" sequence in Settings before creating any transfer.'))
    
    if request.method == 'POST':
        transfer_type = request.POST.get('transfer_type')
        date = request.POST.get('date')
        amount = request.POST.get('amount')
        fees = request.POST.get('fees', 0)
        exchange_rate = request.POST.get('exchange_rate', 1)
        description = request.POST.get('description', '')
        transfer_number = request.POST.get('transfer_number', '').strip()
        
        # معلومات الإيداع (للتحويل من صندوق إلى بنك)
        deposit_document_number = request.POST.get('deposit_document_number', '').strip()
        deposit_type = request.POST.get('deposit_type', '').strip()
        check_number = request.POST.get('check_number', '').strip()
        check_date = request.POST.get('check_date', '')
        check_bank_name = request.POST.get('check_bank_name', '').strip()
        
        # معرفات المصدر والهدف
        from_cashbox_id = request.POST.get('from_cashbox')
        to_cashbox_id = request.POST.get('to_cashbox')
        from_bank_id = request.POST.get('from_bank')
        to_bank_id = request.POST.get('to_bank')
        
        if not all([transfer_type, date, amount]):
            messages.error(request, _('All fields are required'))
            return redirect('cashboxes:transfer_list')
        
        # التحقق من معلومات الإيداع للتحويل من صندوق إلى بنك
        if transfer_type == 'cashbox_to_bank':
            if not deposit_document_number:
                messages.error(request, _('Deposit document number is required for transfers to bank'))
                return redirect('cashboxes:transfer_list')
            if not deposit_type:
                messages.error(request, _('Deposit type is required'))
                return redirect('cashboxes:transfer_list')
            if deposit_type == 'check':
                if not check_number:
                    messages.error(request, _('Check number is required when deposit type is "Check"'))
                    return redirect('cashboxes:transfer_list')
                if not check_date:
                    messages.error(request, _('Check date is required'))
                    return redirect('cashboxes:transfer_list')
                if not check_bank_name:
                    messages.error(request, _('Check bank name is required'))
                    return redirect('cashboxes:transfer_list')
        
        # التحقق من رقم التحويل إذا تم إدخاله
        if transfer_number:
            # التحقق من عدم تكرار الرقم
            if CashboxTransfer.objects.filter(transfer_number=transfer_number).exists():
                messages.error(request, _('Transfer number already exists! Please use another number.'))
                return redirect('cashboxes:transfer_list')
        
        try:
            amount = Decimal(amount)
            fees = Decimal(fees or 0)
            exchange_rate = Decimal(exchange_rate or 1)
            
            if amount <= 0:
                messages.error(request, _('Amount must be greater than zero'))
                return redirect('cashboxes:transfer_list')
            
            with transaction.atomic():
                # تحديد رقم التحويل
                if transfer_number:
                    # استخدام الرقم المُدخل
                    final_transfer_number = transfer_number
                else:
                    # معاينة الرقم التالي دون حجزه
                    try:
                        sequence = DocumentSequence.objects.get(document_type='cashbox_transfer')
                        final_transfer_number = sequence.peek_next_number()
                    except DocumentSequence.DoesNotExist:
                        # استخدام الطريقة القديمة
                        from django.utils import timezone
                        prefix = 'CT'
                        date_str = timezone.now().strftime('%Y%m%d')
                        
                        # البحث عن آخر رقم مُستخدم فعلياً
                        last_transfer = CashboxTransfer.objects.filter(
                            transfer_number__startswith=f'{prefix}{date_str}'
                        ).order_by('-transfer_number').first()
                        
                        if last_transfer:
                            last_number = int(last_transfer.transfer_number[-4:])
                            new_number = last_number + 1
                        else:
                            new_number = 1
                        
                        final_transfer_number = f'{prefix}{date_str}{new_number:04d}'
                
                # إنشاء التحويل
                transfer = CashboxTransfer.objects.create(
                    transfer_number=final_transfer_number,
                    transfer_type=transfer_type,
                    date=date,
                    amount=amount,
                    fees=fees,
                    exchange_rate=exchange_rate,
                    description=description,
                    from_cashbox_id=from_cashbox_id if from_cashbox_id else None,
                    to_cashbox_id=to_cashbox_id if to_cashbox_id else None,
                    from_bank_id=from_bank_id if from_bank_id else None,
                    to_bank_id=to_bank_id if to_bank_id else None,
                    # معلومات الإيداع
                    deposit_document_number=deposit_document_number if transfer_type == 'cashbox_to_bank' else '',
                    deposit_type=deposit_type if transfer_type == 'cashbox_to_bank' else '',
                    check_number=check_number if deposit_type == 'check' else '',
                    check_date=check_date if deposit_type == 'check' and check_date else None,
                    check_bank_name=check_bank_name if deposit_type == 'check' else '',
                    created_by=request.user
                )
                
                # معالجة الحركات حسب نوع التحويل
                if transfer_type == 'cashbox_to_cashbox':
                    from_cashbox = get_object_or_404(Cashbox, id=from_cashbox_id)
                    to_cashbox = get_object_or_404(Cashbox, id=to_cashbox_id)
                    
                    # التحقق من الرصيد
                    if from_cashbox.balance < amount:
                        messages.error(request, _('Insufficient balance in the sender cashbox'))
                        return redirect('cashboxes:transfer_list')
                    
                    # تحديث الأرصدة
                    from_cashbox.balance -= amount
                    to_cashbox.balance += amount
                    from_cashbox.save()
                    to_cashbox.save()
                    
                    # إضافة الحركات
                    CashboxTransaction.objects.create(
                        cashbox=from_cashbox,
                        transaction_type='transfer_out',
                        date=date,
                        amount=-amount,
                        description=f'{description} - {_("Transfer to")} {to_cashbox.name}',
                        related_transfer=transfer,
                        reference_type='transfer',
                        reference_id=transfer.id,
                        created_by=request.user
                    )
                    
                    CashboxTransaction.objects.create(
                        cashbox=to_cashbox,
                        transaction_type='transfer_in',
                        date=date,
                        amount=amount,
                        description=f'{description} - {_("Transfer from")} {from_cashbox.name}',
                        related_transfer=transfer,
                        reference_type='transfer',
                        reference_id=transfer.id,
                        created_by=request.user
                    )
                
                elif transfer_type == 'cashbox_to_bank':
                    from_cashbox = get_object_or_404(Cashbox, id=from_cashbox_id)
                    to_bank = get_object_or_404(BankAccount, id=to_bank_id)
                    
                    # التحقق من الرصيد
                    if from_cashbox.balance < amount:
                        messages.error(request, _('Insufficient balance in the cashbox'))
                        return redirect('cashboxes:transfer_list')
                    
                    # تحديث الأرصدة
                    from_cashbox.balance -= amount
                    to_bank.balance += amount
                    from_cashbox.save()
                    to_bank.save()
                    
                    # إضافة الحركات
                    CashboxTransaction.objects.create(
                        cashbox=from_cashbox,
                        transaction_type='transfer_out',
                        date=date,
                        amount=-amount,
                        description=f'{description} - {_("Transfer to Bank")} {to_bank.name}',
                        related_transfer=transfer,
                        reference_type='transfer',
                        reference_id=transfer.id,
                        created_by=request.user
                    )
                
                elif transfer_type == 'bank_to_cashbox':
                    from_bank = get_object_or_404(BankAccount, id=from_bank_id)
                    to_cashbox = get_object_or_404(Cashbox, id=to_cashbox_id)
                    
                    # التحقق من الرصيد
                    if from_bank.balance < amount:
                        messages.error(request, _('Insufficient balance in the bank'))
                        return redirect('cashboxes:transfer_list')
                    
                    # تحديث الأرصدة
                    from_bank.balance -= amount
                    to_cashbox.balance += amount
                    from_bank.save()
                    to_cashbox.save()
                    
                    # إضافة الحركات
                    CashboxTransaction.objects.create(
                        cashbox=to_cashbox,
                        transaction_type='transfer_in',
                        date=date,
                        amount=amount,
                        description=f'{description} - {_("Transfer from Bank")} {from_bank.name}',
                        related_transfer=transfer,
                        reference_type='transfer',
                        reference_id=transfer.id,
                        created_by=request.user
                    )
                
                # إنشاء القيد المحاسبي
                try:
                    from journal.services import JournalService
                    JournalService.create_cashbox_transfer_entry(transfer, request.user)
                except Exception as e:
                    # تسجيل تحذير في حالة فشل إنشاء القيد
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"فشل في إنشاء القيد المحاسبي للتحويل {transfer.transfer_number}: {str(e)}")
                
                messages.success(request, _('Transfer created successfully'))
                
                # تسجيل النشاط في سجل التدقيق
                from core.models import AuditLog
                AuditLog.objects.create(
                    user=request.user,
                    action_type='create',
                    content_type='CashboxTransfer',
                    object_id=transfer.id,
                    description=f'إنشاء تحويل {transfer.transfer_number} من {transfer.get_from_display_name()} إلى {transfer.get_to_display_name()} - المبلغ: {transfer.amount}'
                )
                
                # تحديث التسلسل بعد نجاح التحويل
                if not transfer_number:  # فقط إذا تم توليد الرقم تلقائياً
                    try:
                        sequence = DocumentSequence.objects.get(document_type='cashbox_transfer')
                        # استخراج الرقم من نهاية الرقم المُستخدم
                        used_number = int(final_transfer_number[len(sequence.prefix):])
                        sequence.advance_to_at_least(used_number)
                    except (DocumentSequence.DoesNotExist, ValueError, IndexError):
                        pass  # تجاهل الأخطاء في تحديث التسلسل
                
                return redirect('cashboxes:transfer_detail', transfer_id=transfer.id)
        
        except Exception as e:
            messages.error(request, _('An error occurred while creating the transfer'))
    
    return redirect('cashboxes:transfer_list')


@login_required
def transfer_list(request):
    """قائمة التحويلات"""
    transfers = CashboxTransfer.objects.all().select_related(
        'from_cashbox', 'to_cashbox', 'from_bank', 'to_bank', 'created_by'
    ).order_by('-date', '-created_at')
    
    # فلترة حسب النوع
    transfer_type = request.GET.get('type')
    if transfer_type:
        transfers = transfers.filter(transfer_type=transfer_type)
    
    # فلترة حسب التاريخ
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        transfers = transfers.filter(date__gte=date_from)
    if date_to:
        transfers = transfers.filter(date__lte=date_to)
    
    # التقسيم لصفحات
    paginator = Paginator(transfers, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # البيانات المساعدة
    cashboxes = Cashbox.objects.filter(is_active=True).order_by('name')
    banks = BankAccount.objects.filter(is_active=True).order_by('name')
    
    # الحصول على رقم التحويل التالي
    from core.models import DocumentSequence
    next_transfer_number = None
    try:
        sequence = DocumentSequence.objects.get(document_type='cashbox_transfer')
        next_transfer_number = sequence.get_next_number()
    except DocumentSequence.DoesNotExist:
        # في حالة عدم وجود تسلسل، استخدم الطريقة القديمة
        from django.utils import timezone
        prefix = 'CT'
        date_str = timezone.now().strftime('%Y%m%d')
        
        # البحث عن آخر رقم في نفس اليوم
        last_transfer = CashboxTransfer.objects.filter(
            transfer_number__startswith=f'{prefix}{date_str}'
        ).order_by('-transfer_number').first()
        
        if last_transfer:
            last_number = int(last_transfer.transfer_number[-4:])
            new_number = last_number + 1
        else:
            new_number = 1
        
        next_transfer_number = f'{prefix}{date_str}{new_number:04d}'
    
    context = {
        'transfers': page_obj,
        'cashboxes': cashboxes,
        'banks': banks,
        'next_transfer_number': next_transfer_number,
    # Use English msgid to avoid Arabic leaking in EN UI; AR translation handled in locale files
    'page_title': _('Cashbox Transfers'),
    }
    return render(request, 'cashboxes/transfer_list.html', context)


@login_required
def transfer_detail(request, transfer_id):
    """تفاصيل التحويل"""
    transfer = get_object_or_404(CashboxTransfer, id=transfer_id)
    
    # الحصول على الحركات المرتبطة
    related_transactions = CashboxTransaction.objects.filter(
        related_transfer=transfer
    ).select_related('cashbox')
    
    context = {
        'transfer': transfer,
        'related_transactions': related_transactions,
        'page_title': f'{_("تفاصيل التحويل")} - {transfer.transfer_number}',
    }
    return render(request, 'cashboxes/transfer_detail.html', context)


@login_required
@require_http_methods(["GET"])
def get_cashbox_balance(request, cashbox_id):
    """الحصول على رصيد الصندوق (Ajax)"""
    try:
        cashbox = get_object_or_404(Cashbox, id=cashbox_id)
        return JsonResponse({
            'balance': float(cashbox.balance),
            'currency': cashbox.currency,
            'currency_symbol': cashbox.get_currency_symbol()
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_http_methods(["GET"])
def get_bank_balance(request, bank_id):
    """الحصول على رصيد البنك (Ajax)"""
    try:
        bank = get_object_or_404(BankAccount, id=bank_id)
        return JsonResponse({
            'balance': float(bank.balance),
            'currency': bank.currency if hasattr(bank, 'currency') else 'SAR'
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@method_decorator(login_required, name='dispatch')
class CashboxTransactionDeleteView(View):
    """حذف معاملة صندوق مع تحديث جميع الحسابات المرتبطة"""
    
    def post(self, request, transaction_id):
        cashbox_transaction = get_object_or_404(CashboxTransaction, id=transaction_id)
        cashbox = cashbox_transaction.cashbox
        
        try:
            with transaction.atomic():
                # إذا كانت المعاملة مرتبطة بتحويل، نحتاج لتحديث جميع الحسابات المرتبطة
                related_transfer = cashbox_transaction.related_transfer
                if related_transfer:
                    # جمع جميع الحسابات التي تحتاج تحديث
                    accounts_to_sync = []
                    cashboxes_to_sync = []
                    
                    # حسب نوع التحويل
                    if related_transfer.transfer_type == 'cashbox_to_cashbox':
                        if related_transfer.from_cashbox:
                            cashboxes_to_sync.append(related_transfer.from_cashbox)
                        if related_transfer.to_cashbox:
                            cashboxes_to_sync.append(related_transfer.to_cashbox)
                    
                    elif related_transfer.transfer_type == 'cashbox_to_bank':
                        if related_transfer.from_cashbox:
                            cashboxes_to_sync.append(related_transfer.from_cashbox)
                        if related_transfer.to_bank:
                            accounts_to_sync.append(related_transfer.to_bank)
                    
                    elif related_transfer.transfer_type == 'bank_to_cashbox':
                        if related_transfer.from_bank:
                            accounts_to_sync.append(related_transfer.from_bank)
                        if related_transfer.to_cashbox:
                            cashboxes_to_sync.append(related_transfer.to_cashbox)
                    
                    # حذف المعاملة
                    cashbox_transaction.delete()
                    
                    # تحديث أرصدة البنوك
                    for account in accounts_to_sync:
                        account.sync_balance()
                    
                    # تحديث أرصدة الصناديق (save() يؤدي لإعادة حساب الرصيد)
                    for cashbox_item in cashboxes_to_sync:
                        cashbox_item.sync_balance()
                
                else:
                    # معاملة عادية غير مرتبطة بتحويل
                    cashbox_transaction.delete()
                    
                    # إعادة حساب رصيد الصندوق
                    cashbox.sync_balance()
                
                messages.success(request, _('Transaction deleted successfully and all related balances have been updated.'))
                
        except Exception as e:
            messages.error(request, _('An error occurred while deleting the transaction: {}').format(str(e)))
        
        return redirect('cashboxes:cashbox_detail', cashbox_id=cashbox.id)


@method_decorator(login_required, name='dispatch')
class CashboxTransferDeleteView(View):
    """حذف تحويل صندوق مع تحديث جميع الحسابات المرتبطة"""
    
    def post(self, request, transfer_id):
        cashbox_transfer = get_object_or_404(CashboxTransfer, id=transfer_id)
        
        try:
            with transaction.atomic():
                # جمع جميع الحسابات والصناديق التي تحتاج تحديث
                accounts_to_sync = []
                cashboxes_to_sync = []
                
                # حسب نوع التحويل
                if cashbox_transfer.transfer_type == 'cashbox_to_cashbox':
                    if cashbox_transfer.from_cashbox:
                        cashboxes_to_sync.append(cashbox_transfer.from_cashbox)
                    if cashbox_transfer.to_cashbox:
                        cashboxes_to_sync.append(cashbox_transfer.to_cashbox)
                
                elif cashbox_transfer.transfer_type == 'cashbox_to_bank':
                    if cashbox_transfer.from_cashbox:
                        cashboxes_to_sync.append(cashbox_transfer.from_cashbox)
                    if cashbox_transfer.to_bank:
                        accounts_to_sync.append(cashbox_transfer.to_bank)
                
                elif cashbox_transfer.transfer_type == 'bank_to_cashbox':
                    if cashbox_transfer.from_bank:
                        accounts_to_sync.append(cashbox_transfer.from_bank)
                    if cashbox_transfer.to_cashbox:
                        cashboxes_to_sync.append(cashbox_transfer.to_cashbox)
                
                # حذف المعاملات المرتبطة بالتحويل
                CashboxTransaction.objects.filter(related_transfer=cashbox_transfer).delete()
                
                # حذف معاملات البنك المرتبطة (إذا وجدت)
                from banks.models import BankTransaction
                transfer_number = cashbox_transfer.transfer_number
                BankTransaction.objects.filter(
                    Q(reference_number__icontains=transfer_number) |
                    Q(reference_number__icontains=transfer_number.split('-')[0] if '-' in transfer_number else transfer_number)
                ).delete()
                
                # حذف التحويل نفسه
                cashbox_transfer.delete()
                
                # تحديث أرصدة البنوك
                for account in accounts_to_sync:
                    account.sync_balance()
                
                # تحديث أرصدة الصناديق
                for cashbox_item in cashboxes_to_sync:
                    cashbox_item.sync_balance()
                
                messages.success(request, _('Transfer deleted successfully and all related balances have been updated.'))
                
        except Exception as e:
            messages.error(request, _('An error occurred while deleting the transfer: {}').format(str(e)))
        
        return redirect('cashboxes:cashbox_list')


@method_decorator(login_required, name='dispatch')
class ClearCashboxTransactionsView(View):
    """حذف جميع معاملات الصندوق مع تحديث الأرصدة"""
    
    def post(self, request, cashbox_id):
        cashbox = get_object_or_404(Cashbox, id=cashbox_id)
        
        # التحقق من الصلاحيات
        if not (request.user.is_superuser or request.user.is_staff):
            messages.error(request, _('You do not have permission to clear cashbox transactions'))
            return redirect('cashboxes:cashbox_detail', cashbox_id=cashbox_id)
        
        try:
            with transaction.atomic():
                # جمع جميع الحسابات والصناديق المرتبطة قبل الحذف
                accounts_to_sync = set()
                cashboxes_to_sync = set()
                
                # البحث عن التحويلات المرتبطة
                transactions = CashboxTransaction.objects.filter(cashbox=cashbox)
                for trans in transactions:
                    if trans.related_transfer:
                        transfer = trans.related_transfer
                        
                        if transfer.transfer_type == 'cashbox_to_cashbox':
                            if transfer.from_cashbox and transfer.from_cashbox != cashbox:
                                cashboxes_to_sync.add(transfer.from_cashbox)
                            if transfer.to_cashbox and transfer.to_cashbox != cashbox:
                                cashboxes_to_sync.add(transfer.to_cashbox)
                        
                        elif transfer.transfer_type == 'cashbox_to_bank':
                            if transfer.to_bank:
                                accounts_to_sync.add(transfer.to_bank)
                        
                        elif transfer.transfer_type == 'bank_to_cashbox':
                            if transfer.from_bank:
                                accounts_to_sync.add(transfer.from_bank)
                
                # حذف جميع المعاملات
                transactions.delete()
                
                # إعادة تعيين رصيد الصندوق إلى صفر
                cashbox.balance = Decimal('0')
                cashbox.save()
                
                # تحديث أرصدة البنوك المرتبطة
                for account in accounts_to_sync:
                    account.sync_balance()
                
                # تحديث أرصدة الصناديق المرتبطة
                for cashbox_item in cashboxes_to_sync:
                    cashbox_item.sync_balance()
                
                messages.success(request, _('All transactions for cashbox "{}" were cleared successfully and all related balances were updated.').format(cashbox.name))
                
        except Exception as e:
            messages.error(request, _('An error occurred while clearing cashbox transactions: {}').format(str(e)))
        
        return redirect('cashboxes:cashbox_detail', cashbox_id=cashbox_id)


@login_required
def cashbox_delete(request, cashbox_id):
    """حذف الصندوق - محسّن للتعامل مع الحماية"""
    # التحقق من الصلاحيات
    if not (request.user.is_superuser or request.user.is_staff):
        messages.error(request, _('You do not have permission to delete cashboxes'))
        return redirect('cashboxes:cashbox_list')
        
    cashbox = get_object_or_404(Cashbox, id=cashbox_id)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # إذا كان الرصيد صفر ولكن يوجد معاملات، احذف المعاملات الخاصة بالصندوق فقط
                if cashbox.balance == 0 and CashboxTransaction.objects.filter(cashbox=cashbox).exists():
                    # حذف المعاملات الخاصة بالصندوق المُراد حذفه فقط
                    # هذا لن يؤثر على أرصدة الصناديق الأخرى لأنها لم تتأثر
                    CashboxTransaction.objects.filter(cashbox=cashbox).delete()
                    
                    # ملاحظة: التحويلات ستبقى موجودة ولكن بمرجع NULL للصندوق المحذوف
                    # هذا بسبب استخدام on_delete=models.SET_NULL في النموذج
                    # والصناديق الأخرى ستحتفظ بأرصدتها الصحيحة
                
                elif cashbox.balance != 0:
                    messages.error(request, _('Cannot delete the cashbox because the balance is not zero'))
                    return redirect('cashboxes:cashbox_detail', cashbox_id=cashbox_id)
                
                # تسجيل العملية في سجل الأنشطة قبل الحذف
                AuditLog.objects.create(
                    user=request.user,
                    action_type='delete',
                    content_type='Cashbox',
                    object_id=cashbox_id,
                    description=_('Deleted cashbox: {}').format(cashbox.name),
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                
                # الآن احذف الصندوق - التحويلات ستصبح تلقائياً بمرجع NULL
                cashbox_name = cashbox.name
                cashbox.delete()
                messages.success(request, _('Cashbox "{}" was deleted successfully while preserving transfers and balances in other cashboxes').format(cashbox_name))
                return redirect('cashboxes:cashbox_list')
                
        except ProtectedError as e:
            messages.error(request, _('Cannot delete the cashbox due to protected related transactions'))
        except Exception as e:
            messages.error(request, _('An error occurred while deleting the cashbox: {}').format(str(e)))
    
    return redirect('cashboxes:cashbox_detail', cashbox_id=cashbox_id)
