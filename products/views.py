from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView, View
from django.db.models import Q
from django.http import JsonResponse
from django.contrib import messages
from django.urls import reverse_lazy
from .models import Category, Product

# Category Views
class CategoryListView(LoginRequiredMixin, TemplateView):
    template_name = 'products/category_list.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        categories = Category.objects.all()
        context['categories'] = categories
        context['total_categories'] = categories.count()
        context['active_categories'] = categories.filter(is_active=True).count()
        context['inactive_categories'] = categories.filter(is_active=False).count()
        return context

class CategoryCreateView(LoginRequiredMixin, View):
    template_name = 'products/category_add.html'
    
    def get(self, request, *args, **kwargs):
        context = {
            'categories': Category.objects.filter(parent__isnull=True)  # فقط الفئات الرئيسية
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
            
            # التحقق من صحة البيانات
            if not name:
                messages.error(request, 'اسم التصنيف مطلوب!')
                return self.get(request)
            
            # التحقق من عدم تكرار الرمز
            if code and Category.objects.filter(name=code).exists():
                messages.error(request, 'رمز التصنيف موجود مسبقاً!')
                return self.get(request)
            
            # معالجة التصنيف الأب
            parent = None
            if parent_id:
                try:
                    parent = Category.objects.get(id=parent_id)
                except Category.DoesNotExist:
                    parent = None
            
            # إنشاء التصنيف
            category = Category.objects.create(
                name=name,
                parent=parent,
                description=description,
                is_active=is_active
            )
            
            messages.success(request, f'تم إنشاء التصنيف "{category.name}" بنجاح!')
            return redirect('products:category_list')
            
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء إنشاء التصنيف: {str(e)}')
            return self.get(request)

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
            
            # التحقق من صحة البيانات
            if not name:
                messages.error(request, 'اسم التصنيف مطلوب!')
                return self.get(request, pk)
            
            # معالجة التصنيف الأب
            parent = None
            if parent_id:
                try:
                    parent = Category.objects.get(id=parent_id)
                    # التأكد من عدم جعل التصنيف أب لنفسه
                    if parent.id == category.id:
                        messages.error(request, 'لا يمكن جعل التصنيف أب لنفسه!')
                        return self.get(request, pk)
                except Category.DoesNotExist:
                    parent = None
            
            # تحديث التصنيف
            category.name = name
            category.parent = parent
            category.description = description
            category.is_active = is_active
            category.save()
            
            messages.success(request, f'تم تحديث التصنيف "{category.name}" بنجاح!')
            return redirect('products:category_list')
            
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء تحديث التصنيف: {str(e)}')
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
                    f'لا يمكن حذف التصنيف "{category_name}" لوجود {products_count} منتج مرتبط به! '
                    f'يجب حذف أو نقل المنتجات أولاً.'
                )
                return redirect('products:category_list')
            
            # التحقق من وجود فئات فرعية
            subcategories_count = Category.objects.filter(parent=category).count()
            if subcategories_count > 0:
                messages.error(
                    request, 
                    f'لا يمكن حذف التصنيف "{category_name}" لوجود {subcategories_count} تصنيف فرعي! '
                    f'يجب حذف أو نقل التصنيفات الفرعية أولاً.'
                )
                return redirect('products:category_list')
            
            # حذف التصنيف
            category.delete()
            messages.success(request, f'تم حذف التصنيف "{category_name}" بنجاح!')
            
        except Category.DoesNotExist:
            messages.error(request, 'التصنيف المحدد غير موجود!')
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء حذف التصنيف: {str(e)}')
        
        return redirect('products:category_list')

# Product Views
class ProductListView(LoginRequiredMixin, ListView):
    model = Product
    template_name = 'products/product_list.html'
    context_object_name = 'products'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Product.objects.all().select_related('category').order_by('-created_at')
        
        # الحصول على معاملات البحث
        search_query = self.request.GET.get('search', '')
        category_filter = self.request.GET.get('category', '')
        
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
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # إضافة إحصائيات
        all_products = Product.objects.all()
        context['total_products'] = all_products.count()
        context['active_products'] = all_products.filter(is_active=True).count()
        context['inactive_products'] = all_products.filter(is_active=False).count()
        
        # إضافة التصنيفات للفلترة
        context['categories'] = Category.objects.filter(is_active=True).order_by('name')
        
        # إضافة معاملات البحث
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_category'] = self.request.GET.get('category', '')
        
        return context

