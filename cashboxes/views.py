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

from .models import Cashbox, CashboxTransfer, CashboxTransaction
from banks.models import BankAccount


@login_required
def cashbox_list(request):
    """قائمة الصناديق"""
    from settings.models import Currency
    
    cashboxes = Cashbox.objects.filter(is_active=True).order_by('name')
    
    # إحصائيات سريعة
    total_balance = sum(cashbox.balance for cashbox in cashboxes)
    
    # العملات المتاحة
    currencies = Currency.objects.filter(is_active=True).order_by('name')
    base_currency = Currency.get_base_currency()
    
    context = {
        'cashboxes': cashboxes,
        'total_balance': total_balance,
        'currencies': currencies,
        'base_currency': base_currency,
        'page_title': _('الصناديق النقدية'),
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
    
    # العملات المتاحة
    currencies = Currency.objects.filter(is_active=True).order_by('name')
    
    context = {
        'cashbox': cashbox,
        'transactions': page_obj,
        'currencies': currencies,
        'page_title': f'{_("تفاصيل الصندوق")} - {cashbox.name}',
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
            messages.error(request, _('اسم الصندوق مطلوب'))
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
                        description=_('الرصيد الافتتاحي'),
                        created_by=request.user
                    )
                
                messages.success(request, _('تم إنشاء الصندوق بنجاح'))
                return redirect('cashboxes:cashbox_detail', cashbox_id=cashbox.id)
        except Exception as e:
            messages.error(request, _('حدث خطأ أثناء إنشاء الصندوق'))
    
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
            messages.error(request, _('اسم الصندوق مطلوب'))
            return redirect('cashboxes:cashbox_detail', cashbox_id=cashbox_id)
        
        try:
            cashbox.name = name
            cashbox.description = description
            cashbox.currency = currency
            cashbox.location = location
            cashbox.responsible_user_id = responsible_user_id if responsible_user_id else None
            cashbox.save()
            
            messages.success(request, _('تم تحديث الصندوق بنجاح'))
            return redirect('cashboxes:cashbox_detail', cashbox_id=cashbox_id)
        except Exception as e:
            messages.error(request, _('حدث خطأ أثناء تحديث الصندوق'))
    
    return redirect('cashboxes:cashbox_detail', cashbox_id=cashbox_id)


@login_required
def transfer_create(request):
    """إنشاء تحويل"""
    # التحقق من وجود تسلسل المستندات
    from core.models import DocumentSequence
    try:
        sequence = DocumentSequence.objects.get(document_type='cashbox_transfer')
    except DocumentSequence.DoesNotExist:
        messages.warning(request, _('تحذير: لم يتم إعداد تسلسل أرقام التحويلات بين الصناديق! يرجى إضافة تسلسل "التحويل بين الصناديق" من صفحة الإعدادات قبل إنشاء أي تحويل.'))
    
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
            messages.error(request, _('جميع الحقول مطلوبة'))
            return redirect('cashboxes:transfer_list')
        
        # التحقق من معلومات الإيداع للتحويل من صندوق إلى بنك
        if transfer_type == 'cashbox_to_bank':
            if not deposit_document_number:
                messages.error(request, _('رقم مستند الإيداع مطلوب للتحويل إلى البنك'))
                return redirect('cashboxes:transfer_list')
            if not deposit_type:
                messages.error(request, _('نوع الإيداع مطلوب'))
                return redirect('cashboxes:transfer_list')
            if deposit_type == 'check':
                if not check_number:
                    messages.error(request, _('رقم الشيك مطلوب عند اختيار نوع الإيداع "شيك"'))
                    return redirect('cashboxes:transfer_list')
                if not check_date:
                    messages.error(request, _('تاريخ الشيك مطلوب'))
                    return redirect('cashboxes:transfer_list')
                if not check_bank_name:
                    messages.error(request, _('اسم بنك الشيك مطلوب'))
                    return redirect('cashboxes:transfer_list')
        
        # التحقق من رقم التحويل إذا تم إدخاله
        if transfer_number:
            # التحقق من عدم تكرار الرقم
            if CashboxTransfer.objects.filter(transfer_number=transfer_number).exists():
                messages.error(request, _('رقم التحويل موجود مسبقاً! يرجى استخدام رقم آخر.'))
                return redirect('cashboxes:transfer_list')
        
        try:
            amount = Decimal(amount)
            fees = Decimal(fees or 0)
            exchange_rate = Decimal(exchange_rate or 1)
            
            if amount <= 0:
                messages.error(request, _('المبلغ يجب أن يكون أكبر من صفر'))
                return redirect('cashboxes:transfer_list')
            
            with transaction.atomic():
                # تحديد رقم التحويل
                if transfer_number:
                    # استخدام الرقم المُدخل
                    final_transfer_number = transfer_number
                else:
                    # توليد رقم جديد بناءً على آخر رقم مُستخدم فعلياً
                    try:
                        sequence = DocumentSequence.objects.get(document_type='cashbox_transfer')
                        final_transfer_number = sequence.get_next_number()
                        # تحديث التسلسل إذا لزم الأمر
                        sequence.save()
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
                        messages.error(request, _('الرصيد غير كافي في الصندوق المرسل'))
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
                        description=f'{description} - {_("تحويل إلى")} {to_cashbox.name}',
                        related_transfer=transfer,
                        created_by=request.user
                    )
                    
                    CashboxTransaction.objects.create(
                        cashbox=to_cashbox,
                        transaction_type='transfer_in',
                        date=date,
                        amount=amount,
                        description=f'{description} - {_("تحويل من")} {from_cashbox.name}',
                        related_transfer=transfer,
                        created_by=request.user
                    )
                
                elif transfer_type == 'cashbox_to_bank':
                    from_cashbox = get_object_or_404(Cashbox, id=from_cashbox_id)
                    to_bank = get_object_or_404(BankAccount, id=to_bank_id)
                    
                    # التحقق من الرصيد
                    if from_cashbox.balance < amount:
                        messages.error(request, _('الرصيد غير كافي في الصندوق'))
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
                        description=f'{description} - {_("تحويل إلى بنك")} {to_bank.name}',
                        related_transfer=transfer,
                        created_by=request.user
                    )
                
                elif transfer_type == 'bank_to_cashbox':
                    from_bank = get_object_or_404(BankAccount, id=from_bank_id)
                    to_cashbox = get_object_or_404(Cashbox, id=to_cashbox_id)
                    
                    # التحقق من الرصيد
                    if from_bank.balance < amount:
                        messages.error(request, _('الرصيد غير كافي في البنك'))
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
                        description=f'{description} - {_("تحويل من بنك")} {from_bank.name}',
                        related_transfer=transfer,
                        created_by=request.user
                    )
                
                messages.success(request, _('تم إنشاء التحويل بنجاح'))
                return redirect('cashboxes:transfer_detail', transfer_id=transfer.id)
        
        except Exception as e:
            messages.error(request, _('حدث خطأ أثناء إنشاء التحويل'))
    
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
                
                messages.success(request, _('تم حذف المعاملة بنجاح وتم تحديث جميع الأرصدة المرتبطة.'))
                
        except Exception as e:
            messages.error(request, _('حدث خطأ أثناء حذف المعاملة: {}').format(str(e)))
        
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
                
                messages.success(request, _('تم حذف التحويل بنجاح وتم تحديث جميع الأرصدة المرتبطة.'))
                
        except Exception as e:
            messages.error(request, _('حدث خطأ أثناء حذف التحويل: {}').format(str(e)))
        
        return redirect('cashboxes:cashbox_list')


