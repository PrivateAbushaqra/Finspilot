from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from django.utils import timezone as django_timezone
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.urls import reverse
import logging

logger = logging.getLogger(__name__)

from .models import PaymentVoucher  # , PaymentVoucherItem
from .forms import PaymentVoucherForm  # , PaymentVoucherItemFormSet
from cashboxes.models import Cashbox, CashboxTransaction
from banks.models import BankAccount
from settings.models import CompanySettings
from customers.models import CustomerSupplier
from journal.services import JournalService


def create_payment_journal_entry(voucher, user):
    """Create journal entry for payment voucher"""
    try:
        # Create journal entry using JournalService
        JournalService.create_payment_voucher_entry(voucher, user)
    except Exception as e:
        print(f"Error creating journal entry for payment voucher: {e}")
        # Don't stop the operation if journal entry creation fails
        pass


def create_payment_account_transaction(voucher, user):
    """إنشاء حركة حساب للمورد عند إنشاء سند دفع"""
    try:
        from accounts.models import AccountTransaction
        import uuid
        
        # إنشاء معاملة للموردين فقط
        if voucher.supplier and voucher.voucher_type == 'supplier':
            # توليد رقم الحركة
            transaction_number = f"PAY-{uuid.uuid4().hex[:8].upper()}"
            
            # حساب الرصيد السابق
            last_transaction = AccountTransaction.objects.filter(
                customer_supplier=voucher.supplier
            ).order_by('-created_at').first()
            
            previous_balance = last_transaction.balance_after if last_transaction else 0
            
            # إنشاء حركة مدينة للمورد (تقليل الذمم الدائنة)
            new_balance = previous_balance - voucher.amount
            
            AccountTransaction.objects.create(
                transaction_number=transaction_number,
                date=voucher.date,
                customer_supplier=voucher.supplier,
                transaction_type='payment',
                direction='debit',
                amount=voucher.amount,
                reference_type='payment',
                reference_id=voucher.id,
                description=f'سند دفع رقم {voucher.voucher_number}',
                balance_after=new_balance,
                created_by=user
            )
            
    except ImportError:
        # في حالة عدم وجود نموذج الحسابات
        pass
    except Exception as e:
        print(f"خطأ في إنشاء حركة الحساب: {e}")
        # لا نوقف العملية في حالة فشل تسجيل الحركة المالية
        pass


def get_currency_symbol():
    """Get currency symbol from company settings"""
    from settings.models import CompanySettings, Currency
    
    company_settings = CompanySettings.objects.first()
    if company_settings and company_settings.base_currency:
        currency = company_settings.base_currency
        if company_settings.show_currency_symbol and currency.symbol:
            return currency.symbol
        return currency.code
    
    # Search for base currency in system
    currency = Currency.get_base_currency()
    if currency:
        return currency.symbol if currency.symbol else currency.code
    
    # If no currency found, return empty string
    return ""


