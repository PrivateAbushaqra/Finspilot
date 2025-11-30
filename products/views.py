from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView, View
from django.db.models import Q
from django.http import JsonResponse
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import Category, Product
from core.models import AuditLog
from inventory.models import InventoryMovement, Warehouse
from .permissions import (
    CanViewProductsMixin, CanAddProductsMixin, CanEditProductsMixin, CanDeleteProductsMixin,
    CanViewProductCategoriesMixin, CanAddProductCategoriesMixin, 
    CanEditProductCategoriesMixin, CanDeleteProductCategoriesMixin
)

# Category Views
class CategoryListView(CanViewProductCategoriesMixin, LoginRequiredMixin, TemplateView):
    template_name = 'products/category_list.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        categories = Category.objects.all()
        context['categories'] = categories
        context['total_categories'] = categories.count()
        context['active_categories'] = categories.filter(is_active=True).count()
        context['inactive_categories'] = categories.filter(is_active=False).count()
        return context

class CategoryCreateView(CanAddProductCategoriesMixin, LoginRequiredMixin, View):
    template_name = 'products/category_add.html'
    
    def get(self, request, *args, **kwargs):
        # حساب الرقم التسلسلي التالي
        from django.db.models import Max
        max_seq = Category.objects.aggregate(Max('sequence_number'))['sequence_number__max']
        if max_seq:
            next_seq = max_seq + 1
        else:
            next_seq = 10000
            
        context = {
            'categories': Category.objects.filter(parent__isnull=True),  # فقط الفئات الرئيسية
            'next_sequence_number': next_seq
        }
        return render(request, self.template_name, context)
    
    def post(self, request, *args, **kwargs):
        try:
            # استلام البيانات من النموذج
            name = request.POST.get('name', '').strip()
            name_en = request.POST.get('name_en', '').strip()
            code = request.POST.get('code', '').strip()
            parent_id = request.POST.get('parent', '')
            description = request.POST.get('description', '').strip()
            sort_order = request.POST.get('sort_order', '0')
            is_active = request.POST.get('is_active') == 'on'
            sequence_number = request.POST.get('sequence_number', '').strip()
            
            # التحقق من صحة البيانات
            if not name:
                messages.error(request, _('Category name is required!'))
                return self.get(request)
            
            # التحقق من عدم تكرار الرمز
            if code and Category.objects.filter(code=code).exists():
                messages.error(request, _('Category code already exists!'))
                return self.get(request)
            
            # معالجة التصنيف الأب
            parent = None
            if parent_id:
                try:
                    parent = Category.objects.get(id=parent_id)
                except Category.DoesNotExist:
                    parent = None
            
            # إنشاء التصنيف
            category = Category()
            category.name = name
            category.name_en = name_en
            category.code = code if code else None
            category.parent = parent
            category.description = description
            category.is_active = is_active
            
            # معالجة الرقم التسلسلي
            if sequence_number and sequence_number.isdigit():
                # التحقق من الصلاحية
                if request.user.is_superuser or request.user.has_perm('products.can_edit_category_sequence_number'):
                    seq_num = int(sequence_number)
                    # التحقق من عدم تكرار الرقم
                    if Category.objects.filter(sequence_number=seq_num).exists():
                        messages.error(request, _('Sequence number already exists!'))
                        return self.get(request)
                    category.sequence_number = seq_num
            
            category.save()
            
            # تسجيل النشاط في سجل المراجعة
            AuditLog.objects.create(
                user=request.user,
                action_type='create',
                content_type='Category',
                object_id=category.id,
                description=f'تم إنشاء فئة جديدة: {category.name} - رقم التسلسل: {category.sequence_number}',
                ip_address=self.get_client_ip(request)
            )
            
            messages.success(request, _(f'Category "{category.name}" created successfully!'))
            return redirect('products:category_list')
            
        except Exception as e:
            messages.error(request, _(f'Error creating category: {str(e)}'))
            return self.get(request)
    
    def get_client_ip(self, request):
        """الحصول على عنوان IP للعميل"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

class CategoryUpdateView(LoginRequiredMixin, View):
    template_name = 'products/category_edit.html'
    
    def get(self, request, pk, *args, **kwargs):
        category = get_object_or_404(Category, pk=pk)
        context = {
            'category': category,
            'categories': Category.objects.filter(parent__isnull=True).exclude(pk=pk)
        }
        return render(request, self.template_name, context)
    
    def post(self, request, pk, *args, **kwargs):
        try:
            category = get_object_or_404(Category, pk=pk)
            
            # استلام البيانات من النموذج
            name = request.POST.get('name', '').strip()
            name_en = request.POST.get('name_en', '').strip()
            code = request.POST.get('code', '').strip()
            parent_id = request.POST.get('parent', '')
            description = request.POST.get('description', '').strip()
            sort_order = request.POST.get('sort_order', '0')
            is_active = request.POST.get('is_active') == 'on'
            sequence_number = request.POST.get('sequence_number', '').strip()
            
            # التحقق من صحة البيانات
            if not name:
                messages.error(request, _('Category name is required!'))
                return self.get(request, pk)
            
            # معالجة رقم التسلسل
            if sequence_number:
                try:
                    sequence_number = int(sequence_number)
                    
                    # التحقق من الصلاحية - يجب أن يكون المستخدم مسؤول أو لديه صلاحية تعديل رقم التسلسل
                    if not request.user.is_superuser and not request.user.has_perm('products.can_edit_category_sequence_number'):
                        messages.error(request, _('You do not have permission to edit the sequence number!'))
                        return self.get(request, pk)
                    
                    # التحقق من أن رقم التسلسل فريد
                    existing_category = Category.objects.filter(sequence_number=sequence_number).exclude(id=category.id).first()
                    if existing_category:
                        messages.error(request, _(f'Sequence number {sequence_number} is already used by category "{existing_category.name}"!'))
                        return self.get(request, pk)
                    
                    category.sequence_number = sequence_number
                except ValueError:
                    messages.error(request, _('Invalid sequence number!'))
                    return self.get(request, pk)
            
            # معالجة التصنيف الأب
            parent = None
            if parent_id:
                try:
                    parent = Category.objects.get(id=parent_id)
                    # التأكد من عدم جعل التصنيف أب لنفسه
                    if parent.id == category.id:
                        messages.error(request, _('Cannot make category parent of itself!'))
                        return self.get(request, pk)
                except Category.DoesNotExist:
                    parent = None
            
            # تحديث التصنيف
            category.name = name
            category.name_en = name_en
            category.code = code if code else None
            category.parent = parent
            category.description = description
            category.is_active = is_active
            category.save()
            
            # تسجيل النشاط
            sequence_info = f' - رقم التسلسل: {category.sequence_number}' if sequence_number else ''
            AuditLog.objects.create(
                user=request.user,
                action_type='update',
                content_type='Category',
                object_id=category.id,
                description=f'تعديل الفئة: {category.name}{sequence_info}',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            messages.success(request, _(f'Category "{category.name}" updated successfully!'))
            return redirect('products:category_list')
            
        except Exception as e:
            messages.error(request, _(f'Error updating category: {str(e)}'))
            return self.get(request, pk)

class CategoryDeleteView(LoginRequiredMixin, View):
    template_name = 'products/category_delete.html'
    
    def get(self, request, pk, *args, **kwargs):
        category = get_object_or_404(Category, pk=pk)
        products_count = Product.objects.filter(category=category).count()
        subcategories_count = Category.objects.filter(parent=category).count()
        context = {
            'category': category,
            'products_count': products_count,
            'subcategories_count': subcategories_count
        }
        return render(request, self.template_name, context)
    
    def post(self, request, pk, *args, **kwargs):
        try:
            category = get_object_or_404(Category, pk=pk)
            category_name = category.name
            
            # التحقق من وجود منتجات مرتبطة
            products_count = Product.objects.filter(category=category).count()
            if products_count > 0:
                messages.error(
                    request, 
                    _(f'Cannot delete category "{category_name}" because it has {products_count} linked products! ')
                    + _('You must delete or move the products first.')
                )
                return redirect('products:category_list')
            
            # التحقق من وجود فئات فرعية
            subcategories_count = Category.objects.filter(parent=category).count()
            if subcategories_count > 0:
                messages.error(
                    request, 
                    _(f'Cannot delete category "{category_name}" because it has {subcategories_count} subcategories! ')
                    + _('You must delete or move the subcategories first.')
                )
                return redirect('products:category_list')
            
            # حذف التصنيف
            category.delete()
            
            # تسجيل النشاط
            AuditLog.objects.create(
                user=request.user,
                action_type='delete',
                content_type='Category',
                object_id=pk,
                description=f'حذف الفئة: {category_name}',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            messages.success(request, _(f'Category "{category_name}" deleted successfully!'))
            
        except Category.DoesNotExist:
            messages.error(request, _('Selected category does not exist!'))
        except Exception as e:
            messages.error(request, _(f'Error deleting category: {str(e)}'))
        
        return redirect('products:category_list')

# Product Views
class ProductListView(CanViewProductsMixin, LoginRequiredMixin, ListView):
    model = Product
    template_name = 'products/product_list.html'
    context_object_name = 'products'
    paginate_by = 30  # عدد مناسب لطباعة A4 (حوالي 30 سطر في الصفحة)
    
    def get_queryset(self):
        queryset = Product.objects.all().select_related('category').order_by('name')
        
        # الحصول على معاملات البحث والفلترة
        search_query = self.request.GET.get('search', '')
        category_filter = self.request.GET.get('category', '')
        status_filter = self.request.GET.get('status', '')
        
        # تطبيق البحث
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(code__icontains=search_query) |
                Q(barcode__icontains=search_query) |
                Q(serial_number__icontains=search_query)
            )
        
        # تطبيق فلتر التصنيف
        if category_filter:
            queryset = queryset.filter(category_id=category_filter)
        
        # تطبيق فلتر الحالة
        if status_filter == 'active':
            queryset = queryset.filter(is_active=True)
        elif status_filter == 'inactive':
            queryset = queryset.filter(is_active=False)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # إضافة إحصائيات لجميع المنتجات
        all_products = Product.objects.all()
        context['total_products'] = all_products.count()
        context['active_products'] = all_products.filter(is_active=True).count()
        context['inactive_products'] = all_products.filter(is_active=False).count()
        
        # إحصائيات المنتجات المفلترة
        filtered_products = self.get_queryset()
        context['filtered_count'] = filtered_products.count()
        
        # إضافة التصنيفات للفلترة
        context['categories'] = Category.objects.filter(is_active=True).order_by('name')
        
        # إضافة المستودعات للشاشة المنبثقة
        from inventory.models import Warehouse
        context['warehouses'] = Warehouse.objects.filter(is_active=True).exclude(code='MAIN')
        
        # إضافة معاملات البحث والفلترة
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_category'] = self.request.GET.get('category', '')
        context['selected_status'] = self.request.GET.get('status', '')
        
        return context

class ProductCreateView(CanAddProductsMixin, LoginRequiredMixin, View):
    template_name = 'products/product_add.html'
    
    def get(self, request, *args, **kwargs):
        context = {
            'categories': Category.objects.filter(is_active=True).order_by('name'),
            'warehouses': Warehouse.objects.filter(is_active=True).exclude(code='MAIN'),
            'products': Product.objects.filter(is_active=True).order_by('name')  # للربط
        }
        return render(request, self.template_name, context)
    
    def post(self, request, *args, **kwargs):
        try:
            # استلام البيانات من النموذج
            name = request.POST.get('name', '').strip()
            name_en = request.POST.get('name_en', '').strip()
            product_type = request.POST.get('product_type', 'physical')
            sku = request.POST.get('sku', '').strip()
            barcode = request.POST.get('barcode', '').strip()
            serial_number = request.POST.get('serial_number', '').strip()
            category_id = request.POST.get('category', '')
            unit = request.POST.get('unit', 'piece')
            sale_price = request.POST.get('sale_price', '0')
            wholesale_price = request.POST.get('wholesale_price', '0')
            tax_rate = request.POST.get('tax_rate', '0')
            opening_balance = request.POST.get('opening_balance', '0')
            opening_balance_cost = request.POST.get('opening_balance_cost', '0')
            min_stock = request.POST.get('min_stock', '0')
            max_stock = request.POST.get('max_stock', '0')
            description = request.POST.get('description', '').strip()
            is_active = request.POST.get('is_active') == 'on'
            track_stock = request.POST.get('track_stock') == 'on'
            opening_balance_warehouse_id = request.POST.get('opening_balance_warehouse')
            sequence_number = request.POST.get('sequence_number', '').strip()
            
            # Linked Units fields
            unit_type = request.POST.get('unit_type', 'standalone')
            linked_product_id = request.POST.get('linked_product', '')
            conversion_factor = request.POST.get('conversion_factor', '0')
            
            # التحقق من صحة البيانات
            if not name:
                messages.error(request, _('Product name is required!'))
                return self.get(request)
            
            if not sale_price or float(sale_price) <= 0:
                messages.error(request, _('Sale price is required and must be greater than zero!'))
                return self.get(request)
            
            # التحقق من التصنيف
            if not category_id:
                messages.error(request, _('Category is required!'))
                return self.get(request)
            
            try:
                category = Category.objects.get(id=category_id)
            except Category.DoesNotExist:
                messages.error(request, _('Selected category does not exist!'))
                return self.get(request)
            
            # التحقق من عدم تكرار رمز المنتج
            if sku and Product.objects.filter(code=sku).exists():
                messages.error(request, _('Product code already exists!'))
                return self.get(request)
            
            # التحقق من عدم تكرار الباركود
            if barcode and Product.objects.filter(barcode=barcode).exists():
                messages.error(request, _('Barcode already exists!'))
                return self.get(request)
            
            # التحقق من عدم تكرار الرقم التسلسلي
            if serial_number and Product.objects.filter(serial_number=serial_number).exists():
                messages.error(request, _('Serial number already exists!'))
                return self.get(request)
            
            # إنشاء رمز تلقائي إذا لم يُدخل
            if not sku:
                # إنشاء رمز تلقائي بناءً على آخر منتج
                last_product = Product.objects.order_by('-id').first()
                if last_product:
                    last_number = int(last_product.code.split('-')[-1]) if '-' in last_product.code else 0
                    sku = f"PROD-{last_number + 1:04d}"
                else:
                    sku = "PROD-0001"
            
            # تحويل الأسعار إلى أرقام
            try:
                # سعر التكلفة يُحسب تلقائياً - نبدأ بصفر
                cost_price = 0
                sale_price = float(sale_price)
                wholesale_price = float(wholesale_price) if wholesale_price else 0
                tax_rate = float(tax_rate) if tax_rate else 0
                opening_balance = float(opening_balance) if opening_balance else 0
                opening_balance_cost = float(opening_balance_cost) if opening_balance_cost else 0
                
                # التحقق من صحة نسبة الضريبة
                if tax_rate < 0 or tax_rate > 100:
                    messages.error(request, _('Tax rate must be between 0 and 100!'))
                    return self.get(request)
                
                # التحقق من صحة رصيد بداية المدة
                if opening_balance < 0:
                    messages.error(request, _('Opening balance must be zero or greater!'))
                    return self.get(request)
                
                # التحقق من تكلفة الرصيد الافتتاحي إذا كان الرصيد أكبر من صفر
                if opening_balance > 0 and not opening_balance_warehouse_id:
                    messages.error(request, _('Opening balance warehouse is required when there is an opening balance!'))
                    return self.get(request)
                
            except ValueError:
                messages.error(request, _('Please enter valid prices and tax rate!'))
                return self.get(request)
            
            # الحصول على مستودع الرصيد الافتتاحي
            opening_balance_warehouse = None
            if opening_balance_warehouse_id:
                try:
                    opening_balance_warehouse = Warehouse.objects.get(id=opening_balance_warehouse_id, is_active=True)
                except Warehouse.DoesNotExist:
                    messages.error(request, _('Selected opening balance warehouse does not exist!'))
                    return self.get(request)
            
            # معالجة رقم التسلسل
            final_sequence_number = None
            if sequence_number:
                try:
                    final_sequence_number = int(sequence_number)
                    
                    # التحقق من الصلاحية - يجب أن يكون المستخدم مسؤول أو لديه صلاحية تعديل رقم التسلسل
                    if not request.user.is_superuser and not request.user.has_perm('products.can_edit_product_sequence_number'):
                        messages.error(request, _('You do not have permission to edit the sequence number!'))
                        return self.get(request)
                    
                    # التحقق من أن رقم التسلسل فريد
                    existing_product = Product.objects.filter(sequence_number=final_sequence_number).first()
                    if existing_product:
                        messages.error(request, _(f'Sequence number {final_sequence_number} is already used by product "{existing_product.name}"!'))
                        return self.get(request)
                    
                except ValueError:
                    messages.error(request, _('Invalid sequence number!'))
                    return self.get(request)
            
            # معالجة المنتج المرتبط
            linked_product = None
            if linked_product_id and unit_type in ['single', 'package']:
                try:
                    linked_product = Product.objects.get(id=linked_product_id, is_active=True)
                except Product.DoesNotExist:
                    messages.error(request, _('Linked product not found!'))
                    return self.get(request)
            
            # التحقق من معامل التحويل للبكج
            conversion_factor_value = 0
            if unit_type == 'package' and conversion_factor:
                try:
                    conversion_factor_value = float(conversion_factor)
                    if conversion_factor_value <= 0:
                        messages.error(request, _('Conversion factor must be greater than zero for package products!'))
                        return self.get(request)
                except ValueError:
                    messages.error(request, _('Invalid conversion factor!'))
                    return self.get(request)
            
            # إنشاء المنتج
            product = Product.objects.create(
                code=sku,
                name=name,
                name_en=name_en,  # إضافة الاسم بالإنجليزية
                product_type=product_type,  # إضافة نوع المنتج
                barcode=barcode,  # إضافة الباركود
                serial_number=serial_number,  # إضافة الرقم التسلسلي
                category=category,
                description=description,
                cost_price=cost_price,  # سيبدأ بصفر ويُحسب من المشتريات
                minimum_quantity=float(min_stock) if min_stock else 0,
                sale_price=sale_price,
                wholesale_price=wholesale_price,  # إضافة سعر الجملة
                tax_rate=tax_rate,
                opening_balance_quantity=opening_balance,
                opening_balance_cost=opening_balance_cost,
                opening_balance_warehouse=opening_balance_warehouse,
                is_active=is_active,
                sequence_number=final_sequence_number,  # رقم التسلسل
                # Linked Units fields
                unit_type=unit_type,
                linked_product=linked_product,
                conversion_factor=conversion_factor_value
            )
            
            # تسجيل النشاط
            sequence_info = f' - رقم التسلسل: {product.sequence_number}' if product.sequence_number else ''
            AuditLog.objects.create(
                user=request.user,
                action_type='create',
                content_type='Product',
                object_id=product.id,
                description=f'إضافة منتج جديد: {product.name}{sequence_info}',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            # إنشاء حركة مخزون للرصيد الافتتاحي إذا كان أكبر من صفر
            if opening_balance and float(opening_balance) > 0 and not product.is_service:
                try:
                    from journal.models import JournalEntry, JournalLine, Account
                    from core.models import DocumentSequence
                    
                    # استخدام مستودع الرصيد الافتتاحي المحدد
                    unit_cost = opening_balance_cost / opening_balance if opening_balance > 0 else 0
                    InventoryMovement.objects.create(
                        product=product,
                        warehouse=opening_balance_warehouse,
                        movement_type='in',
                        quantity=float(opening_balance),
                        unit_cost=unit_cost,
                        total_cost=opening_balance_cost,
                        reference_type='opening_balance',
                        reference_id=product.id,
                        notes=f'الرصيد الافتتاحي للمنتج {product.name}',
                        created_by=request.user,
                        date=product.created_at.date()
                    )
                    
                    # إنشاء القيد المحاسبي للرصيد الافتتاحي (حسب IFRS)
                    # وفقاً لـ IAS 2 (Inventories): يجب قياس المخزون بالتكلفة
                    # وفقاً لـ IAS 1 (Presentation of Financial Statements): الرصيد الافتتاحي يؤثر على حقوق الملكية
                    try:
                        # البحث عن حساب المستودع المحدد (IFRS Compliant - تفصيل حسب الموقع)
                        warehouse_code = f"1201{opening_balance_warehouse.id:04d}"
                        warehouse_account = Account.objects.filter(code=warehouse_code).first()
                        
                        # إذا لم يكن حساب المستودع موجوداً، إنشاؤه
                        if not warehouse_account:
                            # الحصول على حساب المخزون الرئيسي
                            parent_account = Account.objects.filter(code='1201').first()
                            if parent_account:
                                warehouse_account = Account.objects.create(
                                    code=warehouse_code,
                                    name=f'مستودع - {opening_balance_warehouse.name}',
                                    account_type='asset',
                                    parent=parent_account,
                                    description=f'حساب المستودع {opening_balance_warehouse.name}'
                                )
                        
                        # البحث عن حساب حقوق الملكية (301) - Equity
                        equity_account = Account.objects.filter(code='301').first()
                        
                        if warehouse_account and equity_account and opening_balance_cost > 0:
                            # توليد رقم القيد
                            try:
                                seq = DocumentSequence.objects.get(document_type='journal_entry')
                                entry_number = seq.get_next_number()
                            except DocumentSequence.DoesNotExist:
                                last_entry = JournalEntry.objects.order_by('-id').first()
                                if last_entry and last_entry.entry_number:
                                    try:
                                        last_num = int(last_entry.entry_number.split('-')[-1])
                                        entry_number = f'JE-{last_num + 1:06d}'
                                    except:
                                        entry_number = f'JE-{timezone.now().strftime("%Y%m%d%H%M%S")}'
                                else:
                                    entry_number = 'JE-000001'
                            
                            # إنشاء قيد اليومية (IFRS Compliant)
                            journal_entry = JournalEntry.objects.create(
                                entry_number=entry_number,
                                entry_date=timezone.now().date(),
                                entry_type='daily',
                                description=f'رصيد افتتاحي - {product.name} ({product.code})',
                                total_amount=opening_balance_cost,
                                created_by=request.user,
                            )
                            
                            # إنشاء أطراف القيد
                            # من ح/ المستودع (أصل متداول - مدين) - IFRS Compliant
                            JournalLine.objects.create(
                                journal_entry=journal_entry,
                                account=warehouse_account,
                                debit=opening_balance_cost,
                                credit=0,
                                line_description=f'رصيد افتتاحي - {product.name}'
                            )
                            
                            # إلى ح/ حقوق الملكية (دائن)
                            JournalLine.objects.create(
                                journal_entry=journal_entry,
                                account=equity_account,
                                debit=0,
                                credit=opening_balance_cost,
                                line_description=f'رصيد افتتاحي - {product.name}'
                            )
                            
                            # تحديث أرصدة الحسابات
                            warehouse_account.update_account_balance()
                            equity_account.update_account_balance()
                            
                            # تسجيل النشاط
                            AuditLog.objects.create(
                                user=request.user,
                                action_type='create',
                                content_type='JournalEntry',
                                object_id=journal_entry.id,
                                description=f'إنشاء قيد محاسبي للرصيد الافتتاحي - المنتج: {product.name} - رقم القيد: {entry_number} - المبلغ: {opening_balance_cost}',
                                ip_address=request.META.get('REMOTE_ADDR')
                            )
                    except Exception as journal_error:
                        # تسجيل الخطأ
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.error(f"خطأ في إنشاء قيد اليومية للرصيد الافتتاحي: {journal_error}")
                        
                        AuditLog.objects.create(
                            user=request.user,
                            action_type='error',
                            content_type='JournalEntry',
                            object_id=None,
                            description=f'خطأ في إنشاء القيد المحاسبي للرصيد الافتتاحي - المنتج: {product.name} - الخطأ: {str(journal_error)}',
                            ip_address=request.META.get('REMOTE_ADDR')
                        )
                        
                except Exception as e:
                    # تسجيل تحذير في حالة فشل إنشاء حركة المخزون
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"فشل في إنشاء حركة المخزون للرصيد الافتتاحي للمنتج {product.id}: {str(e)}")
            
            # معالجة رفع الصورة
            if 'image' in request.FILES:
                product.image = request.FILES['image']
                product.save()
            
            # تسجيل النشاط في سجل الأنشطة
            AuditLog.objects.create(
                user=request.user,
                action_type='create',
                content_type='Product',
                object_id=product.id,
                description=f'تم إنشاء المنتج: {product.name} - رمز المنتج: {product.code} - سعر البيع: {product.sale_price}',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            # رسالة نجاح مع تفاصيل الضريبة
            success_message = f'تم إنشاء المنتج "{product.name}" بنجاح!'
            if tax_rate > 0:
                from decimal import Decimal
                sale_price_decimal = Decimal(str(sale_price))
                tax_rate_decimal = Decimal(str(tax_rate))
                tax_amount = sale_price_decimal * (tax_rate_decimal / Decimal('100'))
                price_with_tax = sale_price_decimal + tax_amount
                success_message += f' (سعر البيع: {sale_price:.3f}، الضريبة: {tax_rate}%، السعر شامل الضريبة: {price_with_tax:.3f})'
            
            messages.success(request, success_message)
            
            # إذا كان الطلب AJAX، إرسال JSON response
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': success_message,
                    'product_id': product.id,
                    'product_name': product.name
                })
            
            return redirect('products:product_list')
            
        except Exception as e:
            # تسجيل الخطأ في audit log
            AuditLog.objects.create(
                user=request.user,
                action_type='error',
                content_type='Product',
                object_id=None,
                description=f'حدث خطأ أثناء إنشاء المنتج: {str(e)}',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"خطأ في إنشاء المنتج: {str(e)}")
            
            messages.error(request, _(f'Error creating product: {str(e)}'))
            
            # إذا كان الطلب AJAX، إرسال JSON response للخطأ
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': str(e),
                    'message': f'حدث خطأ أثناء إنشاء المنتج: {str(e)}'
                })
            
            return self.get(request)

class ProductUpdateView(CanEditProductsMixin, LoginRequiredMixin, View):
    template_name = 'products/product_edit.html'
    
    def get(self, request, pk, *args, **kwargs):
        product = get_object_or_404(Product, pk=pk)
        
        # حساب الرصيد الافتتاحي الحالي
        current_opening_balance = product.get_opening_balance()
        
        context = {
            'product': product,
            'categories': Category.objects.filter(is_active=True),
            'warehouses': Warehouse.objects.filter(is_active=True).exclude(code='MAIN'),
            'products': Product.objects.filter(is_active=True).exclude(pk=pk).order_by('name'),  # للربط (استبعاد المنتج الحالي)
            'current_opening_balance': current_opening_balance,
            'current_stock': product.current_stock,
            'maximum_quantity': product.maximum_quantity,
            'has_movements': product.has_movements
        }
        return render(request, self.template_name, context)
    
    def post(self, request, pk, *args, **kwargs):
        try:
            product = get_object_or_404(Product, pk=pk)
            
            # استلام جميع البيانات من النموذج
            name = request.POST.get('name', '').strip()
            name_en = request.POST.get('name_en', '').strip()
            product_type = request.POST.get('product_type', 'physical')
            barcode = request.POST.get('barcode', '').strip()
            serial_number = request.POST.get('serial_number', '').strip()
            category_id = request.POST.get('category', '')
            sale_price = request.POST.get('sale_price', '0')
            wholesale_price = request.POST.get('wholesale_price', '0')
            tax_rate = request.POST.get('tax_rate', '0')
            opening_balance = request.POST.get('opening_balance_quantity', '0')
            opening_balance_cost = request.POST.get('opening_balance_cost', '0')
            minimum_quantity = request.POST.get('minimum_quantity', '0')
            maximum_quantity = request.POST.get('maximum_quantity', '0')
            description = request.POST.get('description', '').strip()
            is_active = request.POST.get('is_active') == 'on'
            image = request.FILES.get('image')
            opening_balance_warehouse_id = request.POST.get('opening_balance_warehouse')
            sequence_number = request.POST.get('sequence_number', '').strip()
            
            # Linked Units fields
            unit_type = request.POST.get('unit_type', 'standalone')
            linked_product_id = request.POST.get('linked_product', '')
            conversion_factor = request.POST.get('conversion_factor', '0')
            
            # التحقق من وجود حركات على المنتج
            if product.has_movements:
                # إذا كان هناك حركات، لا نسمح بتعديل الرصيد الافتتاحي
                old_opening_balance = float(product.opening_balance_quantity)
                old_opening_balance_cost = float(product.opening_balance_cost)
                
                if (float(opening_balance) != old_opening_balance or 
                    float(opening_balance_cost) != old_opening_balance_cost):
                    messages.error(request, _('Cannot edit opening balance as there are movements for this product'))
                    return self.get(request, pk)
            
            # معالجة رقم التسلسل
            if sequence_number:
                try:
                    sequence_number = int(sequence_number)
                    
                    # التحقق من الصلاحية - يجب أن يكون المستخدم مسؤول أو لديه صلاحية تعديل رقم التسلسل
                    if not request.user.is_superuser and not request.user.has_perm('products.can_edit_product_sequence_number'):
                        messages.error(request, _('You do not have permission to edit the sequence number!'))
                        return self.get(request, pk)
                    
                    # التحقق من أن رقم التسلسل فريد
                    existing_product = Product.objects.filter(sequence_number=sequence_number).exclude(id=product.id).first()
                    if existing_product:
                        messages.error(request, _(f'Sequence number {sequence_number} is already used by product "{existing_product.name}"!'))
                        return self.get(request, pk)
                    
                    product.sequence_number = sequence_number
                except ValueError:
                    messages.error(request, _('Invalid sequence number!'))
                    return self.get(request, pk)
            
            # التحقق من صحة البيانات
            if not name:
                messages.error(request, _('Product name is required!'))
                return self.get(request, pk)
            
            if not sale_price or float(sale_price) <= 0:
                messages.error(request, _('Sale price is required and must be greater than zero!'))
                return self.get(request, pk)
            
            # التحقق من التصنيف
            if category_id:
                try:
                    category = Category.objects.get(id=category_id)
                    product.category = category
                except Category.DoesNotExist:
                    messages.error(request, _('Selected category does not exist!'))
                    return self.get(request, pk)
            
            # التحقق من عدم تكرار الباركود
            if barcode and Product.objects.filter(barcode=barcode).exclude(pk=pk).exists():
                messages.error(request, _('Barcode already exists!'))
                return self.get(request, pk)
            
            # التحقق من عدم تكرار الرقم التسلسلي
            if serial_number and Product.objects.filter(serial_number=serial_number).exclude(pk=pk).exists():
                messages.error(request, _('Serial number already exists!'))
                return self.get(request, pk)
            
            # تحويل الأسعار إلى أرقام
            try:
                # حساب سعر التكلفة المتوسط المرجح
                calculated_cost = product.calculate_weighted_average_cost()
                cost_price = float(calculated_cost)
                sale_price = float(sale_price)
                wholesale_price = float(wholesale_price) if wholesale_price else 0
                tax_rate = float(tax_rate) if tax_rate else 0
                opening_balance = float(opening_balance) if opening_balance else 0
                opening_balance_cost = float(opening_balance_cost) if opening_balance_cost else 0
                
                minimum_quantity = float(minimum_quantity) if minimum_quantity else 0
                maximum_quantity = float(maximum_quantity) if maximum_quantity else 0
                
                # التحقق من صحة تكلفة الرصيد الافتتاحي - يجب أن يكون الرصيد أكبر من صفر إذا كانت التكلفة أكبر من صفر
                if opening_balance_cost > 0 and opening_balance <= 0:
                    messages.error(request, _('The Opening Balance Must be Greater Than Zero!'))
                    return self.get(request, pk)
                
                # التحقق من صحة نسبة الضريبة
                if tax_rate < 0 or tax_rate > 100:
                    messages.error(request, _('Tax rate must be between 0 and 100!'))
                    return self.get(request, pk)
                
                # التحقق من صحة رصيد بداية المدة
                if opening_balance < 0:
                    messages.error(request, _('Opening balance must be zero or greater!'))
                    return self.get(request, pk)
                
                # التحقق من مستودع الرصيد الافتتاحي إذا كان الرصيد أكبر من صفر
                if opening_balance > 0 and not opening_balance_warehouse_id:
                    messages.error(request, _('Opening balance warehouse is required when there is an opening balance!'))
                    return self.get(request, pk)
                
            except ValueError:
                messages.error(request, _('Please enter valid prices and tax rate!'))
                return self.get(request, pk)
            
            # الحصول على مستودع الرصيد الافتتاحي
            opening_balance_warehouse = None
            if opening_balance_warehouse_id:
                try:
                    opening_balance_warehouse = Warehouse.objects.get(id=opening_balance_warehouse_id, is_active=True)
                except Warehouse.DoesNotExist:
                    messages.error(request, _('Selected opening balance warehouse does not exist!'))
                    return self.get(request, pk)
            
            # معالجة المنتج المرتبط
            linked_product = None
            if linked_product_id and unit_type in ['single', 'package']:
                try:
                    linked_product = Product.objects.get(id=linked_product_id, is_active=True)
                    # التأكد من عدم ربط المنتج بنفسه
                    if linked_product.id == product.id:
                        messages.error(request, _('Cannot link product to itself!'))
                        return self.get(request, pk)
                except Product.DoesNotExist:
                    messages.error(request, _('Linked product not found!'))
                    return self.get(request, pk)
            
            # التحقق من معامل التحويل للبكج
            conversion_factor_value = 0
            if unit_type == 'package' and conversion_factor:
                try:
                    conversion_factor_value = float(conversion_factor)
                    if conversion_factor_value <= 0:
                        messages.error(request, _('Conversion factor must be greater than zero for package products!'))
                        return self.get(request, pk)
                except ValueError:
                    messages.error(request, _('Invalid conversion factor!'))
                    return self.get(request, pk)
            
            # التعامل مع تعديل الرصيد الافتتاحي
            from decimal import Decimal
            from inventory.models import InventoryMovement
            from journal.models import JournalEntry, JournalLine, Account
            from core.models import DocumentSequence
            
            # الحصول على القيم القديمة من قاعدة البيانات قبل التحديث
            old_product_data = Product.objects.get(pk=product.pk)
            old_opening_balance_quantity = Decimal(str(old_product_data.opening_balance_quantity))
            old_opening_balance_cost = Decimal(str(old_product_data.opening_balance_cost))
            old_opening_balance_warehouse = old_product_data.opening_balance_warehouse
            
            # تحديث جميع حقول المنتج
            product.name = name
            product.name_en = name_en
            product.product_type = product_type
            product.barcode = barcode
            product.serial_number = serial_number
            product.description = description
            product.cost_price = cost_price
            product.minimum_quantity = minimum_quantity
            product.maximum_quantity = maximum_quantity
            product.sale_price = sale_price
            product.wholesale_price = wholesale_price
            product.tax_rate = tax_rate
            product.opening_balance_quantity = opening_balance
            product.opening_balance_cost = opening_balance_cost
            product.is_active = is_active
            product.opening_balance_warehouse = opening_balance_warehouse
            # Linked Units fields
            product.unit_type = unit_type
            product.linked_product = linked_product
            product.conversion_factor = conversion_factor_value
            if image:
                product.image = image
            product.save()
            
            # تسجيل النشاط
            sequence_info = f' - رقم التسلسل: {product.sequence_number}' if product.sequence_number else ''
            AuditLog.objects.create(
                user=request.user,
                action_type='update',
                content_type='Product',
                object_id=product.id,
                description=f'تعديل المنتج: {product.name}{sequence_info}',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            new_opening_balance_quantity = Decimal(str(opening_balance))
            new_opening_balance_cost = Decimal(str(opening_balance_cost))
            
            # التحقق من حدوث تغيير في الرصيد الافتتاحي أو تكلفته أو مستودعه
            opening_balance_changed = (
                new_opening_balance_quantity != old_opening_balance_quantity or
                new_opening_balance_cost != old_opening_balance_cost or
                opening_balance_warehouse != old_opening_balance_warehouse
            )
            
            if opening_balance_changed:
                # 1. حذف حركة المخزون القديمة للرصيد الافتتاحي
                old_opening_movement = InventoryMovement.objects.filter(
                    product=product,
                    movement_type='in',
                    reference_type='opening_balance'
                ).first()
                
                old_movement_id = None
                if old_opening_movement:
                    old_movement_id = old_opening_movement.id
                    old_opening_movement.delete()
                    
                    # تسجيل النشاط في سجل الأنشطة
                    AuditLog.objects.create(
                        user=request.user,
                        action_type='delete',
                        content_type='InventoryMovement',
                        object_id=old_movement_id,
                        description=_('حذف الرصيد الافتتاحي القديم للمنتج: %(product_name)s - الكمية القديمة: %(old_quantity)s - التكلفة القديمة: %(old_cost)s') % {
                            'product_name': product.name,
                            'old_quantity': old_opening_balance_quantity,
                            'old_cost': old_opening_balance_cost
                        },
                        ip_address=request.META.get('REMOTE_ADDR')
                    )
                
                # 2. حذف القيد المحاسبي القديم للرصيد الافتتاحي (إن وجد)
                old_journal_entries = JournalEntry.objects.filter(
                    description__icontains=f'{product.code}'
                ).filter(
                    description__icontains='رصيد افتتاحي'
                )
                
                for old_entry in old_journal_entries:
                    # حذف أطراف القيد
                    old_lines = JournalLine.objects.filter(journal_entry=old_entry)
                    affected_accounts = [line.account for line in old_lines]
                    old_lines.delete()
                    
                    # حذف القيد
                    old_entry_number = old_entry.entry_number
                    old_entry.delete()
                    
                    # تحديث أرصدة الحسابات المتأثرة
                    for account in affected_accounts:
                        account.update_account_balance()
                    
                    # تسجيل النشاط
                    AuditLog.objects.create(
                        user=request.user,
                        action_type='delete',
                        content_type='JournalEntry',
                        object_id=old_entry.id if hasattr(old_entry, 'id') else None,
                        description=f'حذف القيد المحاسبي القديم للرصيد الافتتاحي - المنتج: {product.name} - رقم القيد: {old_entry_number}',
                        ip_address=request.META.get('REMOTE_ADDR')
                    )
                
                # 3. إنشاء حركة مخزون جديدة للرصيد الافتتاحي إذا كان أكبر من صفر
                if new_opening_balance_quantity > 0 and opening_balance_warehouse:
                    # حساب تكلفة الوحدة
                    unit_cost = new_opening_balance_cost / new_opening_balance_quantity if new_opening_balance_quantity > 0 else Decimal('0')
                    
                    # توليد رقم الحركة
                    try:
                        seq = DocumentSequence.objects.get(document_type='inventory_movement')
                        movement_number = seq.get_next_number()
                    except DocumentSequence.DoesNotExist:
                        movement_number = f'OB-{product.code}-{timezone.now().strftime("%Y%m%d%H%M%S")}'
                    
                    # إنشاء حركة المخزون
                    new_movement = InventoryMovement.objects.create(
                        movement_number=movement_number,
                        product=product,
                        warehouse=opening_balance_warehouse,
                        movement_type='in',
                        quantity=float(new_opening_balance_quantity),
                        unit_cost=float(unit_cost),
                        total_cost=float(new_opening_balance_cost),
                        reference_type='opening_balance',
                        reference_id=product.id,
                        notes=f'تحديث الرصيد الافتتاحي للمنتج {product.name}',
                        created_by=request.user,
                        date=timezone.now().date()
                    )
                    
                    # تسجيل النشاط في سجل الأنشطة
                    AuditLog.objects.create(
                        user=request.user,
                        action_type='create',
                        content_type='InventoryMovement',
                        object_id=new_movement.id,
                        description=_('إنشاء رصيد افتتاحي جديد للمنتج: %(product_name)s - الكمية: %(quantity)s - التكلفة: %(cost)s') % {
                            'product_name': product.name,
                            'quantity': new_opening_balance_quantity,
                            'cost': new_opening_balance_cost
                        },
                        ip_address=request.META.get('REMOTE_ADDR')
                    )
                    
                    # 4. إنشاء قيد محاسبي جديد للرصيد الافتتاحي (حسب IFRS)
                    # وفقاً لـ IAS 2 (Inventories): يجب قياس المخزون بالتكلفة أو صافي القيمة القابلة للتحقق، أيهما أقل
                    # وفقاً لـ IAS 1 (Presentation of Financial Statements): الرصيد الافتتاحي يؤثر على حقوق الملكية
                    try:
                        # البحث عن حساب المخزون (1501) - Current Assets
                        # IAS 2: Inventories should be classified as current assets
                        inventory_account = Account.objects.filter(code='1501').first()
                        
                        # البحث عن حساب حقوق الملكية/الأرباح المحتجزة (301) - Equity
                        # IAS 1: Opening balances represent owner's equity contribution
                        equity_account = Account.objects.filter(code='301').first()
                        
                        if inventory_account and equity_account and new_opening_balance_cost > 0:
                            # توليد رقم القيد
                            try:
                                seq = DocumentSequence.objects.get(document_type='journal_entry')
                                entry_number = seq.get_next_number()
                            except DocumentSequence.DoesNotExist:
                                last_entry = JournalEntry.objects.order_by('-id').first()
                                if last_entry and last_entry.entry_number:
                                    try:
                                        last_num = int(last_entry.entry_number.split('-')[-1])
                                        entry_number = f'JE-{last_num + 1:06d}'
                                    except:
                                        entry_number = f'JE-{timezone.now().strftime("%Y%m%d%H%M%S")}'
                                else:
                                    entry_number = 'JE-000001'
                            
                            # إنشاء قيد اليومية (IFRS Compliant)
                            # المعالجة المحاسبية حسب IAS 2 (Inventories) و IAS 1 (Presentation)
                            journal_entry = JournalEntry.objects.create(
                                entry_number=entry_number,
                                entry_date=timezone.now().date(),
                                entry_type='daily',
                                description=f'رصيد افتتاحي - {product.name} ({product.code})',
                                total_amount=new_opening_balance_cost,
                                created_by=request.user,
                            )
                            
                            # إنشاء أطراف القيد
                            # من ح/ المخزون (أصل متداول - مدين)
                            # IAS 2: قياس المخزون بالتكلفة عند الاعتراف الأولي
                            # IAS 1: تصنيف المخزون كأصل متداول
                            JournalLine.objects.create(
                                journal_entry=journal_entry,
                                account=inventory_account,
                                debit=new_opening_balance_cost,
                                credit=Decimal('0'),
                                line_description=f'رصيد افتتاحي - {product.name}'
                            )
                            
                            # إلى ح/ حقوق الملكية (دائن)
                            # IAS 1: الرصيد الافتتاحي يؤثر على حقوق الملكية
                            # تمثل مساهمة المالك أو الأرباح المحتجزة من فترات سابقة
                            JournalLine.objects.create(
                                journal_entry=journal_entry,
                                account=equity_account,
                                debit=Decimal('0'),
                                credit=new_opening_balance_cost,
                                line_description=f'رصيد افتتاحي - {product.name}'
                            )
                            
                            # تحديث أرصدة الحسابات
                            inventory_account.update_account_balance()
                            equity_account.update_account_balance()
                            
                            # تسجيل النشاط
                            AuditLog.objects.create(
                                user=request.user,
                                action_type='create',
                                content_type='JournalEntry',
                                object_id=journal_entry.id,
                                description=f'إنشاء قيد محاسبي للرصيد الافتتاحي - المنتج: {product.name} - رقم القيد: {entry_number} - المبلغ: {new_opening_balance_cost}',
                                ip_address=request.META.get('REMOTE_ADDR')
                            )
                    except Exception as e:
                        # تسجيل الخطأ
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.error(f"خطأ في إنشاء قيد اليومية للرصيد الافتتاحي: {e}")
                        
                        AuditLog.objects.create(
                            user=request.user,
                            action_type='error',
                            content_type='JournalEntry',
                            object_id=None,
                            description=f'خطأ في إنشاء القيد المحاسبي للرصيد الافتتاحي - المنتج: {product.name} - الخطأ: {str(e)}',
                            ip_address=request.META.get('REMOTE_ADDR')
                        )
            
            # تسجيل النشاط في سجل الأنشطة
            AuditLog.objects.create(
                user=request.user,
                action_type='update',
                content_type='Product',
                object_id=product.id,
                description=f'تم تحديث المنتج: {product.name} - سعر البيع: {product.sale_price} - سعر التكلفة المحسوب: {cost_price:.3f} - الرصيد الافتتاحي: {new_opening_balance_quantity}',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            # رسالة نجاح مع تفاصيل الضريبة والرصيد الافتتاحي
            success_message = f'تم تحديث المنتج "{product.name}" بنجاح!'
            
            # إضافة معلومات الرصيد الافتتاحي إذا تم تغييره
            if opening_balance_changed:
                success_message += f' (تم تحديث الرصيد الافتتاحي من {old_opening_balance_quantity} إلى {new_opening_balance_quantity})'
            
            if tax_rate > 0:
                from decimal import Decimal
                sale_price_decimal = Decimal(str(product.sale_price))
                tax_rate_decimal = Decimal(str(tax_rate))
                tax_amount = sale_price_decimal * (tax_rate_decimal / Decimal('100'))
                price_with_tax = sale_price_decimal + tax_amount
                success_message += f' (السعر شامل الضريبة: {price_with_tax:.3f})'
            
            messages.success(request, success_message)
            
            # إذا كان الطلب AJAX، إرسال JSON response
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': success_message,
                    'product_id': product.id,
                    'product_name': product.name
                })
            
            return redirect('products:product_list')
            
        except Exception as e:
            # تسجيل الخطأ في audit log
            AuditLog.objects.create(
                user=request.user,
                action_type='error',
                content_type='Product',
                object_id=pk,
                description=f'حدث خطأ أثناء تحديث المنتج ID {pk}: {str(e)}',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"خطأ في تحديث المنتج {pk}: {str(e)}")
            
            messages.error(request, _(f'Error updating product: {str(e)}'))
            
            # إذا كان الطلب AJAX، إرسال JSON response للخطأ
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': str(e),
                    'message': f'حدث خطأ أثناء تحديث المنتج: {str(e)}'
                })
            
            return self.get(request, pk)

class ProductDeleteView(CanDeleteProductsMixin, LoginRequiredMixin, View):
    template_name = 'products/product_delete.html'
    
    def get(self, request, pk, *args, **kwargs):
        product = get_object_or_404(Product, pk=pk)
        
        # فحص الارتباطات المحمية
        related_data = self._check_product_relations(product)
        
        context = {
            'product': product,
            'related_data': related_data,
            'can_delete': not any(related_data.values())
        }
        return render(request, self.template_name, context)
    
    def post(self, request, pk, *args, **kwargs):
        try:
            product = get_object_or_404(Product, pk=pk)
            product_name = product.name
            product_code = product.code
            
            # التحقق من الارتباطات (باستثناء حركات الرصيد الافتتاحي)
            related_data = self._check_product_relations(product, exclude_opening_balance=True)
            
            if any(related_data.values()):
                # إذا كان هناك ارتباطات فعلية (غير الرصيد الافتتاحي)
                error_message = f'لا يمكن حذف المنتج "{product_name}" لأنه مرتبط بالبيانات التالية:'
                
                if related_data['inventory_movements']:
                    count = related_data['inventory_movements']['count']
                    error_message += f'\n• {count} حركة مخزون'
                
                if related_data['warehouse_transfers']:
                    count = related_data['warehouse_transfers']['count']
                    error_message += f'\n• {count} تحويل مستودع'
                
                if related_data['sales']:
                    count = related_data['sales']['count']
                    error_message += f'\n• {count} عملية بيع'
                
                if related_data['purchases']:
                    count = related_data['purchases']['count']
                    error_message += f'\n• {count} عملية شراء'
                
                error_message += '\n\nيجب حذف هذه البيانات المرتبطة أولاً قبل حذف المنتج.'
                
                messages.error(request, error_message)
                return redirect('products:product_delete', pk=pk)
            
            # حذف حركات الرصيد الافتتاحي والقيود المحاسبية المرتبطة بها
            from inventory.models import InventoryMovement
            from journal.models import JournalEntry, JournalLine
            
            # 1. حذف حركات المخزون للرصيد الافتتاحي
            opening_movements = InventoryMovement.objects.filter(
                product=product,
                reference_type='opening_balance'
            )
            
            if opening_movements.exists():
                movements_count = opening_movements.count()
                opening_movements.delete()
                
                # تسجيل الحذف في AuditLog
                AuditLog.objects.create(
                    user=request.user,
                    action_type='delete',
                    content_type='InventoryMovement',
                    object_id=None,
                    description=f'حذف {movements_count} حركة مخزون للرصيد الافتتاحي - المنتج: {product_name} ({product_code})',
                    ip_address=request.META.get('REMOTE_ADDR')
                )
            
            # 2. حذف القيود المحاسبية للرصيد الافتتاحي
            opening_journal_entries = JournalEntry.objects.filter(
                entry_type='daily'
            ).filter(
                description__icontains=product_code
            ).filter(
                description__icontains='رصيد افتتاحي'
            )
            
            for entry in opening_journal_entries:
                entry_number = entry.entry_number
                entry_amount = entry.total_amount
                
                # الحصول على الحسابات المتأثرة قبل الحذف
                entry_lines = JournalLine.objects.filter(journal_entry=entry)
                affected_accounts = [line.account for line in entry_lines]
                
                # حذف أطراف القيد
                entry_lines.delete()
                
                # حذف القيد
                entry.delete()
                
                # تحديث أرصدة الحسابات المتأثرة
                for account in affected_accounts:
                    account.update_account_balance()
                
                # تسجيل الحذف في AuditLog
                AuditLog.objects.create(
                    user=request.user,
                    action_type='delete',
                    content_type='JournalEntry',
                    object_id=None,
                    description=f'حذف قيد محاسبي للرصيد الافتتاحي - المنتج: {product_name} ({product_code}) - رقم القيد: {entry_number} - المبلغ: {entry_amount}',
                    ip_address=request.META.get('REMOTE_ADDR')
                )
            
            # 3. الآن يمكن حذف المنتج
            product.delete()
            
            # تسجيل النشاط في سجل الأنشطة
            AuditLog.objects.create(
                user=request.user,
                action_type='delete',
                content_type='Product',
                object_id=pk,
                description=f'حذف المنتج: {product_name} (الكود: {product_code})',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            messages.success(request, _(f'Product "{product_name}" deleted successfully!'))
            
        except Exception as e:
            # معالجة أخطاء أخرى غير متوقعة
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"خطأ في حذف المنتج {pk}: {str(e)}")
            
            # تسجيل الخطأ في AuditLog
            AuditLog.objects.create(
                user=request.user,
                action_type='error',
                content_type='Product',
                object_id=pk,
                description=f'خطأ في حذف المنتج ID {pk}: {str(e)}',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            messages.error(request, _(f'Unexpected error while deleting product: {str(e)}'))
        
        return redirect('products:product_list')
    
    def _check_product_relations(self, product, exclude_opening_balance=False):
        """
        فحص جميع الارتباطات المحمية للمنتج
        
        Args:
            product: المنتج المراد فحصه
            exclude_opening_balance: استثناء حركات الرصيد الافتتاحي من الفحص
        """
        related_data = {
            'inventory_movements': None,
            'warehouse_transfers': None,
            'sales': None,
            'purchases': None
        }
        
        try:
            # فحص حركات المخزون
            from inventory.models import InventoryMovement
            inventory_movements = InventoryMovement.objects.filter(product=product)
            
            # استثناء حركات الرصيد الافتتاحي إذا طُلب ذلك
            if exclude_opening_balance:
                inventory_movements = inventory_movements.exclude(reference_type='opening_balance')
            
            if inventory_movements.exists():
                related_data['inventory_movements'] = {
                    'count': inventory_movements.count(),
                    'items': list(inventory_movements.values('movement_number', 'date', 'movement_type')[:5])
                }
        except:
            pass
        
        try:
            # فحص تحويلات المستودعات
            from inventory.models import WarehouseTransferItem
            transfer_items = WarehouseTransferItem.objects.filter(product=product)
            if transfer_items.exists():
                related_data['warehouse_transfers'] = {
                    'count': transfer_items.count(),
                    'items': list(transfer_items.values('transfer__transfer_number', 'transfer__date')[:5])
                }
        except:
            pass
        
        try:
            # فحص فواتير المبيعات (إذا كانت موجودة)
            from sales.models import SalesInvoiceItem
            sale_items = SalesInvoiceItem.objects.filter(product=product)
            if sale_items.exists():
                related_data['sales'] = {
                    'count': sale_items.count(),
                    'items': list(sale_items.values('invoice__invoice_number', 'invoice__date')[:5])
                }
        except:
            pass
        
        try:
            # فحص فواتير الشراء (إذا كانت موجودة)
            from purchases.models import PurchaseInvoiceItem
            purchase_items = PurchaseInvoiceItem.objects.filter(product=product)
            if purchase_items.exists():
                related_data['purchases'] = {
                    'count': purchase_items.count(),
                    'items': list(purchase_items.values('invoice__invoice_number', 'invoice__date')[:5])
                }
        except:
            pass
        
        return related_data

class ProductDetailView(LoginRequiredMixin, TemplateView):
    template_name = 'products/product_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = get_object_or_404(Product, pk=kwargs.get('pk'))
        context['product'] = product
        
        # إحصائيات المنتج
        context['related_products'] = Product.objects.filter(
            category=product.category
        ).exclude(pk=product.pk)[:5]
        
        # جمع حركات المنتج من مختلف المصادر
        movements = []
        
        # فواتير المشتريات
        from purchases.models import PurchaseInvoiceItem
        purchase_items = PurchaseInvoiceItem.objects.filter(
            product=product
        ).select_related('invoice').order_by('-invoice__date')
        for item in purchase_items:
            movements.append({
                'type': 'purchase_invoice',
                'date': item.invoice.date,
                'reference': item.invoice.invoice_number,
                'quantity': item.quantity,
                'unit_price': item.unit_price,
                'total': item.total_amount,
                'url': f'/ar/purchases/invoices/{item.invoice.id}/',
                'description': f'فاتورة شراء - {item.invoice.supplier.name}',
                'stock_change': item.quantity  # زيادة في المخزون
            })
        
        # فواتير المبيعات
        from sales.models import SalesInvoiceItem
        sales_items = SalesInvoiceItem.objects.filter(
            product=product
        ).select_related('invoice').order_by('-invoice__date')
        for item in sales_items:
            movements.append({
                'type': 'sales_invoice',
                'date': item.invoice.date,
                'reference': item.invoice.invoice_number,
                'quantity': item.quantity,
                'unit_price': item.unit_price,
                'total': item.total_amount,
                'url': f'/ar/sales/invoices/{item.invoice.id}/',
                'description': f'فاتورة مبيعات - {item.invoice.customer.name}',
                'stock_change': -item.quantity  # نقصان في المخزون
            })
        
        # حركات المخزون (إدخالات وإخراجات) - استثناء الحركات المرتبطة بالفواتير والمردودات والتحويلات
        from inventory.models import InventoryMovement
        inventory_movements = InventoryMovement.objects.filter(
            product=product
        ).exclude(reference_type__in=['purchase_invoice', 'sales_invoice', 'purchase_return', 'sales_return', 'warehouse_transfer']).select_related('warehouse').order_by('-date')
        for movement in inventory_movements:
            stock_change = movement.quantity if movement.movement_type == 'in' else -movement.quantity
            movements.append({
                'type': f'inventory_{movement.movement_type}',
                'date': movement.date,
                'reference': movement.document_number or movement.movement_number,
                'quantity': movement.quantity,
                'unit_price': movement.unit_cost,
                'total': movement.total_cost,
                'url': movement.document_url,
                'description': f'حركة مخزون - {movement.get_movement_type_display()} - {movement.warehouse.name}',
                'stock_change': stock_change
            })
        
        # مردودات المشتريات
        from purchases.models import PurchaseReturnItem
        purchase_returns = PurchaseReturnItem.objects.filter(
            product=product
        ).select_related('return_invoice').order_by('-return_invoice__date')
        for item in purchase_returns:
            movements.append({
                'type': 'purchase_return',
                'date': item.return_invoice.date,
                'reference': item.return_invoice.return_number,
                'quantity': item.returned_quantity,
                'unit_price': item.unit_price,
                'total': item.total_amount,
                'url': f'/ar/purchases/returns/{item.return_invoice.id}/',
                'description': f'مردود شراء - {item.return_invoice.original_invoice.supplier.name}',
                'stock_change': item.returned_quantity  # زيادة في المخزون
            })
        
        # مردودات المبيعات
        from sales.models import SalesReturnItem
        sales_returns = SalesReturnItem.objects.filter(
            product=product
        ).select_related('return_invoice').order_by('-return_invoice__date')
        for item in sales_returns:
            movements.append({
                'type': 'sales_return',
                'date': item.return_invoice.date,
                'reference': item.return_invoice.return_number,
                'quantity': item.quantity,
                'unit_price': item.unit_price,
                'total': item.total_amount,
                'url': None,  # لا يوجد صفحة تفاصيل لمردودات المبيعات
                'description': f'مردود مبيعات - {item.return_invoice.original_invoice.customer.name}',
                'stock_change': item.quantity  # زيادة في المخزون
            })
        
        # ترتيب الحركات حسب التاريخ (الأحدث أولاً)
        movements.sort(key=lambda x: x['date'], reverse=True)
        
        # حساب الكمية المتوفرة لكل حركة
        current_stock = product.current_stock
        for movement in movements:
            movement['available_quantity'] = current_stock
            current_stock -= movement['stock_change']  # عكس التغيير للحصول على الكمية قبل الحركة
        
        context['product_movements'] = movements[:50]  # عرض آخر 50 حركة
        
        # تسجيل النشاط في سجل الأنشطة
        AuditLog.objects.create(
            user=self.request.user,
            action_type='view',
            content_type='product_detail',
            object_id=product.id,
            description=f'عرض تفاصيل المنتج: {product.name} مع حركات المادة',
            ip_address=self.request.META.get('REMOTE_ADDR')
        )
        
        return context

def product_search_api(request):
    return JsonResponse({'products': []})

@csrf_exempt
def category_add_ajax(request):
    """API endpoint لإضافة فئة جديدة عبر AJAX"""
    if request.method == 'POST':
        try:
            # استلام البيانات من النموذج
            name = request.POST.get('name', '').strip()
            name_en = request.POST.get('name_en', '').strip()
            code = request.POST.get('code', '').strip()
            parent_id = request.POST.get('parent', '')
            description = request.POST.get('description', '').strip()
            is_active = request.POST.get('is_active') == 'on'
            
            # التحقق من صحة البيانات
            if not name:
                return JsonResponse({
                    'success': False,
                    'error': 'اسم التصنيف مطلوب!'
                })
            
            # التحقق من عدم تكرار الرمز
            if code and Category.objects.filter(code=code).exists():
                return JsonResponse({
                    'success': False,
                    'error': 'رمز التصنيف موجود مسبقاً!'
                })
                
            # معالجة التصنيف الأب
            parent = None
            if parent_id:
                try:
                    parent = Category.objects.get(id=parent_id)
                except Category.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'error': 'التصنيف الأب المحدد غير موجود!'
                    })
            
            # إنشاء التصنيف الجديد
            category = Category.objects.create(
                name=name,
                name_en=name_en,
                code=code,
                parent=parent,
                description=description,
                is_active=is_active
            )
            
            # تسجيل النشاط في سجل الأنشطة
            AuditLog.objects.create(
                user=request.user,
                action_type='create',
                content_type='Category',
                object_id=category.id,
                description=f'تم إنشاء التصنيف: {category.name} - رمز التصنيف: {category.code}',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            return JsonResponse({
                'success': True,
                'message': f'تم إنشاء التصنيف "{category.name}" بنجاح!',
                'category': {
                    'id': category.id,
                    'name': category.name,
                    'name_en': category.name_en,
                    'code': category.code,
                    'parent_name': category.parent.name if category.parent else None,
                    'is_active': category.is_active
                }
            })
            
        except Exception as e:
            # تسجيل الخطأ في audit log
            AuditLog.objects.create(
                user=request.user,
                action_type='error',
                content_type='Category',
                object_id=None,
                description=f'حدث خطأ أثناء إنشاء التصنيف: {str(e)}',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            return JsonResponse({
                'success': False,
                'error': f'حدث خطأ أثناء إنشاء التصنيف: {str(e)}'
            })
    
    else:
        # إرسال قائمة الفئات الأساسية للاختيار كأب
        categories = Category.objects.filter(parent__isnull=True).values('id', 'name')
        return JsonResponse({
            'categories': list(categories)
        })

def product_add_ajax(request):
    """API endpoint لإضافة منتج جديد عبر AJAX"""
    if request.method == 'POST':
        try:
            # استلام البيانات من النموذج
            name = request.POST.get('name', '').strip()
            name_en = request.POST.get('name_en', '').strip()
            product_type = request.POST.get('product_type', 'physical')
            sku = request.POST.get('sku', '').strip()
            barcode = request.POST.get('barcode', '').strip()
            serial_number = request.POST.get('serial_number', '').strip()
            category_id = request.POST.get('category', '')
            unit = request.POST.get('unit', 'piece')
            cost_price = request.POST.get('cost_price', '0')
            selling_price = request.POST.get('selling_price', '0')
            wholesale_price = request.POST.get('wholesale_price', '0')
            tax_rate = request.POST.get('tax_rate', '0')
            opening_balance = request.POST.get('opening_balance', '0')
            opening_balance_cost = request.POST.get('opening_balance_cost', '0')
            min_stock = request.POST.get('min_stock', '0')
            max_stock = request.POST.get('max_stock', '0')
            description = request.POST.get('description', '').strip()
            is_active = request.POST.get('is_active') == 'on'
            track_stock = request.POST.get('track_stock') == 'on'
            opening_balance_warehouse_id = request.POST.get('opening_balance_warehouse')
            
            # التحقق من صحة البيانات
            if not name:
                return JsonResponse({
                    'success': False,
                    'error': 'اسم المنتج مطلوب!'
                })
            
            if not selling_price or float(selling_price) <= 0:
                return JsonResponse({
                    'success': False,
                    'error': 'سعر البيع مطلوب ويجب أن يكون أكبر من صفر!'
                })
            
            # التحقق من التصنيف
            if not category_id:
                return JsonResponse({
                    'success': False,
                    'error': 'التصنيف مطلوب!'
                })
            
            try:
                category = Category.objects.get(id=category_id)
            except Category.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'التصنيف المحدد غير موجود!'
                })
            
            # التحقق من عدم تكرار رمز المنتج
            if sku and Product.objects.filter(code=sku).exists():
                return JsonResponse({
                    'success': False,
                    'error': 'رمز المنتج موجود مسبقاً!'
                })
            
            # التحقق من عدم تكرار الباركود
            if barcode and Product.objects.filter(barcode=barcode).exists():
                return JsonResponse({
                    'success': False,
                    'error': 'الباركود موجود مسبقاً!'
                })
            
            # التحقق من عدم تكرار الرقم التسلسلي
            if serial_number and Product.objects.filter(serial_number=serial_number).exists():
                return JsonResponse({
                    'success': False,
                    'error': 'الرقم التسلسلي موجود مسبقاً!'
                })
            
            # إنشاء رمز تلقائي إذا لم يُدخل
            if not sku:
                last_product = Product.objects.order_by('-id').first()
                if last_product:
                    last_number = int(last_product.code.split('-')[-1]) if '-' in last_product.code else 0
                    sku = f"PROD-{last_number + 1:04d}"
                else:
                    sku = "PROD-0001"
            
            # تحويل الأسعار إلى أرقام
            try:
                cost_price = float(cost_price) if cost_price else 0
                selling_price = float(selling_price)
                wholesale_price = float(wholesale_price) if wholesale_price else 0
                tax_rate = float(tax_rate) if tax_rate else 0
                min_stock = float(min_stock) if min_stock else 0
                opening_balance = float(opening_balance) if opening_balance else 0
                opening_balance_cost = float(opening_balance_cost) if opening_balance_cost else 0
                
                # التحقق من صحة نسبة الضريبة
                if tax_rate < 0 or tax_rate > 100:
                    return JsonResponse({
                        'success': False,
                        'error': 'نسبة الضريبة يجب أن تكون بين 0 و 100!'
                    })
                
                # التحقق من صحة رصيد بداية المدة
                if opening_balance < 0:
                    return JsonResponse({
                        'success': False,
                        'error': 'رصيد بداية المدة يجب أن يكون صفر أو أكبر!'
                    })
                    
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'error': 'يرجى إدخال أسعار ونسبة ضريبة صحيحة!'
                })
            
            # إنشاء المنتج
            product = Product.objects.create(
                code=sku,
                name=name,
                name_en=name_en,
                product_type=product_type,
                barcode=barcode,
                serial_number=serial_number,
                category=category,
                description=description,
                cost_price=cost_price,
                minimum_quantity=float(min_stock) if min_stock else 0,
                sale_price=selling_price,
                wholesale_price=wholesale_price,
                tax_rate=tax_rate,
                is_active=is_active
            )
            
            # الحصول على مستودع الرصيد الافتتاحي
            opening_balance_warehouse = None
            if opening_balance_warehouse_id:
                try:
                    opening_balance_warehouse = Warehouse.objects.get(id=opening_balance_warehouse_id, is_active=True)
                except Warehouse.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'error': 'مستودع الرصيد الافتتاحي المحدد غير موجود!'
                    })
            
            # إنشاء حركة مخزون للرصيد الافتتاحي إذا كان أكبر من صفر
            if opening_balance and float(opening_balance) > 0:
                try:
                    from inventory.models import InventoryMovement, Warehouse
                    
                    # استخدام مستودع الرصيد الافتتاحي المحدد
                    unit_cost = opening_balance_cost / opening_balance if opening_balance > 0 else 0
                    InventoryMovement.objects.create(
                        product=product,
                        warehouse=opening_balance_warehouse,
                        movement_type='in',
                        quantity=float(opening_balance),
                        unit_cost=unit_cost,
                        total_cost=opening_balance_cost,
                        reference_type='opening_balance',
                        reference_id=product.id,
                        notes=f'الرصيد الافتتاحي للمنتج {product.name}',
                        created_by=request.user,
                        date=product.created_at.date()
                    )
                except Exception as e:
                    # تسجيل تحذير في حالة فشل إنشاء حركة المخزون
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"فشل في إنشاء حركة المخزون للرصيد الافتتاحي للمنتج {product.id}: {str(e)}")
            
            # معالجة رفع الصورة
            if 'image' in request.FILES:
                product.image = request.FILES['image']
                product.save()
            
            # تسجيل النشاط في سجل الأنشطة
            AuditLog.objects.create(
                user=request.user,
                action_type='create',
                content_type='Product',
                object_id=product.id,
                description=f'تم إنشاء المنتج من فاتورة المشتريات: {product.name} - رمز المنتج: {product.code} - سعر البيع: {product.sale_price}',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            # رسالة نجاح مع تفاصيل الضريبة
            success_message = f'تم إنشاء المنتج "{product.name}" بنجاح!'
            if tax_rate > 0:
                from decimal import Decimal
                selling_price_decimal = Decimal(str(selling_price))
                tax_rate_decimal = Decimal(str(tax_rate))
                tax_amount = selling_price_decimal * (tax_rate_decimal / Decimal('100'))
                price_with_tax = selling_price_decimal + tax_amount
                success_message += f' (سعر البيع: {selling_price:.3f}، الضريبة: {tax_rate}%، السعر شامل الضريبة: {price_with_tax:.3f})'
            
            return JsonResponse({
                'success': True,
                'message': success_message,
                'product': {
                    'id': product.id,
                    'name': product.name,
                    'code': product.code,
                    'sale_price': float(product.sale_price),
                    'category_name': product.category.name if product.category else None,
                    'product_type': product.product_type,
                    'tax_rate': float(product.tax_rate),
                    'is_active': product.is_active
                }
            })
            
        except Exception as e:
            # تسجيل الخطأ في audit log
            AuditLog.objects.create(
                user=request.user,
                action_type='error',
                content_type='Product',
                object_id=None,
                description=f'حدث خطأ أثناء إنشاء المنتج من فاتورة المشتريات: {str(e)}',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"خطأ في إنشاء المنتج: {str(e)}")
            
            return JsonResponse({
                'success': False,
                'error': f'حدث خطأ أثناء إنشاء المنتج: {str(e)}'
            })
    
    else:
        # إرسال قائمة الفئات للاختيار
        categories = Category.objects.filter(is_active=True).values('id', 'name')
        return JsonResponse({
            'categories': list(categories)
        })

# AJAX Views for adding categories and products from purchase invoice
@method_decorator(csrf_exempt, name='dispatch')
class CategoryAddAjaxView(LoginRequiredMixin, View):
    def dispatch(self, request, *args, **kwargs):
        """Override dispatch to log all requests"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"=== CategoryAddAjaxView dispatch called ===")
        logger.info(f"Method: {request.method}")
        logger.info(f"User: {request.user}")
        logger.info(f"POST data: {dict(request.POST) if request.method == 'POST' else 'N/A'}")
        return super().dispatch(request, *args, **kwargs)
    
    def get(self, request, *args, **kwargs):
        """إرجاع قائمة الفئات المتاحة للاستخدام في الشاشات المنبثقة"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info("=== GET method called ===")
        try:
            from .models import Category
            categories = Category.objects.filter(is_active=True).order_by('name')
            categories_data = []
            for category in categories:
                categories_data.append({
                    'id': category.id,
                    'name': category.name,
                    'code': category.code
                })
            
            return JsonResponse({
                'success': True,
                'categories': categories_data
            })
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"خطأ في تحميل الفئات: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': f'حدث خطأ أثناء تحميل الفئات: {str(e)}'
            })

    def post(self, request, *args, **kwargs):
        try:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"CategoryAddAjaxView POST called by user: {request.user}")
            
            # استلام البيانات من النموذج
            name = request.POST.get('name', '').strip()
            name_en = request.POST.get('name_en', '').strip()
            code = request.POST.get('code', '').strip()
            parent_id = request.POST.get('parent', '')
            description = request.POST.get('description', '').strip()
            is_active = request.POST.get('is_active') == 'on'
            
            logger.info(f"Received data: name={name}, code={code}, parent_id={parent_id}")
            
            # التحقق من صحة البيانات
            if not name:
                logger.warning("Category name is required")
                return JsonResponse({
                    'success': False,
                    'error': 'اسم الفئة مطلوب!'
                })
            
            if not name_en:
                logger.warning("Category English name is required")
                return JsonResponse({
                    'success': False,
                    'error': _('الاسم بالإنجليزية مطلوب!')
                })
            
            # التحقق من عدم تكرار الرمز
            if code and Category.objects.filter(code=code).exists():
                logger.warning(f"Category code {code} already exists")
                return JsonResponse({
                    'success': False,
                    'error': 'رمز الفئة موجود مسبقاً!'
                })
            
            # معالجة الفئة الأب
            parent = None
            if parent_id:
                try:
                    parent = Category.objects.get(id=parent_id)
                    logger.info(f"Parent category found: {parent.name}")
                except Category.DoesNotExist:
                    logger.warning(f"Parent category {parent_id} not found")
                    parent = None
            
            # إنشاء الفئة
            logger.info("Creating category...")
            category = Category.objects.create(
                name=name,
                name_en=name_en,
                code=code if code else None,
                parent=parent,
                description=description,
                is_active=is_active
            )
            logger.info(f"Category created successfully: {category.id} - {category.name}")
            
            # تسجيل النشاط في سجل المراجعة
            AuditLog.objects.create(
                user=request.user,
                action_type='create',
                content_type='Category',
                object_id=category.id,
                description=f'تم إنشاء فئة جديدة من فاتورة المشتريات: {category.name}',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            logger.info("Audit log created")
            
            return JsonResponse({
                'success': True,
                'message': f'تم إنشاء الفئة "{category.name}" بنجاح!',
                'category': {
                    'id': category.id,
                    'name': category.name,
                    'code': category.code
                }
            })
            
        except Exception as e:
            logger.error(f"Error in CategoryAddAjaxView: {str(e)}", exc_info=True)
            
            # تسجيل الخطأ في audit log
            AuditLog.objects.create(
                user=request.user,
                action_type='error',
                content_type='Category',
                object_id=None,
                description=f'حدث خطأ أثناء إنشاء الفئة من فاتورة المشتريات: {str(e)}',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            return JsonResponse({
                'success': False,
                'error': f'حدث خطأ أثناء إنشاء الفئة: {str(e)}'
            })

@method_decorator(csrf_exempt, name='dispatch')
class ProductAddAjaxView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        """إرجاع قائمة الفئات المتاحة للاستخدام في modal إنشاء المنتج"""
        try:
            from .models import Category
            categories = Category.objects.filter(is_active=True).order_by('name')
            categories_data = []
            for category in categories:
                categories_data.append({
                    'id': category.id,
                    'name': category.name,
                    'code': category.code
                })
            
            return JsonResponse({
                'success': True,
                'categories': categories_data
            })
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"خطأ في تحميل الفئات: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': f'حدث خطأ أثناء تحميل الفئات: {str(e)}'
            })

    def post(self, request, *args, **kwargs):
        try:
            # استلام البيانات من النموذج
            name = request.POST.get('name', '').strip()
            name_en = request.POST.get('name_en', '').strip()
            sku = request.POST.get('sku', '').strip()
            product_type = request.POST.get('product_type', 'physical')
            barcode = request.POST.get('barcode', '').strip()
            serial_number = request.POST.get('serial_number', '').strip()
            category_id = request.POST.get('category', '')
            unit = request.POST.get('unit', 'piece')
            description = request.POST.get('description', '').strip()
            cost_price = request.POST.get('cost_price', '0')
            sale_price = request.POST.get('sale_price', '0')  # Changed from selling_price
            wholesale_price = request.POST.get('wholesale_price', '0')
            tax_rate = request.POST.get('tax_rate', '0')
            min_stock = request.POST.get('min_stock', '0')
            max_stock = request.POST.get('max_stock', '0')
            opening_balance = request.POST.get('opening_balance', '0')
            opening_balance_cost = request.POST.get('opening_balance_cost', '0')
            opening_balance_warehouse_id = request.POST.get('opening_balance_warehouse')
            is_active = request.POST.get('is_active') == 'on' or request.POST.get('is_active', '').lower() == 'true'
            track_stock = request.POST.get('track_stock') == 'on' or request.POST.get('track_stock', '').lower() == 'true'
            is_service = request.POST.get('is_service') == 'on' or request.POST.get('is_service', '').lower() == 'true'
            
            # If is_service checkbox is checked, set product_type to 'service'
            if is_service:
                product_type = 'service'
            
            # التحقق من صحة البيانات الأساسية
            if not name:
                return JsonResponse({
                    'success': False,
                    'error': 'اسم المنتج مطلوب!'
                })
            
            if not sale_price or float(sale_price) <= 0:
                return JsonResponse({
                    'success': False,
                    'error': 'سعر البيع مطلوب ويجب أن يكون أكبر من صفر!'
                })
            
            # التحقق من التصنيف
            if not category_id:
                return JsonResponse({
                    'success': False,
                    'error': 'التصنيف مطلوب!'
                })
            
            # إنشاء رمز تلقائي إذا لم يُدخل
            if not sku:
                # إنشاء رمز تلقائي بناءً على آخر منتج
                last_product = Product.objects.order_by('-id').first()
                if last_product:
                    last_number = int(last_product.code.split('-')[-1]) if '-' in last_product.code else 0
                    sku = f"PROD-{last_number + 1:04d}"
                else:
                    sku = "PROD-0001"
            
            # التحقق من عدم تكرار الرمز
            if Product.objects.filter(code=sku).exists():
                return JsonResponse({
                    'success': False,
                    'error': 'رمز المنتج موجود مسبقاً!'
                })
            
            # التحقق من عدم تكرار الباركود
            if barcode and Product.objects.filter(barcode=barcode).exists():
                return JsonResponse({
                    'success': False,
                    'error': 'الباركود موجود مسبقاً!'
                })
            
            # التحقق من عدم تكرار الرقم التسلسلي
            if serial_number and Product.objects.filter(serial_number=serial_number).exists():
                return JsonResponse({
                    'success': False,
                    'error': 'الرقم التسلسلي موجود مسبقاً!'
                })
            
            # التحقق من صحة الأسعار والنسب
            try:
                # سعر التكلفة يُحسب تلقائياً - نبدأ بصفر
                cost_price = 0
                sale_price = float(sale_price) if sale_price else 0
                wholesale_price = float(wholesale_price) if wholesale_price else 0
                tax_rate = float(tax_rate) if tax_rate else 0
                min_stock = float(min_stock) if min_stock else 0
                max_stock = float(max_stock) if max_stock else 0
                opening_balance = float(opening_balance) if opening_balance else 0
                opening_balance_cost = float(opening_balance_cost) if opening_balance_cost else 0
                
                # التحقق من صحة نسبة الضريبة
                if tax_rate < 0 or tax_rate > 100:
                    return JsonResponse({
                        'success': False,
                        'error': 'نسبة الضريبة يجب أن تكون بين 0 و 100!'
                    })
                
                # التحقق من صحة رصيد بداية المدة
                if opening_balance < 0:
                    return JsonResponse({
                        'success': False,
                        'error': 'رصيد بداية المدة يجب أن يكون صفر أو أكبر!'
                    })
                
                # التحقق من تكلفة الرصيد الافتتاحي إذا كان الرصيد أكبر من صفر
                if opening_balance > 0 and not opening_balance_warehouse_id:
                    return JsonResponse({
                        'success': False,
                        'error': 'مستودع الرصيد الافتتاحي مطلوب عند وجود رصيد افتتاحي!'
                    })
                
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'error': 'يرجى إدخال أسعار ونسبة ضريبة صحيحة!'
                })
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'error': 'يرجى إدخال أسعار ونسبة ضريبة صحيحة!'
                })
            
            # التحقق من صحة نسبة الضريبة
            if tax_rate < 0 or tax_rate > 100:
                return JsonResponse({
                    'success': False,
                    'error': 'نسبة الضريبة يجب أن تكون بين 0 و 100!'
                })
            
            # الحصول على الفئة
            category = None
            if category_id:
                try:
                    category = Category.objects.get(id=category_id)
                except Category.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'error': 'الفئة المحددة غير موجودة!'
                    })
            
            # الحصول على مستودع الرصيد الافتتاحي
            opening_balance_warehouse = None
            if opening_balance_warehouse_id:
                try:
                    opening_balance_warehouse = Warehouse.objects.get(id=opening_balance_warehouse_id, is_active=True)
                except Warehouse.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'error': 'مستودع الرصيد الافتتاحي المحدد غير موجود!'
                    })
            
            # إنشاء المنتج
            product = Product.objects.create(
                code=sku,
                name=name,
                name_en=name_en,
                product_type=product_type,
                barcode=barcode,
                serial_number=serial_number,
                category=category,
                description=description,
                cost_price=cost_price,
                minimum_quantity=min_stock,
                maximum_quantity=max_stock,
                sale_price=sale_price,
                wholesale_price=wholesale_price,
                tax_rate=tax_rate,
                opening_balance_quantity=opening_balance,
                opening_balance_cost=opening_balance_cost,
                opening_balance_warehouse=opening_balance_warehouse,
                is_active=is_active
            )
            
            # إنشاء حركة مخزون للرصيد الافتتاحي إذا كان أكبر من صفر
            if opening_balance > 0:
                try:
                    # استخدام مستودع الرصيد الافتتاحي المحدد
                    unit_cost = opening_balance_cost / opening_balance if opening_balance > 0 else 0
                    InventoryMovement.objects.create(
                        product=product,
                        warehouse=opening_balance_warehouse,
                        movement_type='in',
                        quantity=opening_balance,
                        unit_cost=unit_cost,
                        total_cost=opening_balance_cost,
                        reference_type='opening_balance',
                        reference_id=product.id,
                        notes=f'الرصيد الافتتاحي للمنتج {product.name}',
                        created_by=request.user,
                        date=product.created_at.date()
                    )
                except Exception as e:
                    # تسجيل تحذير في حالة فشل إنشاء حركة المخزون
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"فشل في إنشاء حركة المخزون للرصيد الافتتاحي للمنتج {product.id}: {str(e)}")
            
            # إنشاء القيد المحاسبي للرصيد الافتتاحي إذا كان هناك رصيد افتتاحي
            if opening_balance > 0 and opening_balance_cost > 0:
                try:
                    from journal.models import JournalEntry, JournalLine, Account
                    from core.models import DocumentSequence
                    from django.utils import timezone
                    
                    # البحث عن حساب المخزون (1501) - Current Assets
                    inventory_account = Account.objects.filter(code='1501').first()
                    # البحث عن حساب حقوق الملكية (301) - Equity
                    equity_account = Account.objects.filter(code='301').first()
                    
                    if inventory_account and equity_account:
                        # توليد رقم القيد
                        try:
                            seq = DocumentSequence.objects.get(document_type='journal_entry')
                            entry_number = seq.get_next_number()
                        except DocumentSequence.DoesNotExist:
                            last_entry = JournalEntry.objects.order_by('-id').first()
                            if last_entry and last_entry.entry_number:
                                try:
                                    last_num = int(last_entry.entry_number.split('-')[-1])
                                    entry_number = f'JE-{last_num + 1:06d}'
                                except:
                                    entry_number = f'JE-{timezone.now().strftime("%Y%m%d%H%M%S")}'
                            else:
                                entry_number = f'JE-{timezone.now().strftime("%Y%m%d%H%M%S")}'
                        
                        # إنشاء قيد اليومية (IFRS Compliant)
                        journal_entry = JournalEntry.objects.create(
                            entry_number=entry_number,
                            entry_date=timezone.now().date(),
                            entry_type='daily',
                            reference_type='manual',
                            description=f'رصيد افتتاحي - {product.name} ({product.code})',
                            total_amount=opening_balance_cost,
                            created_by=request.user,
                        )
                        
                        # إنشاء أطراف القيد
                        # من ح/ المخزون (أصل متداول - مدين)
                        JournalLine.objects.create(
                            journal_entry=journal_entry,
                            account=inventory_account,
                            debit=opening_balance_cost,
                            credit=0,
                            line_description=f'رصيد افتتاحي - {product.name}'
                        )
                        
                        # إلى ح/ حقوق الملكية (دائن)
                        JournalLine.objects.create(
                            journal_entry=journal_entry,
                            account=equity_account,
                            debit=0,
                            credit=opening_balance_cost,
                            line_description=f'رصيد افتتاحي - {product.name}'
                        )
                        
                        # تحديث أرصدة الحسابات
                        inventory_account.update_account_balance()
                        equity_account.update_account_balance()
                        
                        # تسجيل النشاط في سجل الأنشطة
                        AuditLog.objects.create(
                            user=request.user,
                            action_type='create',
                            content_type='JournalEntry',
                            object_id=journal_entry.id,
                            description=f'تم إنشاء قيد محاسبي للرصيد الافتتاحي: {journal_entry.entry_number}',
                            ip_address=request.META.get('REMOTE_ADDR')
                        )
                        
                except Exception as e:
                    # تسجيل تحذير في حالة فشل إنشاء القيد المحاسبي
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"فشل في إنشاء القيد المحاسبي للرصيد الافتتاحي للمنتج {product.id}: {str(e)}")
            
            # معالجة رفع الصورة
            if 'image' in request.FILES:
                product.image = request.FILES['image']
                product.save()
            
            # تسجيل النشاط في سجل الأنشطة
            AuditLog.objects.create(
                user=request.user,
                action_type='create',
                content_type='Product',
                object_id=product.id,
                description=f'تم إنشاء المنتج من الشاشة المنبثقة: {product.name} - رمز المنتج: {product.code} - سعر البيع: {product.sale_price}',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            # رسالة نجاح مع تفاصيل الضريبة
            success_message = f'تم إنشاء المنتج "{product.name}" بنجاح!'
            if tax_rate > 0:
                from decimal import Decimal
                sale_price_decimal = Decimal(str(sale_price))
                tax_rate_decimal = Decimal(str(tax_rate))
                tax_amount = sale_price_decimal * (tax_rate_decimal / Decimal('100'))
                price_with_tax = sale_price_decimal + tax_amount
                success_message += f' (سعر البيع: {sale_price:.3f}، الضريبة: {tax_rate}%، السعر شامل الضريبة: {price_with_tax:.3f})'
            
            return JsonResponse({
                'success': True,
                'message': success_message,
                'product': {
                    'id': product.id,
                    'name': product.name,
                    'code': product.code,
                    'sale_price': float(product.sale_price),
                    'category_name': product.category.name if product.category else None,
                    'product_type': product.product_type,
                    'tax_rate': float(product.tax_rate),
                    'is_active': product.is_active
                }
            })
            
        except Exception as e:
            # تسجيل الخطأ في audit log
            AuditLog.objects.create(
                user=request.user,
                action_type='error',
                content_type='Product',
                object_id=None,
                description=f'حدث خطأ أثناء إنشاء المنتج من فاتورة المشتريات: {str(e)}',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"خطأ في إنشاء المنتج: {str(e)}")
            
            return JsonResponse({
                'success': False,
                'error': f'حدث خطأ أثناء إنشاء المنتج: {str(e)}'
            })

class ProductMovementsView(LoginRequiredMixin, ListView):
    model = InventoryMovement
    template_name = 'products/product_movements.html'
    context_object_name = 'movements'
    paginate_by = 50  # عدد مناسب للعرض
    
    def get_queryset(self):
        product_id = self.kwargs.get('pk')
        return InventoryMovement.objects.filter(product_id=product_id).order_by('-date', '-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = get_object_or_404(Product, pk=self.kwargs.get('pk'))
        context['product'] = product
        
        # إحصائيات الحركات
        all_movements = self.get_queryset()
        context['total_movements'] = all_movements.count()
        context['incoming_movements'] = all_movements.filter(movement_type='in').count()
        context['outgoing_movements'] = all_movements.filter(movement_type='out').count()
        context['transfer_movements'] = all_movements.filter(movement_type='transfer').count()
        
        # تسجيل النشاط في سجل الأنشطة
        AuditLog.objects.create(
            user=self.request.user,
            action_type='view',
            content_type='Product Movements',
            object_id=product.id,
            description=f'عرض حركات المنتج: {product.name}',
            ip_address=self.request.META.get('REMOTE_ADDR')
        )
        
        return context


# Linked Units API Endpoints
@csrf_exempt
@login_required
def check_package_conversion(request):
    """
    API endpoint to check if quantity can be converted to package
    Used in sales invoice to suggest package conversion
    """
    if request.method == 'POST':
        try:
            import json
            from decimal import Decimal
            
            data = json.loads(request.body)
            product_id = data.get('product_id')
            quantity = data.get('quantity', 0)
            
            if not product_id:
                return JsonResponse({
                    'success': False,
                    'error': _('Product ID is required')
                })
            
            product = Product.objects.get(id=product_id, is_active=True)
            
            # Check if this is a single unit product
            if product.unit_type != 'single':
                return JsonResponse({
                    'success': True,
                    'can_convert': False,
                    'message': _('This product is not a single unit')
                })
            
            # Get conversion suggestion
            suggestion = product.suggest_package_conversion(quantity)
            
            if suggestion:
                return JsonResponse({
                    'success': True,
                    'can_convert': True,
                    'suggestion': {
                        'single_product_id': suggestion['single_product'].id,
                        'single_product_name': suggestion['single_product'].name,
                        'package_product_id': suggestion['package_product'].id,
                        'package_product_name': suggestion['package_product'].name,
                        'quantity_singles': float(suggestion['quantity_singles']),
                        'conversion_factor': float(suggestion['conversion_factor']),
                        'packages': float(suggestion['packages']),
                        'remaining_singles': float(suggestion['remaining_singles']),
                        'single_unit_price': float(suggestion['single_unit_price']),
                        'package_unit_price': float(suggestion['package_unit_price']),
                        'total_as_singles': float(suggestion['total_as_singles']),
                        'total_as_packages': float(suggestion['total_as_packages'])
                    }
                })
            else:
                return JsonResponse({
                    'success': True,
                    'can_convert': False,
                    'message': _('Quantity does not reach package size')
                })
                
        except Product.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': _('Product not found')
            })
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in check_package_conversion: {str(e)}")
            
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({
        'success': False,
        'error': _('Invalid request method')
    })


@csrf_exempt
@login_required
def get_linked_products(request, product_id):
    """
    API endpoint to get linked products (single and package)
    """
    try:
        product = Product.objects.get(id=product_id, is_active=True)
        
        result = {
            'success': True,
            'product': {
                'id': product.id,
                'name': product.name,
                'code': product.code,
                'unit_type': product.unit_type,
                'sale_price': float(product.sale_price)
            }
        }
        
        if product.unit_type == 'single':
            package = product.get_linked_package_unit()
            if package:
                result['linked_package'] = {
                    'id': package.id,
                    'name': package.name,
                    'code': package.code,
                    'sale_price': float(package.sale_price),
                    'conversion_factor': float(package.conversion_factor)
                }
        elif product.unit_type == 'package':
            single = product.get_linked_single_unit()
            if single:
                result['linked_single'] = {
                    'id': single.id,
                    'name': single.name,
                    'code': single.code,
                    'sale_price': float(single.sale_price)
                }
                result['conversion_factor'] = float(product.conversion_factor)
        
        return JsonResponse(result)
        
    except Product.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': _('Product not found')
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })
