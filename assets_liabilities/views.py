from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from datetime import date, datetime
from decimal import Decimal

from .models import (
    AssetCategory, Asset, LiabilityCategory, Liability, DepreciationEntry
)
from .forms import (
    AssetCategoryForm, AssetForm, LiabilityCategoryForm, LiabilityForm, DepreciationEntryForm
)
from settings.models import CompanySettings


@login_required
def assets_liabilities_dashboard(request):
    """لوحة تحكم الأصول والخصوم"""
    # الحصول على العملة الأساسية
    company_settings = CompanySettings.objects.first()
    base_currency = company_settings.base_currency if company_settings else None
    
    # إحصائيات الأصول
    total_assets_cost = Asset.objects.filter(
        status='active'
    ).aggregate(total=Sum('purchase_cost'))['total'] or 0
    
    total_depreciation = Asset.objects.filter(
        status='active'
    ).aggregate(total=Sum('accumulated_depreciation'))['total'] or 0
    
    net_assets_value = total_assets_cost - total_depreciation
    
    # إحصائيات الخصوم
    total_liabilities = Liability.objects.filter(
        status='active'
    ).aggregate(total=Sum('current_balance'))['total'] or 0
    
    overdue_liabilities = Liability.objects.filter(
        status='overdue'
    ).aggregate(total=Sum('current_balance'))['total'] or 0
    
    # الأصول حسب الفئة
    assets_by_category = AssetCategory.objects.annotate(
        total_cost=Sum('asset__purchase_cost'),
        total_depreciation=Sum('asset__accumulated_depreciation')
    ).filter(is_active=True)
    
    # الخصوم المستحقة قريباً
    upcoming_liabilities = Liability.objects.filter(
        status='active',
        due_date__range=[date.today(), date.today().replace(month=date.today().month+1)]
    ).select_related('category', 'currency').order_by('due_date')[:5]
    
    context = {
        'page_title': _('لوحة تحكم الأصول والخصوم'),
        'total_assets_cost': total_assets_cost,
        'total_depreciation': total_depreciation,
        'net_assets_value': net_assets_value,
        'total_liabilities': total_liabilities,
        'overdue_liabilities': overdue_liabilities,
        'assets_by_category': assets_by_category,
        'upcoming_liabilities': upcoming_liabilities,
        'base_currency': base_currency,
    }
    
    return render(request, 'assets_liabilities/dashboard.html', context)


@login_required
def asset_list(request):
    """قائمة الأصول"""
    assets = Asset.objects.select_related(
        'category', 'responsible_person', 'created_by', 'currency'
    ).order_by('-purchase_date')
    
    # التصفية
    category = request.GET.get('category')
    if category:
        assets = assets.filter(category_id=category)
    
    status = request.GET.get('status')
    if status:
        assets = assets.filter(status=status)
    
    search = request.GET.get('search')
    if search:
        assets = assets.filter(
            Q(asset_number__icontains=search) |
            Q(name__icontains=search) |
            Q(supplier__icontains=search)
        )
    
    # الترقيم
    paginator = Paginator(assets, 25)
    page_number = request.GET.get('page')
    assets_page = paginator.get_page(page_number)
    
    # فئات للتصفية
    categories = AssetCategory.objects.filter(is_active=True).order_by('name')
    
    # حساب القيمة الإجمالية للأصول
    total_value = assets.aggregate(
        total=Sum('purchase_cost')
    )['total'] or 0
    
    context = {
        'page_title': _('الأصول'),
        'assets': assets_page,
        'categories': categories,
        'status_choices': Asset.STATUS_CHOICES,
        'total_value': total_value,
    }
    
    return render(request, 'assets_liabilities/asset_list.html', context)


@login_required
def asset_create(request):
    """إضافة أصل جديد"""
    if request.method == 'POST':
        form = AssetForm(request.POST)
        if form.is_valid():
            asset = form.save(commit=False)
            asset.created_by = request.user
            asset.save()
            messages.success(request, _('تم إنشاء الأصل بنجاح'))
            return redirect('assets_liabilities:asset_detail', asset_id=asset.id)
        else:
            messages.error(request, _('يرجى تصحيح الأخطاء في النموذج'))
    else:
        form = AssetForm()
    
    context = {
        'form': form,
        'page_title': _('إضافة أصل جديد'),
    }
    return render(request, 'assets_liabilities/asset_create.html', context)


