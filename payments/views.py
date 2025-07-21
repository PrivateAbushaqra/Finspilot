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

from .models import PaymentVoucher  # , PaymentVoucherItem
from .forms import PaymentVoucherForm  # , PaymentVoucherItemFormSet
from cashboxes.models import Cashbox, CashboxTransaction
from banks.models import BankAccount
from settings.models import CompanySettings
from customers.models import CustomerSupplier
from settings.models import CompanySettings
from journal.services import JournalService


def create_payment_journal_entry(voucher, user):
    """إنشاء قيد محاسبي لسند الصرف"""
    try:
        # إنشاء القيد المحاسبي باستخدام JournalService
        JournalService.create_payment_voucher_entry(voucher, user)
    except Exception as e:
        print(f"خطأ في إنشاء القيد المحاسبي لسند الصرف: {e}")
        # لا نوقف العملية في حالة فشل إنشاء القيد المحاسبي
        pass


def get_currency_symbol():
    """الحصول على رمز العملة من إعدادات الشركة"""
    from settings.models import CompanySettings, Currency
    
    company_settings = CompanySettings.objects.first()
    if company_settings and company_settings.base_currency:
        currency = company_settings.base_currency
        if company_settings.show_currency_symbol and currency.symbol:
            return currency.symbol
        return currency.code
    
    # البحث عن العملة الأساسية في النظام
    currency = Currency.get_base_currency()
    if currency:
        return currency.symbol if currency.symbol else currency.code
    
    # إذا لم توجد عملة، عدم إرجاع أي عملة افتراضية
    return ""


