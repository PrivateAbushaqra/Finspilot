from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.utils.translation import gettext_lazy as _
from django.http import JsonResponse
from django.core.paginator import Paginator
from decimal import Decimal
from datetime import datetime, date

from .models import Account, JournalEntry, JournalLine
from .forms import (AccountForm, JournalEntryForm, JournalLineFormSet, 
                   JournalSearchForm, TrialBalanceForm)
from .services import JournalService


@login_required
def journal_dashboard(request):
    """لوحة تحكم القيود المحاسبية"""
    # إحصائيات عامة
    total_entries = JournalEntry.objects.count()
    total_accounts = Account.objects.filter(is_active=True).count()
    recent_entries = JournalEntry.objects.select_related().order_by('-created_at')[:5]
    
    # إحصائيات القيود حسب النوع
    entries_by_type = {}
    for ref_type, ref_name in JournalEntry.REFERENCE_TYPES:
        count = JournalEntry.objects.filter(reference_type=ref_type).count()
        entries_by_type[ref_name] = count
    
    # إحصائيات الحسابات حسب النوع
    account_types_count = {}
    for account_type, type_name in Account.ACCOUNT_TYPES:
        count = Account.objects.filter(account_type=account_type, is_active=True).count()
        account_types_count[type_name] = count
    
    # القيود الحديثة مع التفاصيل
    recent_entries_with_totals = []
    for entry in recent_entries:
        entry_dict = {
            'entry': entry,
            'total_debit': entry.lines.aggregate(total=Sum('debit'))['total'] or 0,
            'total_credit': entry.lines.aggregate(total=Sum('credit'))['total'] or 0,
        }
        recent_entries_with_totals.append(entry_dict)
    
    context = {
        'total_entries': total_entries,
        'total_accounts': total_accounts,
        'recent_entries': recent_entries_with_totals,
        'account_types_count': account_types_count,
        'entries_by_type': entries_by_type,
    }
    return render(request, 'journal/dashboard.html', context)


@login_required
def account_list(request):
    """قائمة الحسابات"""
    accounts = Account.objects.filter(is_active=True).order_by('code')
    
    # البحث
    search = request.GET.get('search')
    if search:
        accounts = accounts.filter(
            Q(name__icontains=search) | 
            Q(code__icontains=search) |
            Q(description__icontains=search)
        )
    
    # التصفية حسب النوع
    account_type = request.GET.get('type')
    if account_type:
        accounts = accounts.filter(account_type=account_type)
    
    # الترقيم
    paginator = Paginator(accounts, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'account_types': Account.ACCOUNT_TYPES,
        'current_type': account_type,
        'search_query': search
    }
    return render(request, 'journal/account_list.html', context)


@login_required
def account_create(request):
    """إنشاء حساب جديد"""
    if request.method == 'POST':
        form = AccountForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _('تم إنشاء الحساب بنجاح'))
            return redirect('journal:account_list')
    else:
        form = AccountForm()
    
    return render(request, 'journal/account_form.html', {'form': form, 'title': _('إنشاء حساب جديد')})


@login_required
def account_edit(request, pk):
    """تعديل حساب"""
    account = get_object_or_404(Account, pk=pk)
    if request.method == 'POST':
        form = AccountForm(request.POST, instance=account)
        if form.is_valid():
            form.save()
            messages.success(request, _('تم تحديث الحساب بنجاح'))
            return redirect('journal:account_list')
    else:
        form = AccountForm(instance=account)
    
    return render(request, 'journal/account_form.html', {
        'form': form, 
        'title': _('تعديل الحساب'),
        'account': account
    })


@login_required
def account_delete(request, pk):
    """حذف حساب"""
    account = get_object_or_404(Account, pk=pk)
    
    # التحقق من الصلاحيات
    if not (request.user.is_superuser or request.user.has_perm('users.can_delete_accounts')):
        messages.error(request, _('ليس لديك صلاحية لحذف الحسابات'))
        return redirect('journal:account_list')
    
    # التحقق من وجود حركات على الحساب
    if account.journal_lines.exists():
        messages.error(request, _('لا يمكن حذف الحساب لوجود حركات عليه'))
        return redirect('journal:account_list')
    
    if request.method == 'POST':
        account_name = account.name
        account.delete()
        
        # تسجيل النشاط
        try:
            from core.models import AuditLog
            AuditLog.objects.create(
                user=request.user,
                action_type='delete',
                content_type='Account',
                description=f'تم حذف الحساب: {account_name}'
            )
        except Exception as e:
            pass
            
        messages.success(request, _('تم حذف الحساب بنجاح'))
        return redirect('journal:account_list')
    
    return redirect('journal:account_list')


