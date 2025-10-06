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
from journal.models import JournalEntry


def process_cheque_errors_warnings():
    """
    معالجة الأخطاء والتحذيرات في الشيكات تلقائياً وفق IFRS 9
    """
    from datetime import datetime
    from django.utils import timezone

    # الحصول على جميع الشيكات
    cheques = PaymentReceipt.objects.filter(payment_type='check').select_related('customer')

    processed_errors = []
    processed_warnings = []

    for cheque in cheques:
        # معالجة الأخطاء: الشيكات المرتدة بدون قيد يومية
        if cheque.check_status == 'bounced':
            # فحص وجود قيد يومية
            journal_exists = JournalEntry.objects.filter(
                reference_type='check_bounced',
                reference_id=cheque.id
            ).exists()

            if not journal_exists:
                try:
                    # إنشاء قيد يومية تلقائي
                    collection_date = timezone.now().date()
                    JournalService.create_check_bounced_entry(cheque, collection_date)

                    # تحديث سبب الارتداد إذا لم يكن محدد
                    if not cheque.bounce_reason:
                        cheque.bounce_reason = 'تم اكتشاف الارتداد أثناء التدقيق - تم إنشاء القيد اليومية تلقائياً'
                        cheque.save()

                    processed_errors.append({
                        'cheque': cheque,
                        'action': 'تم إنشاء قيد يومية تلقائي للشيك المرتد',
                        'details': f'قيد من ذمم مدينة إلى شيكات تحت التحصيل بمبلغ {cheque.amount}'
                    })

                except Exception as e:
                    print(f"خطأ في إنشاء قيد يومية للشيك {cheque.check_number}: {e}")

        # معالجة التحذيرات: الشيكات المحصلة
        elif cheque.check_status == 'collected':
            collection = CheckCollection.objects.filter(
                receipt=cheque,
                status='collected'
            ).first()

            if collection:
                days_difference = (collection.collection_date - cheque.check_due_date).days

                if days_difference > 0:
                    # تحصيل متأخر
                    processed_warnings.append({
                        'cheque': cheque,
                        'type': 'تحصيل متأخر',
                        'days_late': days_difference,
                        'action': 'تم تسجيل التحذير - يرجى متابعة مخاطر التحصيل',
                        'ifrs_note': 'قد يؤثر على توقيت الإيرادات وفق IFRS 9'
                    })

                elif days_difference < 0:
                    # تحصيل مبكر - فحص الفاتورة
                    from sales.models import SalesInvoice
                    try:
                        invoice = SalesInvoice.objects.filter(
                            customer=cheque.customer,
                            total_amount=cheque.amount,
                            date__lte=cheque.check_date
                        ).first()

                        if invoice:
                            processed_warnings.append({
                                'cheque': cheque,
                                'type': 'تحصيل مبكر',
                                'days_early': abs(days_difference),
                                'action': 'تم ربط الشيك بالفاتورة ومراجعة الإيراد',
                                'ifrs_note': 'تمت مراجعة الإيراد - لا تأثير على IFRS 9',
                                'invoice': invoice.invoice_number
                            })
                        else:
                            processed_warnings.append({
                                'cheque': cheque,
                                'type': 'تحصيل مبكر',
                                'days_early': abs(days_difference),
                                'action': 'لم يتم العثور على فاتورة مرتبطة',
                                'ifrs_note': 'يرجى التأكد من عدم الاعتراف المبكر بالإيراد'
                            })

                    except Exception as e:
                        print(f"خطأ في فحص الفاتورة للشيك {cheque.check_number}: {e}")

    return {
        'processed_errors': processed_errors,
        'processed_warnings': processed_warnings
    }


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
        
        # Bank transfer data
        bank_account_id = request.POST.get('bank_account')
        bank_transfer_reference = request.POST.get('bank_transfer_reference', '')
        bank_transfer_date = request.POST.get('bank_transfer_date')
        bank_transfer_notes = request.POST.get('bank_transfer_notes', '')
        
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
                    bank_account_id=bank_account_id if payment_type == 'bank_transfer' else None,
                    bank_transfer_reference=bank_transfer_reference if payment_type == 'bank_transfer' else '',
                    bank_transfer_date=bank_transfer_date if payment_type == 'bank_transfer' else None,
                    bank_transfer_notes=bank_transfer_notes if payment_type == 'bank_transfer' else '',
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
                
                # For bank transfer: add amount to bank account
                if payment_type == 'bank_transfer' and bank_account_id:
                    from banks.models import BankAccount, BankTransaction
                    bank_account = get_object_or_404(BankAccount, id=bank_account_id)
                    
                    # Add bank transaction
                    BankTransaction.objects.create(
                        bank=bank_account,
                        transaction_type='deposit',
                        date=bank_transfer_date if bank_transfer_date else date,
                        amount=amount,
                        reference_number=bank_transfer_reference,
                        description=f'{_("Receipt voucher")} {receipt.receipt_number} {_("from")} {customer.name} - {bank_transfer_notes}',
                        created_by=request.user
                    )
                    
                    # تسجيل النشاط
                    try:
                        from core.signals import log_user_activity
                        log_user_activity(
                            request,
                            'create',
                            receipt,
                            _('تحويل بنكي لسند قبض رقم %(number)s - الحساب البنكي: %(account)s - المبلغ: %(amount)s') % {
                                'number': receipt.receipt_number,
                                'account': bank_account.name,
                                'amount': amount
                            }
                        )
                    except Exception:
                        pass
                
                # For checks: update check status and add to cashbox
                if payment_type == 'check':
                    receipt.check_status = 'pending'
                    receipt.save()
                    
                    # إضافة الشيك إلى الصندوق المحدد
                    if check_cashbox_id:
                        check_cashbox = get_object_or_404(Cashbox, id=check_cashbox_id)
                        check_cashbox.balance += amount
                        check_cashbox.save()
                        
                        # إضافة حركة صندوق للشيك
                        CashboxTransaction.objects.create(
                            cashbox=check_cashbox,
                            transaction_type='deposit',
                            date=date,
                            amount=amount,
                            description=f'{_("شيك قيد التحصيل")} - {_("سند قبض")} {receipt.receipt_number} {_("من")} {customer.name} - {_("رقم الشيك")}: {check_number}',
                            created_by=request.user
                        )
                        
                        # تسجيل النشاط
                        try:
                            from core.signals import log_user_activity
                            log_user_activity(
                                request,
                                'create',
                                receipt,
                                _('إيداع شيك في الصندوق - سند قبض رقم %(number)s - الصندوق: %(cashbox)s - المبلغ: %(amount)s - رقم الشيك: %(check)s') % {
                                    'number': receipt.receipt_number,
                                    'cashbox': check_cashbox.name,
                                    'amount': amount,
                                    'check': check_number
                                }
                            )
                        except Exception:
                            pass
                
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
    
    # Get bank accounts
    from banks.models import BankAccount
    bank_accounts = BankAccount.objects.filter(is_active=True).order_by('name')
    
    context = {
        'customers': customers,
        'cashboxes': cashboxes,
        'bank_accounts': bank_accounts,
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
    """تحصيل الشيك مع معالجة تلقائية للأخطاء والتحذيرات وفق IFRS 9"""
    receipt = get_object_or_404(PaymentReceipt, id=receipt_id, payment_type='check')
    
    if request.method == 'POST':
        collection_date = request.POST.get('collection_date')
        status = request.POST.get('status')  # collected أو bounced
        cashbox_id = request.POST.get('cashbox')
        notes = request.POST.get('notes', '')
        bounce_reason = request.POST.get('bounce_reason', '')  # سبب الارتداد
        
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
                if status == 'bounced' and bounce_reason:
                    receipt.bounce_reason = bounce_reason
                receipt.save()
                
                # حساب خسائر الائتمان المتوقعة (ECL) وفق IFRS 9
                try:
                    ecl_amount, ecl_method = receipt.calculate_expected_credit_loss()
                    receipt.expected_credit_loss = ecl_amount
                    receipt.ecl_calculation_date = timezone.now().date()
                    receipt.ecl_calculation_method = ecl_method
                    receipt.save()
                    
                    # إضافة ملاحظة ECL في سجل التحصيل
                    if ecl_amount > 0:
                        collection.notes += f'\n💰 تم حساب ECL بمبلغ {ecl_amount} ({ecl_method})'
                        collection.save()
                        
                        # تسجيل في السجل للمراجعة
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.info(f'تم حساب ECL للشيك {receipt.check_number}: {ecl_amount} ({ecl_method})')
                        
                except Exception as e:
                    print(f"خطأ في حساب ECL للشيك {receipt.check_number}: {e}")
                
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
                    
                    # معالجة التحذيرات تلقائياً - IFRS 9
                    from datetime import datetime
                    collection_date_obj = datetime.strptime(collection_date, '%Y-%m-%d').date()
                    
                    if collection_date_obj > receipt.check_due_date:
                        # تحصيل بعد تاريخ الاستحقاق - حساب عدد الأيام المتأخرة
                        days_late = (collection_date_obj - receipt.check_due_date).days
                        
                        # إضافة تنبيه في السجل
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.warning(f'تم تحصيل الشيك {receipt.check_number} بعد تاريخ الاستحقاق بـ {days_late} يوماً. '
                                     f'تاريخ الاستحقاق: {receipt.check_due_date}, تاريخ التحصيل: {collection_date}. '
                                     f'قد يؤثر هذا على توقيت الإيرادات وفق IFRS 9.')
                        
                        # إضافة ملاحظة في سجل التحصيل
                        collection.notes += f'\n⚠️ تحذير IFRS 9: تم التحصيل بعد تاريخ الاستحقاق بـ {days_late} يوماً ({receipt.check_due_date})'
                        collection.save()
                        
                        # توصية بمتابعة العميل
                        collection.notes += f'\n📋 توصية: متابعة العميل ومراقبة مخاطر التحصيل'
                        collection.save()
                    
                    elif collection_date_obj < receipt.check_due_date:
                        # تحصيل قبل تاريخ الاستحقاق - التحقق من حالة الفاتورة
                        days_early = (receipt.check_due_date - collection_date_obj).days
                        
                        # البحث عن الفاتورة المرتبطة بالشيك
                        from sales.models import SalesInvoice
                        try:
                            # افتراض أن الشيك مرتبط بفاتورة مبيعات
                            invoice = SalesInvoice.objects.filter(
                                customer=receipt.customer,
                                total_amount=receipt.amount,
                                date__lte=receipt.check_date
                            ).first()
                            
                            if invoice:
                                # التحقق من حالة الفاتورة (افتراض أن هناك حقل is_completed)
                                is_invoice_complete = getattr(invoice, 'is_completed', True)  # افتراض أنها مكتملة إذا لم يكن الحقل موجود
                                
                                if not is_invoice_complete:
                                    # الفاتورة غير مكتملة - تسجيل كدفعة مقدمة
                                    JournalService.create_check_early_collection_entry(
                                        receipt, collection_date_obj, is_invoice_complete=False, user=request.user
                                    )
                                    
                                    # إضافة تنبيه
                                    import logging
                                    logger = logging.getLogger(__name__)
                                    logger.info(f'تم تسجيل تحصيل الشيك {receipt.check_number} كدفعة مقدمة '
                                              f'بسبب عدم اكتمال الفاتورة المرتبطة.')
                                    
                                    collection.notes += f'\nℹ️ تم تسجيل المبلغ كدفعة مقدمة من العملاء (فاتورة غير مكتملة)'
                                    collection.save()
                                else:
                                    # الفاتورة مكتملة - اعتراف طبيعي
                                    JournalService.create_check_early_collection_entry(
                                        receipt, collection_date_obj, is_invoice_complete=True, user=request.user
                                    )
                                    
                                    # إضافة ملاحظة
                                    collection.notes += f'\n✅ تمت مراجعة الإيراد - لا تأثير على IFRS 9 (فاتورة مكتملة)'
                                    collection.save()
                            else:
                                # لم يتم العثور على فاتورة مرتبطة - اعتراف طبيعي
                                JournalService.create_check_early_collection_entry(
                                    receipt, collection_date_obj, is_invoice_complete=True, user=request.user
                                )
                                
                                collection.notes += f'\n⚠️ لم يتم العثور على فاتورة مرتبطة - يرجى التأكد من عدم الاعتراف المبكر بالإيراد'
                                collection.save()
                        except Exception as e:
                            # في حالة خطأ في البحث عن الفاتورة - اعتراف طبيعي
                            JournalService.create_check_early_collection_entry(
                                receipt, collection_date_obj, is_invoice_complete=True, user=request.user
                            )
                            print(f"خطأ في البحث عن الفاتورة المرتبطة: {e}")
                
                # إذا ارتد الشيك - معالجة الأخطاء تلقائياً IFRS 9 متوافق
                elif status == 'bounced':
                    # إنشاء القيد اليومية للشيك المرتد
                    from datetime import datetime
                    collection_date_obj = datetime.strptime(collection_date, '%Y-%m-%d').date()
                    
                    JournalService.create_check_bounced_entry(
                        receipt, collection_date_obj, user=request.user
                    )
                    
                    # إضافة تنبيه في السجل
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f'ارتداد شيك رقم {receipt.check_number} - تم إنشاء قيد يومية أوتوماتيكي '
                                 f'لنقل المبلغ من شيكات تحت التحصيل إلى ذمم مدينة وفق IFRS 9. '
                                 f'سبب الارتداد: {bounce_reason or "غير محدد"}')
                    
                    # إضافة ملاحظة في سجل التحصيل
                    collection.notes += f'\n❌ تم إنشاء قيد يومية للارتداد وفق IFRS 9'
                    if bounce_reason:
                        collection.notes += f'\n📝 سبب الارتداد: {bounce_reason}'
                    collection.save()
                
                status_text = 'تم التحصيل' if status == 'collected' else 'ارتد'
                messages.success(request, f'تم تسجيل {status_text} للشيك {receipt.check_number} مع المعالجة التلقائية')
                return redirect('receipts:receipt_detail', receipt_id=receipt_id)
                
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء التحصيل: {str(e)}')
    
    # البيانات المساعدة
    cashboxes = Cashbox.objects.filter(is_active=True).order_by('name')
    
    # أسباب الارتداد المحتملة
    bounce_reasons = [
        'رصيد غير كافٍ',
        'توقيع غير صحيح',
        'إيقاف من البنك',
        'تاريخ غير صحيح',
        'رقم حساب خاطئ',
        'شيك مزور',
        'أسباب أخرى'
    ]
    
    context = {
        'receipt': receipt,
        'cashboxes': cashboxes,
        'bounce_reasons': bounce_reasons,
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