@login_required
def payment_voucher_list(request):
    """قائمة سندات الصرف"""
    vouchers = PaymentVoucher.objects.filter(is_active=True).select_related(
        'supplier', 'cashbox', 'bank', 'created_by'
    )
    
    # التصفية
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
    
    # التصفية بالتاريخ
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        vouchers = vouchers.filter(date__gte=date_from)
    if date_to:
        vouchers = vouchers.filter(date__lte=date_to)
    
    # الترقيم
    paginator = Paginator(vouchers, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # الإحصائيات
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
    """إنشاء سند صرف جديد"""
    if request.method == 'POST':
        form = PaymentVoucherForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    voucher = form.save(commit=False)
                    voucher.created_by = request.user
                    voucher.save()
                    
                    # إنشاء حركة الصندوق أو البنك
                    create_payment_transaction(voucher)
                    
                    # إنشاء القيد المحاسبي
                    create_payment_journal_entry(voucher, request.user)
                    
                    messages.success(request, _('تم إنشاء سند الصرف بنجاح'))
                    return redirect('payments:voucher_detail', pk=voucher.pk)
            except Exception as e:
                messages.error(request, f'خطأ في إنشاء سند الصرف: {str(e)}')
    else:
        form = PaymentVoucherForm()
    
    currency_symbol = get_currency_symbol()
    
    context = {
        'form': form,
        'title': _('إنشاء سند صرف جديد'),
        'currency_symbol': currency_symbol,
    }
    return render(request, 'payments/voucher_form.html', context)


@login_required
def payment_voucher_detail(request, pk):
    """تفاصيل سند الصرف"""
    voucher = get_object_or_404(PaymentVoucher, pk=pk)
    
    currency_symbol = get_currency_symbol()
    
    context = {
        'voucher': voucher,
        'currency_symbol': currency_symbol,
    }
    return render(request, 'payments/voucher_detail.html', context)


@login_required
def payment_voucher_edit(request, pk):
    """تعديل سند الصرف"""
    voucher = get_object_or_404(PaymentVoucher, pk=pk)
    
    if voucher.is_reversed:
        messages.error(request, _('لا يمكن تعديل سند صرف معكوس'))
        return redirect('payments:voucher_detail', pk=voucher.pk)
    
    if request.method == 'POST':
        form = PaymentVoucherForm(request.POST, instance=voucher)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # حذف الحركة القديمة
                    reverse_payment_transaction(voucher)
                    
                    # حفظ التعديلات
                    voucher = form.save()
                    
                    # إنشاء حركة جديدة
                    create_payment_transaction(voucher)
                    
                    messages.success(request, _('تم تحديث سند الصرف بنجاح'))
                    return redirect('payments:voucher_detail', pk=voucher.pk)
            except Exception as e:
                messages.error(request, f'خطأ في تحديث سند الصرف: {str(e)}')
    else:
        form = PaymentVoucherForm(instance=voucher)
    
    currency_symbol = get_currency_symbol()
    
    context = {
        'form': form,
        'voucher': voucher,
        'title': _('تعديل سند الصرف'),
        'currency_symbol': currency_symbol,
    }
    return render(request, 'payments/voucher_form.html', context)


@login_required
def payment_voucher_reverse(request, pk):
    """عكس سند الصرف"""
    voucher = get_object_or_404(PaymentVoucher, pk=pk)
    
    if not voucher.can_be_reversed:
        messages.error(request, _('لا يمكن عكس هذا السند'))
        return redirect('payments:voucher_detail', pk=voucher.pk)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        if not reason:
            messages.error(request, _('سبب العكس مطلوب'))
            return redirect('payments:voucher_detail', pk=voucher.pk)
        
        try:
            with transaction.atomic():
                # عكس الحركة المالية
                reverse_payment_transaction(voucher)
                
                # تحديث حالة السند
                voucher.is_reversed = True
                voucher.reversed_by = request.user
                voucher.reversed_at = django_timezone.now()
                voucher.reversal_reason = reason
                voucher.save()
                
                messages.success(request, _('تم عكس سند الصرف بنجاح'))
        except Exception as e:
            messages.error(request, f'خطأ في عكس سند الصرف: {str(e)}')
    
    return redirect('payments:voucher_detail', pk=voucher.pk)


def create_payment_transaction(voucher):
    """إنشاء حركة مالية لسند الصرف"""
    if voucher.payment_type == 'cash' and voucher.cashbox:
        # حركة صندوق (صرف)
        CashboxTransaction.objects.create(
            cashbox=voucher.cashbox,
            transaction_type='withdrawal',
            amount=voucher.amount,
            description=f'سند صرف {voucher.voucher_number} - {voucher.beneficiary_display}',
            date=voucher.date,
            created_by=voucher.created_by
        )
    
    elif voucher.payment_type == 'bank_transfer' and voucher.bank:
        # حركة بنك (صرف) - نستخدم الاستيراد المباشر لتجنب المشاكل الدائرية
        from banks.models import BankTransaction
        BankTransaction.objects.create(
            bank=voucher.bank,
            transaction_type='withdrawal',
            amount=voucher.amount,
            description=f'سند صرف {voucher.voucher_number} - {voucher.beneficiary_display}',
            reference_number=voucher.bank_reference or voucher.voucher_number,
            date=voucher.date,
            created_by=voucher.created_by
        )


def reverse_payment_transaction(voucher):
    """عكس الحركة المالية لسند الصرف"""
    if voucher.payment_type == 'cash' and voucher.cashbox:
        # البحث عن حركة الصندوق وعكسها
        # نبحث عن الحركة باستخدام الوصف لأن CashboxTransaction لا يحتوي على reference_number
        transactions = CashboxTransaction.objects.filter(
            cashbox=voucher.cashbox,
            description__contains=voucher.voucher_number,
            transaction_type='withdrawal'
        )
        for transaction in transactions:
            CashboxTransaction.objects.create(
                cashbox=transaction.cashbox,
                transaction_type='deposit',
                amount=transaction.amount,
                description=f'عكس {transaction.description}',
                date=django_timezone.now().date(),
                created_by=voucher.reversed_by or voucher.created_by
            )
    
    elif voucher.payment_type == 'bank_transfer' and voucher.bank:
        # البحث عن حركة البنك وعكسها - نستخدم الاستيراد المباشر
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
                description=f'عكس {transaction.description}',
                reference_number=f'REV-{transaction.reference_number}',
                date=django_timezone.now().date(),
                created_by=voucher.reversed_by or voucher.created_by
            )


@login_required
def get_supplier_data(request):
    """الحصول على بيانات المورد عبر AJAX"""
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
    
    return JsonResponse({'error': 'المورد غير موجود'}, status=404)


@login_required
def payment_voucher_delete(request, pk):
    """حذف سند الصرف - محدود للـ Super Admin والـ Admin فقط"""
    # التحقق من الصلاحيات
    if not (request.user.is_superuser or request.user.is_staff):
        messages.error(request, _('ليس لديك صلاحية لحذف سندات الصرف'))
        return redirect('payments:voucher_list')
    
    voucher = get_object_or_404(PaymentVoucher, pk=pk)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # عكس الحركة المالية إذا لم تكن معكوسة بالفعل
                if not voucher.is_reversed:
                    reverse_payment_transaction(voucher)
                
                # تعطيل السند بدلاً من حذفه فعلياً
                voucher.is_active = False
                voucher.save()
                
                messages.success(request, _('تم حذف سند الصرف بنجاح'))
                return redirect('payments:voucher_list')
        except Exception as e:
            messages.error(request, f'خطأ في حذف سند الصرف: {str(e)}')
    
    return redirect('payments:voucher_detail', pk=voucher.pk)
