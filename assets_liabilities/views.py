from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count
from django.contrib.auth import get_user_model
from datetime import date, datetime
from decimal import Decimal

from .models import (
    AssetCategory, Asset, LiabilityCategory, Liability, DepreciationEntry
)
from .forms import (
    AssetCategoryForm, AssetForm, LiabilityCategoryForm, LiabilityForm, DepreciationEntryForm
)
from settings.models import CompanySettings, Currency

User = get_user_model()


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
        # التحقق من نوع المحتوى
        if request.content_type == 'application/json':
            # معالجة طلب JSON من الـ modal
            import json
            from django.http import JsonResponse
            
            try:
                data = json.loads(request.body)
                
                # العثور على الفئة
                category = None
                if data.get('category'):
                    try:
                        category = AssetCategory.objects.get(name=data['category'])
                    except AssetCategory.DoesNotExist:
                        # إنشاء فئة جديدة إذا لم تكن موجودة
                        category = AssetCategory.objects.create(
                            name=data['category'],
                            description=f'فئة تم إنشاؤها تلقائياً: {data["category"]}',
                            created_by=request.user
                        )
                
                # توليد رقم الأصل تلقائياً
                from datetime import datetime
                current_year = datetime.now().year
                count = Asset.objects.filter(
                    asset_number__startswith=f'AS{current_year}'
                ).count() + 1
                asset_number = f'AS{current_year}{count:04d}'
                
                # إنشاء الأصل
                asset = Asset.objects.create(
                    name=data['name'],
                    category=category,
                    purchase_cost=data['purchase_value'],
                    current_value=data['purchase_value'],
                    purchase_date=data.get('purchase_date'),
                    useful_life=data.get('useful_life', 5),
                    salvage_value=data.get('salvage_value', 0),
                    description=data.get('description', ''),
                    asset_number=asset_number,
                    created_by=request.user,
                    responsible_person=request.user,
                    currency=Currency.objects.filter(is_active=True).first()
                )
                
                # تسجيل النشاط
                from core.signals import log_activity
                log_activity(
                    action_type='create',
                    obj=asset,
                    description=f'إضافة أصل جديد من المودال: {asset.name} - رقم الأصل: {asset.asset_number} - القيمة: {asset.purchase_cost}',
                    user=request.user
                )
                
                return JsonResponse({
                    'success': True,
                    'message': f'تم إنشاء الأصل "{asset.name}" بنجاح',
                    'asset_id': asset.pk,
                    'asset_name': asset.name,
                    'asset_number': asset.asset_number
                })
                
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'error': str(e)
                })
        
        else:
            # معالجة النموذج العادي
            form = AssetForm(request.POST)
            if form.is_valid():
                try:
                    with transaction.atomic():
                        asset = form.save(commit=False)
                        asset.created_by = request.user
                        
                        # توليد رقم الأصل تلقائياً إذا لم يكن موجود
                        if not asset.asset_number:
                            from datetime import datetime
                            current_year = datetime.now().year
                            count = Asset.objects.filter(
                                asset_number__startswith=f'AS{current_year}'
                            ).count() + 1
                            asset.asset_number = f'AS{current_year}{count:04d}'
                        
                        # تعيين القيمة الحالية إذا لم تكن محددة
                        if not asset.current_value:
                            asset.current_value = asset.purchase_cost
                        
                        asset.save()
                        
                        # تسجيل النشاط
                        from core.signals import log_activity
                        log_activity(
                            action_type='create',
                            obj=asset,
                            description=f'إضافة أصل جديد: {asset.name} - رقم الأصل: {asset.asset_number} - القيمة: {asset.purchase_cost}',
                            user=request.user
                        )
                        
                        messages.success(request, f'تم إنشاء الأصل "{asset.name}" بنجاح')
                        return redirect('assets_liabilities:asset_detail', pk=asset.pk)
                        
                except Exception as e:
                    messages.error(request, f'خطأ في إنشاء الأصل: {str(e)}')
            else:
                messages.error(request, 'يرجى تصحيح الأخطاء في النموذج')
    else:
        form = AssetForm()
    
    # جلب البيانات المطلوبة للنموذج
    categories = AssetCategory.objects.filter(is_active=True).order_by('name')
    currencies = Currency.objects.filter(is_active=True).order_by('name')
    users = User.objects.filter(is_active=True).order_by('first_name', 'last_name')
    
    context = {
        'form': form,
        'categories': categories,
        'currencies': currencies,
        'users': users,
        'page_title': 'إضافة أصل جديد',
    }
    return render(request, 'assets_liabilities/asset_create.html', context)