@login_required
def account_detail(request, pk):
    """تفاصيل الحساب"""
    account = get_object_or_404(Account, pk=pk)
    
    # الحصول على حركات الحساب
    lines = JournalLine.objects.filter(account=account).order_by('-created_at')
    
    # البحث في الحركات
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if date_from:
        lines = lines.filter(journal_entry__entry_date__gte=date_from)
    if date_to:
        lines = lines.filter(journal_entry__entry_date__lte=date_to)
    
    # حساب الإجماليات
    totals = lines.aggregate(
        total_debit=Sum('debit'),
        total_credit=Sum('credit')
    )
    
    # الترقيم
    paginator = Paginator(lines, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'account': account,
        'page_obj': page_obj,
        'totals': totals,
        'date_from': date_from,
        'date_to': date_to,
        'balance': account.get_balance()
    }
    return render(request, 'journal/account_detail.html', context)


@login_required
def journal_entry_list(request):
    """قائمة القيود المحاسبية"""
    entries = JournalEntry.objects.all().order_by('-entry_date', '-created_at')
    
    # البحث والتصفية
    form = JournalSearchForm(request.GET)
    if form.is_valid():
        if form.cleaned_data['date_from']:
            entries = entries.filter(entry_date__gte=form.cleaned_data['date_from'])
        if form.cleaned_data['date_to']:
            entries = entries.filter(entry_date__lte=form.cleaned_data['date_to'])
        if form.cleaned_data['reference_type']:
            entries = entries.filter(reference_type=form.cleaned_data['reference_type'])
        if form.cleaned_data['account']:
            entries = entries.filter(lines__account=form.cleaned_data['account']).distinct()
        if form.cleaned_data['entry_number']:
            entries = entries.filter(entry_number__icontains=form.cleaned_data['entry_number'])
    
    # حساب الإحصائيات
    total_amount = entries.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    
    # الترقيم
    paginator = Paginator(entries, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'entries': page_obj,
        'form': form,
        'reference_types': JournalEntry.REFERENCE_TYPES,
        'total_amount': total_amount
    }
    return render(request, 'journal/entry_list.html', context)


@login_required
def journal_entry_create(request):
    """إنشاء قيد محاسبي جديد"""
    if request.method == 'POST':
        form = JournalEntryForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.created_by = request.user
            entry.save()
            
            formset = JournalLineFormSet(request.POST, instance=entry)
            if formset.is_valid():
                formset.save()
                
                # التحقق من توازن القيد
                try:
                    entry.clean()
                    # حساب إجمالي المبلغ
                    total_debit = entry.lines.aggregate(total=Sum('debit'))['total'] or Decimal('0')
                    entry.total_amount = total_debit
                    entry.save()
                    
                    messages.success(request, _('تم إنشاء القيد بنجاح'))
                    return redirect('journal:entry_detail', pk=entry.pk)
                except Exception as e:
                    messages.error(request, str(e))
            else:
                messages.error(request, _('يرجى التحقق من بيانات البنود'))
    else:
        form = JournalEntryForm()
        entry = JournalEntry()
        formset = JournalLineFormSet(instance=entry)
    
    context = {
        'form': form,
        'formset': formset,
        'accounts': Account.objects.filter(is_active=True).order_by('code'),
        'title': _('إنشاء قيد محاسبي جديد')
    }
    return render(request, 'journal/entry_create.html', context)


@login_required
def journal_entry_detail(request, pk):
    """تفاصيل القيد المحاسبي"""
    entry = get_object_or_404(JournalEntry, pk=pk)
    lines = entry.lines.all().order_by('id')
    
    # حساب الإجماليات
    totals = lines.aggregate(
        total_debit=Sum('debit'),
        total_credit=Sum('credit')
    )
    
    context = {
        'entry': entry,
        'lines': lines,
        'totals': totals
    }
    return render(request, 'journal/entry_detail.html', context)


