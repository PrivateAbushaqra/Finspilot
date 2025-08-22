from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.urls import reverse
from datetime import date, datetime
from decimal import Decimal

from .models import RevenueExpenseCategory, RevenueExpenseEntry, RecurringRevenueExpense
from .forms import RevenueExpenseCategoryForm, RevenueExpenseEntryForm, RecurringRevenueExpenseForm
from settings.models import CompanySettings


@login_required
def revenue_expense_dashboard(request):
    """لوحة تحكم الإيرادات والمصروفات"""
    # الحصول على العملة الأساسية
    company_settings = CompanySettings.objects.first()
    base_currency = company_settings.base_currency if company_settings else None
    
    # الإحصائيات الشهرية
    current_month = date.today().month
    current_year = date.today().year
    
    monthly_revenues = RevenueExpenseEntry.objects.filter(
        type='revenue',
        date__month=current_month,
        date__year=current_year,
        is_approved=True
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    monthly_expenses = RevenueExpenseEntry.objects.filter(
        type='expense',
        date__month=current_month,
        date__year=current_year,
        is_approved=True
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # الإحصائيات السنوية
    yearly_revenues = RevenueExpenseEntry.objects.filter(
        type='revenue',
        date__year=current_year,
        is_approved=True
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    yearly_expenses = RevenueExpenseEntry.objects.filter(
        type='expense',
        date__year=current_year,
        is_approved=True
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # آخر العمليات
    recent_entries = RevenueExpenseEntry.objects.select_related('category', 'created_by', 'currency').order_by('-created_at')[:10]
    
    # العمليات المتكررة المستحقة
    pending_recurring = RecurringRevenueExpense.objects.filter(
        is_active=True,
        next_due_date__lte=date.today()
    ).select_related('category', 'currency').order_by('next_due_date')[:5]
    
    context = {
        'page_title': _('لوحة تحكم الإيرادات والمصروفات'),
        'monthly_revenues': monthly_revenues,
        'monthly_expenses': monthly_expenses,
        'monthly_net': monthly_revenues - monthly_expenses,
        'yearly_revenues': yearly_revenues,
        'yearly_expenses': yearly_expenses,
        'yearly_net': yearly_revenues - yearly_expenses,
        'recent_entries': recent_entries,
        'pending_recurring': pending_recurring,
        'base_currency': base_currency,
    }
    
    return render(request, 'revenues_expenses/dashboard.html', context)


@login_required
def category_list(request):
    """قائمة فئات الإيرادات والمصروفات"""
    categories = RevenueExpenseCategory.objects.filter(is_active=True).select_related('created_by')
    
    # التصفية
    category_type = request.GET.get('type')
    if category_type:
        categories = categories.filter(type=category_type)
    
    search = request.GET.get('search')
    if search:
        categories = categories.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search)
        )
    
    # الترقيم
    paginator = Paginator(categories, 25)
    page_number = request.GET.get('page')
    categories = paginator.get_page(page_number)
    
    context = {
        'page_title': _('فئات الإيرادات والمصروفات'),
        'categories': categories,
        'category_types': RevenueExpenseCategory.CATEGORY_TYPES,
    }
    
    return render(request, 'revenues_expenses/category_list.html', context)


@login_required
def category_create(request):
    """إضافة فئة جديدة"""
    if request.method == 'POST':
        form = RevenueExpenseCategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.created_by = request.user
            category.save()
            messages.success(request, _('تم إنشاء الفئة بنجاح'))
            return redirect('revenues_expenses:category_list')
        else:
            messages.error(request, _('يرجى تصحيح الأخطاء في النموذج'))
    else:
        form = RevenueExpenseCategoryForm()
    
    context = {
        'form': form,
        'page_title': _('إضافة فئة جديدة'),
    }
    return render(request, 'revenues_expenses/category_create.html', context)


@login_required
def entry_create(request):
    """إضافة قيد جديد"""
    if request.method == 'POST':
        form = RevenueExpenseEntryForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.created_by = request.user
            entry.save()
            messages.success(request, _('تم إنشاء القيد بنجاح'))
            return redirect('revenues_expenses:entry_detail', entry_id=entry.id)
        else:
            messages.error(request, _('يرجى تصحيح الأخطاء في النموذج'))
    else:
        form = RevenueExpenseEntryForm()
    
    context = {
        'form': form,
        'page_title': _('إضافة قيد جديد'),
    }
    return render(request, 'revenues_expenses/entry_create.html', context)


@login_required
def entry_detail(request, entry_id):
    """تفاصيل القيد"""
    entry = get_object_or_404(RevenueExpenseEntry.objects.select_related('category', 'created_by', 'approved_by', 'currency'), id=entry_id)
    context = {
        'entry': entry,
        'page_title': f'{_("تفاصيل القيد")} - {entry.entry_number}',
    }
    return render(request, 'revenues_expenses/entry_detail.html', context)


@login_required
def entry_approve(request, entry_id):
    """اعتماد القيد"""
    entry = get_object_or_404(RevenueExpenseEntry, id=entry_id)
    if not entry.is_approved:
        entry.is_approved = True
        entry.approved_by = request.user
        entry.approved_at = datetime.now()
        entry.save()
        messages.success(request, _('تم اعتماد القيد بنجاح'))
    return redirect('revenues_expenses:entry_detail', entry_id=entry.id)


@login_required
def recurring_list(request):
    """قائمة الإيرادات والمصروفات المتكررة"""
    recurring = RecurringRevenueExpense.objects.filter(is_active=True).select_related('category', 'created_by', 'currency')
    context = {
        'recurring': recurring,
        'page_title': _('الإيرادات والمصروفات المتكررة'),
    }
    return render(request, 'revenues_expenses/recurring_list.html', context)


@login_required
def recurring_create(request):
    """إضافة إيراد/مصروف متكرر"""
    if request.method == 'POST':
        form = RecurringRevenueExpenseForm(request.POST)
        if form.is_valid():
            recurring = form.save(commit=False)
            recurring.created_by = request.user
            recurring.save()
            messages.success(request, _('تم إنشاء الإيراد/المصروف المتكرر بنجاح'))
            return redirect('revenues_expenses:recurring_list')
        else:
            messages.error(request, _('يرجى تصحيح الأخطاء في النموذج'))
    else:
        form = RecurringRevenueExpenseForm()
    
    context = {
        'form': form,
        'page_title': _('إضافة إيراد/مصروف متكرر'),
    }
    return render(request, 'revenues_expenses/recurring_create.html', context)


@login_required
def entry_list(request):
    """قائمة قيود الإيرادات والمصروفات"""
    entries = RevenueExpenseEntry.objects.select_related(
        'category', 'created_by', 'approved_by', 'currency'
    ).order_by('-date', '-created_at')
    
    # التصفية
    entry_type = request.GET.get('type')
    if entry_type:
        entries = entries.filter(type=entry_type)
    
    category = request.GET.get('category')
    if category:
        entries = entries.filter(category_id=category)
    
    status = request.GET.get('status')
    if status == 'approved':
        entries = entries.filter(is_approved=True)
    elif status == 'pending':
        entries = entries.filter(is_approved=False)
    
    search = request.GET.get('search')
    if search:
        entries = entries.filter(
            Q(entry_number__icontains=search) |
            Q(description__icontains=search) |
            Q(reference_number__icontains=search)
        )
    
    # الترقيم
    paginator = Paginator(entries, 25)
    page_number = request.GET.get('page')
    entries = paginator.get_page(page_number)
    
    # فئات للتصفية
    categories = RevenueExpenseCategory.objects.filter(is_active=True).order_by('name')
    
    context = {
        'page_title': _('قيود الإيرادات والمصروفات'),
        'entries': entries,
        'categories': categories,
        'entry_types': RevenueExpenseEntry.ENTRY_TYPES,
    }
    
    return render(request, 'revenues_expenses/entry_list.html', context)