@login_required
def asset_detail(request, pk):
    """تفاصيل الأصل"""
    asset = get_object_or_404(
        Asset.objects.select_related(
            'category', 'responsible_person', 'created_by', 'currency'
        ), 
        pk=pk
    )
    
    # قيود الإهلاك المرتبطة
    depreciation_entries = DepreciationEntry.objects.filter(
        asset=asset
    ).select_related('created_by', 'currency').order_by('-depreciation_date')
    
    context = {
        'asset': asset,
        'depreciation_entries': depreciation_entries,
        'page_title': f'تفاصيل الأصل - {asset.name}',
    }
    return render(request, 'assets_liabilities/asset_detail.html', context)


@login_required
def asset_edit(request, pk):
    """تعديل الأصل"""
    asset = get_object_or_404(Asset, pk=pk)
    
    if request.method == 'POST':
        form = AssetForm(request.POST, instance=asset)
        if form.is_valid():
            try:
                with transaction.atomic():
                    updated_asset = form.save()
                    
                    # تسجيل النشاط
                    from core.signals import log_activity
                    log_activity(
                        action_type='update',
                        obj=updated_asset,
                        description=f'تعديل الأصل: {updated_asset.name} - رقم الأصل: {updated_asset.asset_number}',
                        user=request.user
                    )
                    
                    messages.success(request, f'تم تحديث الأصل "{updated_asset.name}" بنجاح')
                    return redirect('assets_liabilities:asset_detail', pk=updated_asset.pk)
                    
            except Exception as e:
                messages.error(request, f'خطأ في تحديث الأصل: {str(e)}')
        else:
            messages.error(request, 'يرجى تصحيح الأخطاء في النموذج')
    else:
        form = AssetForm(instance=asset)
    
    # جلب البيانات المطلوبة للنموذج
    categories = AssetCategory.objects.filter(is_active=True).order_by('name')
    currencies = Currency.objects.filter(is_active=True).order_by('name')
    users = User.objects.filter(is_active=True).order_by('first_name', 'last_name')
    
    context = {
        'form': form,
        'asset': asset,
        'categories': categories,
        'currencies': currencies,
        'users': users,
        'page_title': f'تعديل الأصل - {asset.name}',
    }
    return render(request, 'assets_liabilities/asset_edit.html', context)


@login_required
def asset_delete(request, pk):
    """حذف الأصل"""
    asset = get_object_or_404(Asset, pk=pk)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                asset_name = asset.name
                asset_number = asset.asset_number
                
                # تسجيل النشاط قبل الحذف
                from core.signals import log_activity
                log_activity(
                    action_type='delete',
                    obj=None,
                    description=f'حذف الأصل: {asset_name} - رقم الأصل: {asset_number}',
                    user=request.user
                )
                
                asset.delete()
                messages.success(request, f'تم حذف الأصل "{asset_name}" بنجاح')
                
        except Exception as e:
            messages.error(request, f'خطأ في حذف الأصل: {str(e)}')
        
        return redirect('assets_liabilities:asset_list')
    
    context = {
        'asset': asset,
        'page_title': f'حذف الأصل - {asset.name}',
    }
    return render(request, 'assets_liabilities/asset_confirm_delete.html', context)


@login_required
def asset_category_list(request):
    """قائمة فئات الأصول"""
    categories = AssetCategory.objects.annotate(
        assets_count=Count('asset')
    ).order_by('type', 'name')
    
    context = {
        'categories': categories,
        'page_title': 'فئات الأصول',
    }
    return render(request, 'assets_liabilities/asset_category_list.html', context)


@login_required
def asset_category_create(request):
    """إضافة فئة أصول جديدة"""
    if request.method == 'POST':
        form = AssetCategoryForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    category = form.save(commit=False)
                    category.created_by = request.user
                    category.save()
                    
                    # تسجيل النشاط
                    from core.signals import log_activity
                    log_activity(
                        action_type='create',
                        obj=category,
                        description=f'إضافة فئة أصول جديدة: {category.name} - النوع: {category.get_type_display()}',
                        user=request.user
                    )
                    
                    messages.success(request, f'تم إنشاء فئة الأصول "{category.name}" بنجاح')
                    return redirect('assets_liabilities:asset_category_list')
                    
            except Exception as e:
                messages.error(request, f'خطأ في إنشاء فئة الأصول: {str(e)}')
        else:
            messages.error(request, 'يرجى تصحيح الأخطاء في النموذج')
    else:
        form = AssetCategoryForm()
    
    context = {
        'form': form,
        'page_title': 'إضافة فئة أصول جديدة',
    }
    return render(request, 'assets_liabilities/asset_category_create.html', context)