@login_required
def trial_balance(request):
    """ميزان المراجعة"""
    from datetime import datetime, date, timedelta
    
    # تواريخ افتراضية (الشهر الحالي)
    today = date.today()
    default_date_from = today.replace(day=1)  # أول يوم في الشهر
    default_date_to = today
    
    # إذا كان هناك بيانات في الطلب، استخدمها، وإلا استخدم القيم الافتراضية
    initial_data = {
        'date_from': request.GET.get('date_from', default_date_from.strftime('%Y-%m-%d')),
        'date_to': request.GET.get('date_to', default_date_to.strftime('%Y-%m-%d')),
        'account_type': request.GET.get('account_type', '')
    }
    
    form = TrialBalanceForm(initial=initial_data)
    accounts_data = []
    totals = {'debit': Decimal('0'), 'credit': Decimal('0')}
    
    # إذا كان الطلب GET وله بيانات، أو استخدم البيانات الافتراضية
    if request.GET or True:  # عرض البيانات دائماً
        # استخدام البيانات من الطلب أو الافتراضية
        date_from_str = request.GET.get('date_from', default_date_from.strftime('%Y-%m-%d'))
        date_to_str = request.GET.get('date_to', default_date_to.strftime('%Y-%m-%d'))
        account_type = request.GET.get('account_type', '')
        
        try:
            date_from = datetime.strptime(date_from_str, '%Y-%m-%d').date()
            date_to = datetime.strptime(date_to_str, '%Y-%m-%d').date()
        except ValueError:
            date_from = default_date_from
            date_to = default_date_to
        
        # الحصول على الحسابات
        accounts = Account.objects.filter(is_active=True)
        if account_type:
            accounts = accounts.filter(account_type=account_type)
        
        for account in accounts:
            # حساب الحركات في الفترة المحددة
            lines = JournalLine.objects.filter(
                account=account,
                journal_entry__entry_date__gte=date_from,
                journal_entry__entry_date__lte=date_to
            )
            
            if lines.exists():
                line_totals = lines.aggregate(
                    debit_total=Sum('debit'),
                    credit_total=Sum('credit')
                )
                
                debit_total = line_totals['debit_total'] or Decimal('0')
                credit_total = line_totals['credit_total'] or Decimal('0')
                balance = debit_total - credit_total
                
                if balance != 0:  # عرض الحسابات التي لها حركة فقط
                    account_data = {
                        'account': account,
                        'debit_total': debit_total,
                        'credit_total': credit_total,
                        'balance': balance,
                        'debit_balance': balance if balance > 0 else Decimal('0'),
                        'credit_balance': abs(balance) if balance < 0 else Decimal('0')
                    }
                    accounts_data.append(account_data)
                    
                    # إضافة للإجماليات
                    if balance > 0:
                        totals['debit'] += balance
                    else:
                        totals['credit'] += abs(balance)
        
        # تحديث form بالبيانات المستخدمة
        form = TrialBalanceForm(initial={
            'date_from': date_from,
            'date_to': date_to,
            'account_type': account_type
        })
    
    context = {
        'form': form,
        'accounts_data': accounts_data,
        'totals': totals,
        'date_from': date_from if 'date_from' in locals() else default_date_from,
        'date_to': date_to if 'date_to' in locals() else default_date_to,
    }
    return render(request, 'journal/trial_balance.html', context)


@login_required
def get_account_balance(request, account_id):
    """API للحصول على رصيد الحساب"""
    try:
        account = Account.objects.get(pk=account_id)
        balance = account.get_balance()
        return JsonResponse({
            'success': True,
            'balance': float(balance),
            'account_name': account.name,
            'account_code': account.code
        })
    except Account.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': _('الحساب غير موجود')
        })


@login_required
def accounts_api(request):
    """API للحصول على قائمة الحسابات للاستخدام في JavaScript"""
    search = request.GET.get('search', '')
    accounts = Account.objects.filter(is_active=True)
    
    if search:
        accounts = accounts.filter(
            Q(name__icontains=search) | Q(code__icontains=search)
        )
    
    accounts_data = [
        {
            'id': account.id,
            'code': account.code,
            'name': account.name,
            'type': account.get_account_type_display(),
            'balance': float(account.get_balance())
        }
        for account in accounts[:20]  # حد أقصى 20 نتيجة
    ]
    
    return JsonResponse({'accounts': accounts_data})