@method_decorator(login_required, name='dispatch')
class ClearCashboxTransactionsView(View):
    """حذف جميع معاملات الصندوق مع تحديث الأرصدة"""
    
    def post(self, request, cashbox_id):
        cashbox = get_object_or_404(Cashbox, id=cashbox_id)
        
        # التحقق من الصلاحيات
        if not (request.user.is_superuser or request.user.is_staff):
            messages.error(request, _('ليس لديك صلاحية لمسح معاملات الصندوق'))
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
                
                messages.success(request, _('تم مسح جميع معاملات الصندوق "{}" بنجاح وتم تحديث جميع الأرصدة المرتبطة.').format(cashbox.name))
                
        except Exception as e:
            messages.error(request, _('حدث خطأ أثناء مسح معاملات الصندوق: {}').format(str(e)))
        
        return redirect('cashboxes:cashbox_detail', cashbox_id=cashbox_id)


@login_required
def cashbox_delete(request, cashbox_id):
    """حذف الصندوق - محسّن للتعامل مع الحماية"""
    # التحقق من الصلاحيات
    if not (request.user.is_superuser or request.user.is_staff):
        messages.error(request, _('ليس لديك صلاحية لحذف الصناديق'))
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
                    messages.error(request, _('لا يمكن حذف الصندوق لأن الرصيد غير صفر'))
                    return redirect('cashboxes:cashbox_detail', cashbox_id=cashbox_id)
                
                # الآن احذف الصندوق - التحويلات ستصبح تلقائياً بمرجع NULL
                cashbox_name = cashbox.name
                cashbox.delete()
                messages.success(request, _('تم حذف الصندوق "{}" بنجاح مع الحفاظ على التحويلات والأرصدة في الصناديق الأخرى').format(cashbox_name))
                return redirect('cashboxes:cashbox_list')
                
        except ProtectedError as e:
            messages.error(request, _('لا يمكن حذف الصندوق بسبب وجود معاملات مرتبطة محمية'))
        except Exception as e:
            messages.error(request, _('حدث خطأ أثناء حذف الصندوق: {}').format(str(e)))
    
    return redirect('cashboxes:cashbox_detail', cashbox_id=cashbox_id)