@login_required
def asset_category_edit(request, pk):
    """تعديل فئة الأصول"""
    category = get_object_or_404(AssetCategory, pk=pk)
    
    if request.method == 'POST':
        form = AssetCategoryForm(request.POST, instance=category)
        if form.is_valid():
            try:
                with transaction.atomic():
                    updated_category = form.save()
                    
                    # تسجيل النشاط
                    from core.signals import log_activity
                    log_activity(
                        action_type='update',
                        obj=updated_category,
                        description=f'تعديل فئة الأصول: {updated_category.name} - النوع: {updated_category.get_type_display()}',
                        user=request.user
                    )
                    
                    messages.success(request, f'تم تحديث فئة الأصول "{updated_category.name}" بنجاح')
                    return redirect('assets_liabilities:asset_category_list')
                    
            except Exception as e:
                messages.error(request, f'خطأ في تحديث فئة الأصول: {str(e)}')
        else:
            messages.error(request, 'يرجى تصحيح الأخطاء في النموذج')
    else:
        form = AssetCategoryForm(instance=category)
    
    context = {
        'form': form,
        'category': category,
        'page_title': f'تعديل فئة الأصول - {category.name}',
    }
    return render(request, 'assets_liabilities/asset_category_edit.html', context)


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
            
            # إذا لم يتم تحديد الرصيد الحالي، استخدم المبلغ الأصلي
            if not liability.current_balance:
                liability.current_balance = liability.original_amount
            
            liability.save()
            
            # تسجيل النشاط
            from core.signals import log_activity
            log_activity(
                action_type='create',
                obj=liability,
                description=f'إضافة خصم جديد: {liability.name}',
                user=request.user
            )
            
            messages.success(request, _('تم إنشاء الخصم بنجاح'))
            return redirect('assets_liabilities:liability_list')
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


@login_required
def category_create_ajax(request):
    """إنشاء فئة أصل جديدة عبر AJAX"""
    if request.method == 'POST':
        import json
        from django.http import JsonResponse
        
        try:
            data = json.loads(request.body)
            
            # التحقق من البيانات المطلوبة
            name = data.get('name', '').strip()
            if not name:
                return JsonResponse({
                    'success': False,
                    'error': 'اسم الفئة مطلوب'
                })
            
            # التحقق من عدم وجود فئة بنفس الاسم
            if AssetCategory.objects.filter(name=name).exists():
                return JsonResponse({
                    'success': False,
                    'error': 'فئة بهذا الاسم موجودة مسبقاً'
                })
            
            # إنشاء الفئة الجديدة
            category = AssetCategory.objects.create(
                name=name,
                description=data.get('description', ''),
                is_active=data.get('is_active', True),
                created_by=request.user
            )
            
            # تسجيل النشاط
            from core.signals import log_activity
            log_activity(
                action_type='create',
                obj=category,
                description=f'إضافة فئة أصل جديدة: {category.name}',
                user=request.user
            )
            
            return JsonResponse({
                'success': True,
                'message': f'تم إنشاء الفئة "{category.name}" بنجاح',
                'category_id': category.pk,
                'category_name': category.name
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({
        'success': False,
        'error': 'طريقة الطلب غير مدعومة'
    })


@login_required
def liability_category_create_ajax(request):
    """إنشاء فئة خصم جديدة عبر AJAX"""
    if request.method == 'POST':
        import json
        from django.http import JsonResponse
        
        try:
            # التحقق من البيانات المرسلة عبر FormData
            name = request.POST.get('name', '').strip()
            description = request.POST.get('description', '').strip()
            
            # التحقق من البيانات المطلوبة
            if not name:
                return JsonResponse({
                    'success': False,
                    'error': 'اسم الفئة مطلوب'
                })
            
            # التحقق من عدم وجود فئة بنفس الاسم
            if LiabilityCategory.objects.filter(name=name).exists():
                return JsonResponse({
                    'success': False,
                    'error': 'فئة بهذا الاسم موجودة مسبقاً'
                })
            
            # إنشاء الفئة الجديدة
            category = LiabilityCategory.objects.create(
                name=name,
                description=description,
                is_active=True,
                created_by=request.user
            )
            
            # تسجيل النشاط
            from core.signals import log_activity
            log_activity(
                action_type='create',
                obj=category,
                description=f'إضافة فئة خصم جديدة: {category.name}',
                user=request.user
            )
            
            return JsonResponse({
                'success': True,
                'message': f'تم إنشاء الفئة "{category.name}" بنجاح',
                'category': {
                    'id': category.pk,
                    'name': category.name
                }
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({
        'success': False,
        'error': 'طريقة الطلب غير مدعومة'
    })