@login_required
def asset_detail(request, asset_id):
    """تفاصيل الأصل"""
    asset = get_object_or_404(Asset.objects.select_related('category', 'responsible_person', 'created_by', 'currency'), id=asset_id)
    
    # قيود الإهلاك المرتبطة
    depreciation_entries = DepreciationEntry.objects.filter(asset=asset).select_related('created_by', 'currency').order_by('-depreciation_date')
    
    context = {
        'asset': asset,
        'depreciation_entries': depreciation_entries,
        'page_title': f'{_("تفاصيل الأصل")} - {asset.name}',
    }
    return render(request, 'assets_liabilities/asset_detail.html', context)


@login_required
def liability_list(request):
    """قائمة الخصوم"""
    from datetime import timedelta
    
    liabilities = Liability.objects.select_related(
        'category', 'created_by', 'currency'
    ).order_by('due_date')
    
    # التصفية
    category = request.GET.get('category')
    if category:
        liabilities = liabilities.filter(category_id=category)
    
    status = request.GET.get('status')
    if status:
        liabilities = liabilities.filter(status=status)
    
    search = request.GET.get('search')
    if search:
        liabilities = liabilities.filter(
            Q(liability_number__icontains=search) |
            Q(name__icontains=search) |
            Q(creditor_name__icontains=search)
        )
    
    # الترقيم
    paginator = Paginator(liabilities, 25)
    page_number = request.GET.get('page')
    liabilities = paginator.get_page(page_number)
    
    # فئات للتصفية
    categories = LiabilityCategory.objects.filter(is_active=True).order_by('name')
    
    # التواريخ للمقارنة
    today = date.today()
    week_from_today = today + timedelta(days=7)
    
    context = {
        'page_title': _('الخصوم'),
        'liabilities': liabilities,
        'categories': categories,
        'status_choices': Liability.STATUS_CHOICES,
        'today': today,
        'week_from_today': week_from_today,
    }
    
    return render(request, 'assets_liabilities/liability_list.html', context)


@login_required
def liability_create(request):
    """إضافة خصم جديد"""
    if request.method == 'POST':
        form = LiabilityForm(request.POST)
        if form.is_valid():
            liability = form.save(commit=False)
            liability.created_by = request.user
            liability.save()
            messages.success(request, _('تم إنشاء الخصم بنجاح'))
            return redirect('assets_liabilities:liability_detail', liability_id=liability.id)
        else:
            messages.error(request, _('يرجى تصحيح الأخطاء في النموذج'))
    else:
        form = LiabilityForm()
    
    context = {
        'form': form,
        'page_title': _('إضافة خصم جديد'),
    }
    return render(request, 'assets_liabilities/liability_create.html', context)


@login_required
def liability_detail(request, liability_id):
    """تفاصيل الخصم"""
    liability = get_object_or_404(Liability.objects.select_related('category', 'created_by', 'currency'), id=liability_id)
    
    context = {
        'liability': liability,
        'page_title': f'{_("تفاصيل الخصم")} - {liability.name}',
    }
    return render(request, 'assets_liabilities/liability_detail.html', context)


@login_required
def depreciation_create(request, asset_id):
    """إضافة قيد إهلاك جديد"""
    asset = get_object_or_404(Asset, id=asset_id)
    
    if request.method == 'POST':
        form = DepreciationEntryForm(request.POST)
        if form.is_valid():
            depreciation = form.save(commit=False)
            depreciation.created_by = request.user
            depreciation.asset = asset
            
            # حساب القيم تلقائياً
            depreciation.accumulated_depreciation_before = asset.accumulated_depreciation
            depreciation.accumulated_depreciation_after = asset.accumulated_depreciation + depreciation.depreciation_amount
            depreciation.net_book_value_after = asset.purchase_cost - depreciation.accumulated_depreciation_after
            
            depreciation.save()
            
            # تحديث الأصل
            asset.accumulated_depreciation = depreciation.accumulated_depreciation_after
            asset.last_depreciation_date = depreciation.depreciation_date
            asset.save()
            
            messages.success(request, _('تم إنشاء قيد الإهلاك بنجاح'))
            return redirect('assets_liabilities:asset_detail', asset_id=asset.id)
        else:
            messages.error(request, _('يرجى تصحيح الأخطاء في النموذج'))
    else:
        form = DepreciationEntryForm(initial={'asset': asset})
    
    context = {
        'form': form,
        'asset': asset,
        'page_title': f'{_("إضافة قيد إهلاك")} - {asset.name}',
    }
    return render(request, 'assets_liabilities/depreciation_create.html', context)
