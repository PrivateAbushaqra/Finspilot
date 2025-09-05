from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone
from django.core.paginator import Paginator
from decimal import Decimal

from .models import PaymentReceipt, CheckCollection, ReceiptReversal
from customers.models import CustomerSupplier
from cashboxes.models import Cashbox, CashboxTransaction
from accounts.models import AccountTransaction
from journal.services import JournalService


def create_receipt_journal_entry(receipt, user):
    """Create journal entry for receipt voucher"""
    try:
        # Create journal entry using JournalService
        JournalService.create_receipt_voucher_entry(receipt, user)
    except Exception as e:
        print(f"Error creating journal entry for receipt voucher: {e}")
        # Don't stop the operation if journal entry creation fails
        pass


@login_required
def receipt_list(request):
    """Receipt vouchers list"""
    receipts = PaymentReceipt.objects.all().select_related(
        'customer', 'cashbox', 'created_by'
    ).order_by('-date', '-receipt_number')
    
    # Filter by customer
    customer_id = request.GET.get('customer')
    if customer_id:
        receipts = receipts.filter(customer_id=customer_id)
    
    # Filter by payment type
    payment_type = request.GET.get('payment_type')
    if payment_type:
        receipts = receipts.filter(payment_type=payment_type)
    
    # Filter by date
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        receipts = receipts.filter(date__gte=date_from)
    if date_to:
        receipts = receipts.filter(date__lte=date_to)
    
    # Filter by status
    status = request.GET.get('status')
    if status == 'active':
        receipts = receipts.filter(is_active=True, is_reversed=False)
    elif status == 'reversed':
        receipts = receipts.filter(is_reversed=True)
    
    # Pagination
    paginator = Paginator(receipts, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Helper data
    customers = CustomerSupplier.objects.filter(
        type__in=['customer', 'both'], 
        is_active=True
    ).order_by('name')
    
    context = {
        'receipts': page_obj,
        'customers': customers,
        'page_title': _('Receipt Vouchers'),
    }
    return render(request, 'receipts/receipt_list.html', context)


@login_required
def receipt_add(request):
    """Add new receipt voucher"""
    if request.method == 'POST':
        receipt_number = request.POST.get('receipt_number', '').strip()
        customer_id = request.POST.get('customer')
        payment_type = request.POST.get('payment_type')
        amount = request.POST.get('amount')
        date = request.POST.get('date')
        description = request.POST.get('description', '')
        notes = request.POST.get('notes', '')
        
        # Cash box data for cash payment
        cashbox_id = request.POST.get('cashbox')
        
        # Check data
        check_number = request.POST.get('check_number', '')
        check_date = request.POST.get('check_date')
        check_due_date = request.POST.get('check_due_date')
        bank_name = request.POST.get('bank_name', '')
        check_cashbox_id = request.POST.get('check_cashbox')
        
        # Validate basic data
        if not all([receipt_number, customer_id, payment_type, amount, date]):
            messages.error(request, _('جميع الحقول مطلوبة'))
            return redirect('receipts:receipt_add')
        
        # Check for duplicate receipt number
        if PaymentReceipt.objects.filter(receipt_number=receipt_number).exists():
            messages.error(request, _('رقم السند موجود مسبقاً، يرجى اختيار رقم آخر'))
            return redirect('receipts:receipt_add')
        
        try:
            amount = Decimal(amount)
            if amount <= 0:
                messages.error(request, _('المبلغ يجب أن يكون أكبر من صفر'))
                return redirect('receipts:receipt_add')
            
            customer = get_object_or_404(
                CustomerSupplier, 
                id=customer_id, 
                type__in=['customer', 'both']
            )
            
            with transaction.atomic():
                # Create receipt voucher
                receipt = PaymentReceipt.objects.create(
                    receipt_number=receipt_number,
                    customer=customer,
                    payment_type=payment_type,
                    amount=amount,
                    date=date,
                    description=description,
                    notes=notes,
                    cashbox_id=cashbox_id if payment_type == 'cash' else None,
                    check_number=check_number if payment_type == 'check' else '',
                    check_date=check_date if payment_type == 'check' else None,
                    check_due_date=check_due_date if payment_type == 'check' else None,
                    bank_name=bank_name if payment_type == 'check' else '',
                    check_cashbox_id=check_cashbox_id if payment_type == 'check' else None,
                    created_by=request.user
                )
                
                # إضافة الحركة إلى حساب العميل
                AccountTransaction.create_transaction(
                    customer_supplier=customer,
                    transaction_type='receipt',  # تصحيح نوع المعاملة
                    direction='credit',  # دائن - يقلل من رصيد العميل
                    amount=amount,
                    reference_type='receipt',
                    reference_id=receipt.id,
                    description=f'{_("Receipt voucher")} {receipt.receipt_number} - {description}',
                    notes=f'{_("Payment type")}: {payment_type}',
                    user=request.user,
                    date=date
                )
                
                # For cash payment: add amount to cash box
                if payment_type == 'cash' and cashbox_id:
                    cashbox = get_object_or_404(Cashbox, id=cashbox_id)
                    cashbox.balance += amount
                    cashbox.save()
                    
                    # Add cash box transaction
                    CashboxTransaction.objects.create(
                        cashbox=cashbox,
                        transaction_type='deposit',
                        date=date,
                        amount=amount,
                        description=f'{_("Receipt voucher")} {receipt.receipt_number} {_("from")} {customer.name}',
                        created_by=request.user
                    )
                
                # For checks: update check status
                if payment_type == 'check':
                    receipt.check_status = 'pending'
                    receipt.save()
                
                # إنشاء القيد المحاسبي
                create_receipt_journal_entry(receipt, request.user)
                
                messages.success(request, _('Receipt voucher {} created successfully').format(receipt.receipt_number))
                return redirect('receipts:receipt_detail', receipt_id=receipt.id)
        
        except Exception as e:
            messages.error(request, _('Error occurred while creating receipt voucher: {}').format(str(e)))
    
    # البيانات المساعدة للنموذج
    customers = CustomerSupplier.objects.filter(
        type__in=['customer', 'both'], 
        is_active=True
    ).order_by('name')
    cashboxes = Cashbox.objects.filter(is_active=True).order_by('name')
    
    context = {
        'customers': customers,
        'cashboxes': cashboxes,
        'page_title': _('Add Receipt Voucher'),
        'today': timezone.now().date(),
    }
    return render(request, 'receipts/receipt_add.html', context)


@login_required
def receipt_detail(request, receipt_id):
    """Receipt voucher details"""
    receipt = get_object_or_404(PaymentReceipt, id=receipt_id)
    
    # Get related account movements
    account_movements = AccountTransaction.objects.filter(
        reference_type='receipt',
        reference_id=receipt.id
    ).order_by('-created_at')
    
    # Get check collections (if any)
    collections = CheckCollection.objects.filter(receipt=receipt).order_by('-collection_date')
    
    context = {
        'receipt': receipt,
        'account_movements': account_movements,
        'collections': collections,
        'page_title': f'{_("Receipt Voucher Details")} - {receipt.receipt_number}',
    }
    return render(request, 'receipts/receipt_detail.html', context)


@login_required
def receipt_edit(request, receipt_id):
    """Edit receipt voucher"""
    receipt = get_object_or_404(PaymentReceipt, id=receipt_id)
    
    # Check edit permission
    if receipt.is_reversed:
        messages.error(request, _('لا يمكن تعديل سند معكوس'))
        return redirect('receipts:receipt_detail', receipt_id=receipt_id)
    
    if request.method == 'POST':
        description = request.POST.get('description', '')
        notes = request.POST.get('notes', '')
        
        try:
            receipt.description = description
            receipt.notes = notes
            receipt.save()
            
            messages.success(request, _('Receipt voucher updated successfully'))
            return redirect('receipts:receipt_detail', receipt_id=receipt_id)
            
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء التحديث: {str(e)}')
    
    return redirect('receipts:receipt_detail', receipt_id=receipt_id)


@login_required
def receipt_reverse(request, receipt_id):
    """Reverse receipt voucher"""
    receipt = get_object_or_404(PaymentReceipt, id=receipt_id)
    
    # Check reversal permission
    if not receipt.can_be_reversed:
        messages.error(request, _('لا يمكن عكس هذا السند'))
        return redirect('receipts:receipt_detail', receipt_id=receipt_id)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        notes = request.POST.get('notes', '')
        
        if not reason:
            messages.error(request, _('سبب العكس مطلوب'))
            return redirect('receipts:receipt_detail', receipt_id=receipt_id)
        
        try:
            with transaction.atomic():
                # تحديث السند كمعكوس
                receipt.is_reversed = True
                receipt.reversed_by = request.user
                receipt.reversed_at = timezone.now()
                receipt.reversal_reason = reason
                receipt.save()
                
                # إنشاء سجل العكس
                reversal = ReceiptReversal.objects.create(
                    original_receipt=receipt,
                    reversal_date=timezone.now().date(),
                    reason=reason,
                    notes=notes,
                    created_by=request.user
                )
                
                # عكس حركة حساب العميل
                AccountTransaction.create_transaction(
                    customer_supplier=receipt.customer,
                    transaction_type='receipt',
                    direction='debit',  # مدين - يزيد من رصيد العميل (عكس الدفع)
                    amount=receipt.amount,
                    reference_type='receipt_reversal',
                    reference_id=reversal.id,
                    description=f'{_("Reversal of receipt voucher")} {receipt.receipt_number} - {reason}',
                    notes=f'{_("Reversal")}: {notes}',
                    user=request.user,
                    date=timezone.now().date()
                )
                
                # For cash payment: subtract amount from cash box
                if receipt.payment_type == 'cash' and receipt.cashbox:
                    cashbox = receipt.cashbox
                    if cashbox.balance >= receipt.amount:
                        cashbox.balance -= receipt.amount
                        cashbox.save()
                        
                        # Add cash box transaction
                        CashboxTransaction.objects.create(
                            cashbox=cashbox,
                            transaction_type='withdrawal',
                            date=timezone.now().date(),
                            amount=-receipt.amount,
                            description=f'{_("Reversal of receipt voucher")} {receipt.receipt_number} - {reason}',
                            created_by=request.user
                        )
                    else:
                        messages.warning(request, _('Warning: Insufficient cash box balance, reversal applied to account only'))
                
                messages.success(request, f'{_("Receipt voucher")} {receipt.receipt_number} {_("has been reversed successfully")}')
                return redirect('receipts:receipt_detail', receipt_id=receipt_id)
                
        except Exception as e:
            messages.error(request, f'{_("Error occurred while reversing voucher")}: {str(e)}')
    
    return redirect('receipts:receipt_detail', receipt_id=receipt_id)


@login_required
def check_list(request):
    """قائمة الشيكات"""
    checks = PaymentReceipt.objects.filter(
        payment_type='check'
    ).select_related('customer', 'created_by').order_by('-check_due_date')
    
    # فلترة حسب الحالة
    status = request.GET.get('status')
    if status:
        checks = checks.filter(check_status=status)
    
    # فلترة حسب تاريخ الاستحقاق
    due_date_from = request.GET.get('due_date_from')
    due_date_to = request.GET.get('due_date_to')
    if due_date_from:
        checks = checks.filter(check_due_date__gte=due_date_from)
    if due_date_to:
        checks = checks.filter(check_due_date__lte=due_date_to)
    
    # التقسيم لصفحات
    paginator = Paginator(checks, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'checks': page_obj,
        'page_title': _('الشيكات'),
    }
    return render(request, 'receipts/check_list.html', context)


@login_required
def check_collect(request, receipt_id):
    """تحصيل الشيك"""
    receipt = get_object_or_404(PaymentReceipt, id=receipt_id, payment_type='check')
    
    if request.method == 'POST':
        collection_date = request.POST.get('collection_date')
        status = request.POST.get('status')  # collected أو bounced
        cashbox_id = request.POST.get('cashbox')
        notes = request.POST.get('notes', '')
        
        if not all([collection_date, status]):
            messages.error(request, _('جميع الحقول مطلوبة'))
            return redirect('receipts:receipt_detail', receipt_id=receipt_id)
        
        try:
            with transaction.atomic():
                # إنشاء سجل التحصيل
                collection = CheckCollection.objects.create(
                    receipt=receipt,
                    collection_date=collection_date,
                    status=status,
                    cashbox_id=cashbox_id if status == 'collected' else None,
                    notes=notes,
                    created_by=request.user
                )
                
                # تحديث حالة الشيك
                receipt.check_status = status
                receipt.save()
                
                # إذا تم التحصيل بنجاح
                if status == 'collected' and cashbox_id:
                    cashbox = get_object_or_404(Cashbox, id=cashbox_id)
                    cashbox.balance += receipt.amount
                    cashbox.save()
                    
                    # Add cash box transaction
                    CashboxTransaction.objects.create(
                        cashbox=cashbox,
                        transaction_type='deposit',
                        date=collection_date,
                        amount=receipt.amount,
                        description=f'{_("Check collection")} {receipt.check_number} - {_("voucher")} {receipt.receipt_number}',
                        created_by=request.user
                    )
                
                # إذا ارتد الشيك
                elif status == 'bounced':
                    # عكس حركة حساب العميل
                    AccountTransaction.create_transaction(
                        customer_supplier=receipt.customer,
                        transaction_type='receipt',
                        direction='debit',  # مدين - يزيد من رصيد العميل (عكس الدفع)
                        amount=receipt.amount,
                        reference_type='check_bounced',
                        reference_id=receipt.id,
                        description=f'ارتداد شيك {receipt.check_number} - سند {receipt.receipt_number}',
                        notes=f'ارتداد شيك رقم: {receipt.check_number}',
                        user=request.user,
                        date=collection_date
                    )
                
                status_text = 'تم التحصيل' if status == 'collected' else 'ارتد'
                messages.success(request, f'تم تسجيل {status_text} للشيك {receipt.check_number}')
                return redirect('receipts:receipt_detail', receipt_id=receipt_id)
                
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء التحصيل: {str(e)}')
    
    # البيانات المساعدة
    cashboxes = Cashbox.objects.filter(is_active=True).order_by('name')
    
    context = {
        'receipt': receipt,
        'cashboxes': cashboxes,
        'page_title': f'{_("تحصيل الشيك")} - {receipt.check_number}',
        'today': timezone.now().date(),
    }
    return render(request, 'receipts/check_collect.html', context)


@login_required
def get_customer_balance(request, customer_id):
    """Get customer balance (Ajax)"""
    try:
        customer = get_object_or_404(
            CustomerSupplier, 
            id=customer_id, 
            type__in=['customer', 'both']
        )
        
        return JsonResponse({
            'balance': float(customer.balance),
            'customer_name': customer.name
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