class ProductCreateView(LoginRequiredMixin, View):
    template_name = 'products/product_add.html'
    
    def get(self, request, *args, **kwargs):
        context = {
            'categories': Category.objects.filter(is_active=True)
        }
        return render(request, self.template_name, context)
    
    def post(self, request, *args, **kwargs):
        try:
            # استلام البيانات من النموذج
            name = request.POST.get('name', '').strip()
            name_en = request.POST.get('name_en', '').strip()
            sku = request.POST.get('sku', '').strip()
            barcode = request.POST.get('barcode', '').strip()
            serial_number = request.POST.get('serial_number', '').strip()
            category_id = request.POST.get('category', '')
            unit = request.POST.get('unit', 'piece')
            cost_price = request.POST.get('cost_price', '0')
            selling_price = request.POST.get('selling_price', '0')
            wholesale_price = request.POST.get('wholesale_price', '0')
            tax_rate = request.POST.get('tax_rate', '0')
            current_stock = request.POST.get('current_stock', '0')
            min_stock = request.POST.get('min_stock', '0')
            max_stock = request.POST.get('max_stock', '0')
            description = request.POST.get('description', '').strip()
            is_active = request.POST.get('is_active') == 'on'
            track_stock = request.POST.get('track_stock') == 'on'
            
            # التحقق من صحة البيانات
            if not name:
                messages.error(request, 'اسم المنتج مطلوب!')
                return self.get(request)
            
            if not selling_price or float(selling_price) <= 0:
                messages.error(request, 'سعر البيع مطلوب ويجب أن يكون أكبر من صفر!')
                return self.get(request)
            
            # التحقق من التصنيف
            if not category_id:
                messages.error(request, 'التصنيف مطلوب!')
                return self.get(request)
            
            try:
                category = Category.objects.get(id=category_id)
            except Category.DoesNotExist:
                messages.error(request, 'التصنيف المحدد غير موجود!')
                return self.get(request)
            
            # التحقق من عدم تكرار رمز المنتج
            if sku and Product.objects.filter(code=sku).exists():
                messages.error(request, 'رمز المنتج موجود مسبقاً!')
                return self.get(request)
            
            # التحقق من عدم تكرار الباركود
            if barcode and Product.objects.filter(barcode=barcode).exists():
                messages.error(request, 'الباركود موجود مسبقاً!')
                return self.get(request)
            
            # التحقق من عدم تكرار الرقم التسلسلي
            if serial_number and Product.objects.filter(serial_number=serial_number).exists():
                messages.error(request, 'الرقم التسلسلي موجود مسبقاً!')
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
                cost_price = float(cost_price) if cost_price else 0
                selling_price = float(selling_price)
                wholesale_price = float(wholesale_price) if wholesale_price else 0
                tax_rate = float(tax_rate) if tax_rate else 0
                
                # التحقق من صحة نسبة الضريبة
                if tax_rate < 0 or tax_rate > 100:
                    messages.error(request, 'نسبة الضريبة يجب أن تكون بين 0 و 100!')
                    return self.get(request)
                    
            except ValueError:
                messages.error(request, 'يرجى إدخال أسعار ونسبة ضريبة صحيحة!')
                return self.get(request)
            
            # إنشاء المنتج
            product = Product.objects.create(
                code=sku,
                name=name,
                name_en=name_en,  # إضافة الاسم بالإنجليزية
                barcode=barcode,  # إضافة الباركود
                serial_number=serial_number,  # إضافة الرقم التسلسلي
                category=category,
                description=description,
                minimum_quantity=float(min_stock) if min_stock else 0,
                sale_price=selling_price,
                wholesale_price=wholesale_price,  # إضافة سعر الجملة
                tax_rate=tax_rate,
                is_active=is_active
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
            
            messages.success(request, success_message)
            return redirect('products:product_list')
            
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء إنشاء المنتج: {str(e)}')
            return self.get(request)

class ProductUpdateView(LoginRequiredMixin, View):
    template_name = 'products/product_edit.html'
    
    def get(self, request, pk, *args, **kwargs):
        product = get_object_or_404(Product, pk=pk)
        context = {
            'product': product,
            'categories': Category.objects.filter(is_active=True)
        }
        return render(request, self.template_name, context)
    
    def post(self, request, pk, *args, **kwargs):
        try:
            product = get_object_or_404(Product, pk=pk)
            
            # استلام جميع البيانات من النموذج
            name = request.POST.get('name', '').strip()
            name_en = request.POST.get('name_en', '').strip()
            barcode = request.POST.get('barcode', '').strip()
            serial_number = request.POST.get('serial_number', '').strip()
            category_id = request.POST.get('category', '')
            cost_price = request.POST.get('cost_price', '0')
            selling_price = request.POST.get('selling_price', '0')
            wholesale_price = request.POST.get('wholesale_price', '0')
            tax_rate = request.POST.get('tax_rate', '0')
            description = request.POST.get('description', '').strip()
            is_active = request.POST.get('is_active') == 'on'
            
            # التحقق من صحة البيانات
            if not name:
                messages.error(request, 'اسم المنتج مطلوب!')
                return self.get(request, pk)
            
            if not selling_price or float(selling_price) <= 0:
                messages.error(request, 'سعر البيع مطلوب ويجب أن يكون أكبر من صفر!')
                return self.get(request, pk)
            
            # التحقق من التصنيف
            if category_id:
                try:
                    category = Category.objects.get(id=category_id)
                    product.category = category
                except Category.DoesNotExist:
                    messages.error(request, 'التصنيف المحدد غير موجود!')
                    return self.get(request, pk)
            
            # التحقق من عدم تكرار الباركود
            if barcode and Product.objects.filter(barcode=barcode).exclude(pk=pk).exists():
                messages.error(request, 'الباركود موجود مسبقاً!')
                return self.get(request, pk)
            
            # التحقق من عدم تكرار الرقم التسلسلي
            if serial_number and Product.objects.filter(serial_number=serial_number).exclude(pk=pk).exists():
                messages.error(request, 'الرقم التسلسلي موجود مسبقاً!')
                return self.get(request, pk)
            
            # تحويل الأسعار إلى أرقام
            try:
                cost_price = float(cost_price) if cost_price else 0
                selling_price = float(selling_price)
                wholesale_price = float(wholesale_price) if wholesale_price else 0
                tax_rate = float(tax_rate) if tax_rate else 0
                
                # التحقق من صحة نسبة الضريبة
                if tax_rate < 0 or tax_rate > 100:
                    messages.error(request, 'نسبة الضريبة يجب أن تكون بين 0 و 100!')
                    return self.get(request, pk)
                    
            except ValueError:
                messages.error(request, 'يرجى إدخال أسعار ونسبة ضريبة صحيحة!')
                return self.get(request, pk)
            
            # تحديث جميع حقول المنتج
            product.name = name
            product.name_en = name_en
            product.barcode = barcode
            product.serial_number = serial_number
            product.description = description
            product.cost_price = cost_price
            product.sale_price = selling_price
            product.wholesale_price = wholesale_price
            product.tax_rate = tax_rate
            product.is_active = is_active
            product.save()
            
            # رسالة نجاح مع تفاصيل الضريبة
            success_message = f'تم تحديث المنتج "{product.name}" بنجاح!'
            if tax_rate > 0:
                from decimal import Decimal
                sale_price_decimal = Decimal(str(product.sale_price))
                tax_rate_decimal = Decimal(str(tax_rate))
                tax_amount = sale_price_decimal * (tax_rate_decimal / Decimal('100'))
                price_with_tax = sale_price_decimal + tax_amount
                success_message += f' (السعر شامل الضريبة: {price_with_tax:.3f})'
            
            messages.success(request, success_message)
            return redirect('products:product_list')
            
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء تحديث المنتج: {str(e)}')
            return self.get(request, pk)

class ProductDeleteView(LoginRequiredMixin, View):
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
            
            # التحقق من الارتباطات قبل الحذف
            related_data = self._check_product_relations(product)
            
            if any(related_data.values()):
                # إذا كان هناك ارتباطات، عرض رسالة مفصلة
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
            
            # إذا لم تكن هناك ارتباطات، احذف المنتج
            product.delete()
            messages.success(request, f'تم حذف المنتج "{product_name}" بنجاح!')
            
        except Exception as e:
            # معالجة أخطاء أخرى غير متوقعة
            messages.error(request, f'حدث خطأ غير متوقع أثناء حذف المنتج: {str(e)}')
        
        return redirect('products:product_list')
    
    def _check_product_relations(self, product):
        """فحص جميع الارتباطات المحمية للمنتج"""
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
            from sales.models import SaleInvoiceItem
            sale_items = SaleInvoiceItem.objects.filter(product=product)
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
        
        return context

def product_search_api(request):
    return JsonResponse({'products': []})

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
            sort_order = request.POST.get('sort_order', '0')
            is_active = request.POST.get('is_active') == 'on'
            
            # التحقق من صحة البيانات
            if not name:
                return JsonResponse({
                    'success': False,
                    'error': 'اسم التصنيف مطلوب!'
                })
            
            # التحقق من عدم تكرار الرمز
            if code and Category.objects.filter(name=code).exists():
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
                sort_order=int(sort_order) if sort_order else 0,
                is_active=is_active
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
            sku = request.POST.get('sku', '').strip()
            barcode = request.POST.get('barcode', '').strip()
            serial_number = request.POST.get('serial_number', '').strip()
            category_id = request.POST.get('category', '')
            unit = request.POST.get('unit', 'piece')
            cost_price = request.POST.get('cost_price', '0')
            selling_price = request.POST.get('selling_price', '0')
            wholesale_price = request.POST.get('wholesale_price', '0')
            tax_rate = request.POST.get('tax_rate', '0')
            current_stock = request.POST.get('current_stock', '0')
            min_stock = request.POST.get('min_stock', '0')
            max_stock = request.POST.get('max_stock', '0')
            description = request.POST.get('description', '').strip()
            is_active = request.POST.get('is_active') == 'on'
            track_stock = request.POST.get('track_stock') == 'on'
            
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
            category = None
            if category_id:
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
                
                # التحقق من صحة نسبة الضريبة
                if tax_rate < 0 or tax_rate > 100:
                    return JsonResponse({
                        'success': False,
                        'error': 'نسبة الضريبة يجب أن تكون بين 0 و 100!'
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
                barcode=barcode,
                serial_number=serial_number,
                category=category,
                description=description,
                minimum_quantity=float(min_stock) if min_stock else 0,
                sale_price=selling_price,
                wholesale_price=wholesale_price,
                tax_rate=tax_rate,
                is_active=is_active
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
                    'is_active': product.is_active
                }
            })
            
        except Exception as e:
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