@login_required
def payment_voucher_list(request):
    """Payment vouchers list"""
    vouchers = PaymentVoucher.objects.filter(is_active=True).select_related(
        'supplier', 'cashbox', 'bank', 'created_by'
    )
    
    # Filtering
    search = request.GET.get('search')
    if search:
        vouchers = vouchers.filter(
            Q(voucher_number__icontains=search) |
            Q(supplier__name__icontains=search) |
            Q(beneficiary_name__icontains=search) |
            Q(description__icontains=search)
        )
    
    payment_type = request.GET.get('payment_type')
    if payment_type:
        vouchers = vouchers.filter(payment_type=payment_type)
    
    voucher_type = request.GET.get('voucher_type')
    if voucher_type:
        vouchers = vouchers.filter(voucher_type=voucher_type)
    
    # Date filtering
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        vouchers = vouchers.filter(date__gte=date_from)
    if date_to:
        vouchers = vouchers.filter(date__lte=date_to)
    
    # Pagination
    paginator = Paginator(vouchers, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistics
    total_amount = vouchers.aggregate(Sum('amount'))['amount__sum'] or 0
    voucher_count = vouchers.count()
    average_amount = total_amount / voucher_count if voucher_count > 0 else 0
    
    currency_symbol = get_currency_symbol()
    
    context = {
        'page_obj': page_obj,
        'total_amount': total_amount,
        'average_amount': average_amount,
        'currency_symbol': currency_symbol,
        'search': search,
        'payment_type': payment_type,
        'voucher_type': voucher_type,
        'date_from': date_from,
        'date_to': date_to,
    }
    return render(request, 'payments/voucher_list.html', context)


@login_required
def payment_voucher_create(request):
    """Create new payment voucher"""
    if not request.user.has_perm('payments.add_paymentvoucher'):
        from django.core.exceptions import PermissionDenied
        messages.error(request, _('ليس لديك صلاحية إضافة سند صرف'))
        raise PermissionDenied(_('ليس لديك صلاحية إضافة سند صرف'))
    if request.method == 'POST':
        form = PaymentVoucherForm(request.POST)
        if form.is_valid():
            try:
                # التحقق من الرصيد قبل إنشاء السند
                voucher = form.save(commit=False)
                
                # التحقق من رصيد الصندوق للدفع النقدي
                if voucher.payment_type == 'cash' and voucher.cashbox:
                    if voucher.cashbox.balance < voucher.amount:
                        messages.error(request, _('رصيد الصندوق غير كافي لإتمام هذا الدفع'))
                        return render(request, 'payments/voucher_form.html', {'form': form})
                
                # التحقق من رصيد البنك للتحويل البنكي
                elif voucher.payment_type == 'bank_transfer' and voucher.bank:
                    if voucher.bank.balance < voucher.amount:
                        messages.error(request, _('رصيد البنك غير كافي لإتمام هذا الدفع'))
                        return render(request, 'payments/voucher_form.html', {'form': form})
                
                # التحقق من رصيد البنك للشيكات (إذا كان مرتبط ببنك معين)
                elif voucher.payment_type == 'check' and voucher.bank:
                    if voucher.bank.balance < voucher.amount:
                        messages.error(request, _('رصيد البنك غير كافي لإصدار هذا الشيك'))
                        return render(request, 'payments/voucher_form.html', {'form': form})
                
                with transaction.atomic():
                    voucher.created_by = request.user
                    voucher.save()
                    
                    # Create cash box or bank transaction
                    create_payment_transaction(voucher)
                    
                    # Create account transaction for supplier
                    create_payment_account_transaction(voucher, request.user)
                    
                    # Create journal entry
                    create_payment_journal_entry(voucher, request.user)
                    
                    # تسجيل النشاط في سجل التدقيق
                    from core.models import AuditLog
                    payment_type_display = dict(PaymentVoucher.PAYMENT_TYPES).get(voucher.payment_type, voucher.payment_type)
                    beneficiary = voucher.supplier.name if voucher.supplier else voucher.beneficiary_name
                    AuditLog.objects.create(
                        user=request.user,
                        action_type='create',
                        content_type='PaymentVoucher',
                        object_id=voucher.id,
                        description=f'إنشاء سند صرف رقم {voucher.voucher_number} - المستفيد: {beneficiary} - المبلغ: {voucher.amount} - نوع الدفع: {payment_type_display}'
                    )
                    
                    messages.success(request, _('Payment voucher created successfully'))
                    return redirect('payments:voucher_detail', pk=voucher.pk)
            except Exception as e:
                logger.error(f"Error creating payment voucher {form.cleaned_data.get('voucher_number', 'unknown')}: {str(e)}", exc_info=True)
                messages.error(request, f'{_("Error creating payment voucher")}: {str(e)}')
    else:
        form = PaymentVoucherForm()
    
    currency_symbol = get_currency_symbol()
    
    context = {
        'form': form,
        'title': _('Create New Payment Voucher'),
        'currency_symbol': currency_symbol,
    }
    return render(request, 'payments/voucher_form.html', context)


@login_required
def payment_voucher_detail(request, pk):
    """عرض تفاصيل سند الصرف (يتطلب صلاحية عرض فقط)"""
    if not request.user.has_perm('payments.view_paymentvoucher'):
        from django.core.exceptions import PermissionDenied
        messages.error(request, _('ليس لديك صلاحية عرض تفاصيل سندات الصرف'))
        raise PermissionDenied(_('ليس لديك صلاحية عرض تفاصيل سندات الصرف'))
    voucher = get_object_or_404(PaymentVoucher, pk=pk)
    currency_symbol = get_currency_symbol()
    context = {
        'voucher': voucher,
        'currency_symbol': currency_symbol,
    }
    return render(request, 'payments/voucher_detail.html', context)


@login_required
def payment_voucher_edit(request, pk):
    """Edit payment voucher"""
    voucher = get_object_or_404(PaymentVoucher, pk=pk)
    
    if voucher.is_reversed:
        messages.error(request, _('Cannot edit a reversed payment voucher'))
        return redirect('payments:voucher_detail', pk=voucher.pk)
    
    if request.method == 'POST':
        form = PaymentVoucherForm(request.POST, instance=voucher)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Delete old transaction
                    reverse_payment_transaction(voucher)
                    
                    # Save changes
                    voucher = form.save()
                    
                    # Create new transaction
                    create_payment_transaction(voucher)
                    
                    messages.success(request, _('Payment voucher updated successfully'))
                    return redirect('payments:voucher_detail', pk=voucher.pk)
            except Exception as e:
                messages.error(request, f'Error updating payment voucher: {str(e)}')
    else:
        form = PaymentVoucherForm(instance=voucher)
    
    currency_symbol = get_currency_symbol()
    
    context = {
        'form': form,
        'voucher': voucher,
        'title': _('Edit Payment Voucher'),
        'currency_symbol': currency_symbol,
    }
    return render(request, 'payments/voucher_form.html', context)


@login_required
def payment_voucher_reverse(request, pk):
    """Reverse payment voucher"""
    voucher = get_object_or_404(PaymentVoucher, pk=pk)
    
    if not voucher.can_be_reversed:
        messages.error(request, _('This voucher cannot be reversed'))
        return redirect('payments:voucher_detail', pk=voucher.pk)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        if not reason:
            messages.error(request, _('Reversal reason is required'))
            return redirect('payments:voucher_detail', pk=voucher.pk)
        
        try:
            with transaction.atomic():
                # Reverse financial transaction
                reverse_payment_transaction(voucher)
                
                # Update voucher status
                voucher.is_reversed = True
                voucher.reversed_by = request.user
                voucher.reversed_at = django_timezone.now()
                voucher.reversal_reason = reason
                voucher.save()
                
                messages.success(request, _('Payment voucher reversed successfully'))
        except Exception as e:
            messages.error(request, f'Error reversing payment voucher: {str(e)}')
    
    return redirect('payments:voucher_detail', pk=voucher.pk)


def create_payment_transaction(voucher):
    """Create financial transaction for payment voucher"""
    if voucher.payment_type == 'cash' and voucher.cashbox:
        # Cashbox transaction (payment)
        # Note: رصيد الصندوق يتم تحديثه تلقائياً من خلال signals في cashboxes/signals.py
        cashbox_trans = CashboxTransaction.objects.create(
            cashbox=voucher.cashbox,
            transaction_type='withdrawal',
            amount=-voucher.amount,  # المبلغ سالب للسحب
            description=f'Payment voucher {voucher.voucher_number} - {voucher.beneficiary_display}',
            date=voucher.date,
            reference_type='payment',
            reference_id=voucher.id,
            created_by=voucher.created_by
        )
        print(f"✓ تم إنشاء حركة صندوق: {cashbox_trans.id}")
        # تم إزالة التحديث اليدوي - الآن يتم عبر signals
    
    elif voucher.payment_type == 'bank_transfer' and voucher.bank:
        # Bank transaction (payment) - using direct import to avoid circular problems
        from banks.models import BankTransaction
        BankTransaction.objects.create(
            bank=voucher.bank,
            transaction_type='withdrawal',
            amount=-voucher.amount,  # المبلغ سالب للسحب
            description=f'Payment voucher {voucher.voucher_number} - {voucher.beneficiary_display}',
            reference_number=voucher.bank_reference or voucher.voucher_number,
            date=voucher.date,
            created_by=voucher.created_by
        )

    elif voucher.payment_type == 'check':
        # Check transaction (payment) - using direct import to avoid circular problems
        from banks.models import BankTransaction
        BankTransaction.objects.create(
            bank=None,  # يمكن تحديد البنك لاحقاً أو تركه فارغ للشيكات
            transaction_type='check_issued',
            amount=voucher.amount,
            description=f'Payment voucher {voucher.voucher_number} - Check {voucher.check_number} - {voucher.beneficiary_display}',
            reference_number=voucher.check_number,
            date=voucher.date,
            created_by=voucher.created_by
        )


def reverse_payment_transaction(voucher):
    """Reverse financial transaction for payment voucher"""
    if voucher.payment_type == 'cash' and voucher.cashbox:
        # Find and reverse cash box transaction
        # Search for transaction using description since CashboxTransaction doesn't have reference_number
        # Note: رصيد الصندوق يتم تحديثه تلقائياً من خلال signals
        transactions = CashboxTransaction.objects.filter(
            cashbox=voucher.cashbox,
            description__contains=voucher.voucher_number,
            transaction_type='withdrawal'
        )
        for transaction in transactions:
            CashboxTransaction.objects.create(
                cashbox=transaction.cashbox,
                transaction_type='deposit',
                amount=abs(transaction.amount),  # المبلغ موجب للإيداع (نعيد المبلغ المسحوب)
                description=f'Reverse {transaction.description}',
                date=django_timezone.now().date(),
                created_by=voucher.reversed_by or voucher.created_by
            )
            # تم إزالة التحديث اليدوي - الآن يتم عبر signals
    
    elif voucher.payment_type == 'bank_transfer' and voucher.bank:
        # Find and reverse bank transaction - using direct import
        from banks.models import BankTransaction
        transactions = BankTransaction.objects.filter(
            bank=voucher.bank,
            reference_number__in=[voucher.bank_reference, voucher.voucher_number],
            transaction_type='withdrawal'
        )
        for transaction in transactions:
            BankTransaction.objects.create(
                bank=transaction.bank,
                transaction_type='deposit',
                amount=transaction.amount,
                description=f'Reverse {transaction.description}',
                reference_number=f'REV-{transaction.reference_number}',
                date=django_timezone.now().date(),
                created_by=voucher.reversed_by or voucher.created_by
            )


@login_required
def get_supplier_data(request):
    """Get supplier data via AJAX"""
    supplier_id = request.GET.get('supplier_id')
    if supplier_id:
        try:
            supplier = CustomerSupplier.objects.get(id=supplier_id, type__in=['supplier', 'both'])
            data = {
                'name': supplier.name,
                'phone': supplier.phone,
                'address': supplier.address,
            }
            return JsonResponse(data)
        except CustomerSupplier.DoesNotExist:
            pass
    
    return JsonResponse({'error': 'Supplier not found'}, status=404)


@login_required
def payment_voucher_delete(request, pk):
    """Delete payment voucher - limited to Super Admin and Admin only"""
    # Check permissions
    if not (request.user.is_superuser or request.user.is_staff):
        messages.error(request, _('You do not have permission to delete payment vouchers'))
        return redirect('payments:voucher_list')
    
    voucher = get_object_or_404(PaymentVoucher, pk=pk)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Reverse financial transaction if not already reversed
                if not voucher.is_reversed:
                    reverse_payment_transaction(voucher)
                
                # Deactivate voucher instead of actual deletion
                voucher.is_active = False
                voucher.save()
                
                messages.success(request, _('Payment voucher deleted successfully'))
                return redirect('payments:voucher_list')
        except Exception as e:
            messages.error(request, f'Error deleting payment voucher: {str(e)}')
    
    return redirect('payments:voucher_detail', pk=voucher.pk)