@login_required
def journal_entries_by_type(request):
    """عرض القيود المحاسبية حسب النوع"""
    entry_type = request.GET.get('type', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    entries = JournalEntry.objects.all()
    
    # تصفية حسب النوع
    if entry_type:
        entries = entries.filter(reference_type=entry_type)
    
    # تصفية حسب التاريخ
    if date_from:
        entries = entries.filter(entry_date__gte=date_from)
    if date_to:
        entries = entries.filter(entry_date__lte=date_to)
    
    entries = entries.order_by('-entry_date', '-created_at')
    
    # إحصائيات
    total_entries = entries.count()
    total_amount = entries.aggregate(total=Sum('total_amount'))['total'] or 0
    
    # إحصائيات حسب النوع
    types_statistics = []
    reference_types = JournalEntry.REFERENCE_TYPES
    for type_value, type_name in reference_types:
        count = JournalEntry.objects.filter(reference_type=type_value).count()
        total_for_type = JournalEntry.objects.filter(reference_type=type_value).aggregate(
            total=Sum('total_amount'))['total'] or 0
        
        # تحديد الأيقونة
        icon = 'file-invoice'  # افتراضي
        if type_value == 'sales_invoice':
            icon = 'shopping-cart'
        elif type_value == 'purchase_invoice':
            icon = 'truck'
        elif type_value == 'receipt':
            icon = 'money-bill-wave'
        elif type_value == 'payment':
            icon = 'credit-card'
        elif type_value == 'manual':
            icon = 'edit'
        
        types_statistics.append({
            'value': type_value,
            'name': type_name,
            'count': count,
            'total_amount': total_for_type,
            'icon': icon
        })
    
    # اسم النوع المحدد
    selected_type_name = ''
    if entry_type:
        for type_value, type_name in reference_types:
            if type_value == entry_type:
                selected_type_name = type_name
                break
    
    # الترقيم
    paginator = Paginator(entries, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'entries': page_obj,
        'page_obj': page_obj,
        'reference_types': reference_types,
        'types_statistics': types_statistics,
        'selected_type': entry_type,
        'selected_type_name': selected_type_name,
        'date_from': date_from,
        'date_to': date_to,
        'total_entries': total_entries,
        'total_amount': total_amount,
    }
    return render(request, 'journal/entries_by_type.html', context)

@login_required
def journal_entry_detail_with_lines(request, pk):
    """تفاصيل القيد المحاسبي مع البنود"""
    entry = get_object_or_404(JournalEntry, pk=pk)
    lines = entry.lines.all().order_by('id')
    
    # حساب الإجماليات
    totals = lines.aggregate(
        total_debit=Sum('debit'),
        total_credit=Sum('credit')
    )
    
    context = {
        'entry': entry,
        'lines': lines,
        'totals': totals,
    }
    return render(request, 'journal/entry_detail_with_lines.html', context)

@login_required
def delete_journal_entry(request, pk):
    """حذف قيد محاسبي (للمشرفين فقط)"""
    if not (request.user.is_superuser or request.user.is_staff):
        messages.error(request, _('ليس لديك صلاحية لحذف القيود المحاسبية'))
        return redirect('journal:entry_list')
    
    entry = get_object_or_404(JournalEntry, pk=pk)
    
    if request.method == 'POST':
        try:
            entry_number = entry.entry_number
            entry.delete()
            messages.success(request, f'تم حذف القيد {entry_number} بنجاح')
        except Exception as e:
            messages.error(request, f'خطأ في حذف القيد: {str(e)}')
        
        return redirect('journal:entry_list')
    
    context = {
        'entry': entry,
        'lines': entry.lines.all(),
    }
    return render(request, 'journal/entry_confirm_delete.html', context)

@login_required
def account_ledger(request, pk):
    """دفتر الحساب (حركات مفصلة)"""
    account = get_object_or_404(Account, pk=pk)
    
    # التصفية بالتاريخ
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    lines = JournalLine.objects.filter(account=account).select_related('journal_entry')
    
    if date_from:
        lines = lines.filter(journal_entry__entry_date__gte=date_from)
    if date_to:
        lines = lines.filter(journal_entry__entry_date__lte=date_to)
    
    lines = lines.order_by('journal_entry__entry_date', 'journal_entry__created_at')
    
    # حساب الرصيد التراكمي
    running_balance = Decimal('0')
    lines_with_balance = []
    
    for line in lines:
        if account.account_type in ['asset', 'expense', 'purchases']:
            # الأصول والمصاريف ترتفع بالمدين
            running_balance += line.debit - line.credit
        else:
            # المطلوبات والإيرادات وحقوق الملكية ترتفع بالدائن
            running_balance += line.credit - line.debit
        
        lines_with_balance.append({
            'line': line,
            'balance': running_balance
        })
    
    # الترقيم
    paginator = Paginator(lines_with_balance, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # إجماليات
    totals = lines.aggregate(
        total_debit=Sum('debit'),
        total_credit=Sum('credit')
    )
    
    context = {
        'account': account,
        'page_obj': page_obj,
        'totals': totals,
        'date_from': date_from,
        'date_to': date_to,
        'final_balance': running_balance,
    }
    return render(request, 'journal/account_ledger.html', context)
