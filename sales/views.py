from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, TemplateView
from django.http import HttpResponse, JsonResponse
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.db import transaction, IntegrityError
from django.utils import timezone
from decimal import Decimal, ROUND_HALF_UP
from datetime import date, datetime
from .models import SalesInvoice, SalesInvoiceItem, SalesReturn
from .models import SalesCreditNote
from products.models import Product
from customers.models import CustomerSupplier
from settings.models import CompanySettings, Currency
from core.models import DocumentSequence
from accounts.services import create_sales_invoice_transaction, create_sales_return_transaction, delete_transaction_by_reference
from journal.services import JournalService
import json
import logging
from django.utils.translation import gettext_lazy as _


def create_sales_invoice_journal_entry(invoice, user):
    """إنشاء قيد محاسبي لفاتورة المبيعات"""
    try:
        # إنشاء القيد المحاسبي باستخدام JournalService
        JournalService.create_sales_invoice_entry(invoice, user)
    except Exception as e:
        print(f"خطأ في إنشاء القيد المحاسبي لفاتورة المبيعات: {e}")
        # لا نوقف العملية في حالة فشل إنشاء القيد المحاسبي
        pass

def create_sales_return_journal_entry(sales_return, user):
    """إنشاء قيد محاسبي لمردود المبيعات"""
    try:
        # إنشاء القيد المحاسبي باستخدام JournalService
        JournalService.create_sales_return_entry(sales_return, user)
    except Exception as e:
        print(f"خطأ في إنشاء القيد المحاسبي لمردود المبيعات: {e}")
        # لا نوقف العملية في حالة فشل إنشاء القيد المحاسبي
        pass


def create_sales_invoice_account_transaction(invoice, user):
    """إنشاء حركة حساب للعميل عند إنشاء فاتورة مبيعات"""
    try:
        from accounts.models import AccountTransaction
        import uuid
        
        # إذا كانت طريقة الدفع ليست نقداً، نسجل حركة في حساب العميل
        if invoice.payment_type != 'cash' and invoice.customer:
            # توليد رقم الحركة
            transaction_number = f"SALE-{uuid.uuid4().hex[:8].upper()}"
            
            # حساب الرصيد السابق
            last_transaction = AccountTransaction.objects.filter(
                customer_supplier=invoice.customer
            ).order_by('-created_at').first()
            
            previous_balance = last_transaction.balance_after if last_transaction else Decimal('0')
            
            # إنشاء حركة مدينة للعميل (زيادة الذمم المدينة)
            new_balance = previous_balance + invoice.total_amount
            
            AccountTransaction.objects.create(
                transaction_number=transaction_number,
                date=invoice.date,
                customer_supplier=invoice.customer,
                transaction_type='sales_invoice',
                direction='debit',
                amount=invoice.total_amount,
                reference_type='sales_invoice',
                reference_id=invoice.id,
                description=f'مبيعات - فاتورة رقم {invoice.invoice_number}',
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


def create_sales_return_account_transaction(return_invoice, user):
    """إنشاء حركة حساب للعميل عند إنشاء مردود مبيعات"""
    try:
        from accounts.models import AccountTransaction
        import uuid
        
        # إذا كان هناك عميل، نسجل حركة دائنة (تقليل الذمم المدينة)
        if return_invoice.customer:
            # توليد رقم الحركة
            transaction_number = f"SRET-{uuid.uuid4().hex[:8].upper()}"
            
            # حساب الرصيد السابق
            last_transaction = AccountTransaction.objects.filter(
                customer_supplier=return_invoice.customer
            ).order_by('-created_at').first()
            
            previous_balance = last_transaction.balance_after if last_transaction else Decimal('0')
            
            # إنشاء حركة دائنة للعميل (تقليل الذمم المدينة)
            new_balance = previous_balance - return_invoice.total_amount
            
            AccountTransaction.objects.create(
                transaction_number=transaction_number,
                date=return_invoice.date,
                customer_supplier=return_invoice.customer,
                transaction_type='sales_return',
                direction='credit',
                amount=return_invoice.total_amount,
                reference_type='sales_return',
                reference_id=return_invoice.id,
                description=f'مردود مبيعات - فاتورة رقم {return_invoice.return_number}',
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


def create_sales_return_inventory_movements(return_invoice, user):
    """إنشاء حركات مخزون لمردود المبيعات"""
    try:
        from inventory.models import InventoryMovement, Warehouse
        import uuid
        
        # الحصول على المستودع الافتراضي
        default_warehouse = Warehouse.objects.filter(is_active=True).first()
        if not default_warehouse:
            # إنشاء مستودع افتراضي إذا لم يكن موجوداً
            default_warehouse = Warehouse.objects.create(
                name='المستودع الرئيسي',
                code='MAIN',
                is_active=True
            )
        
        # إنشاء حركة مخزون واردة لكل عنصر في المردود
        for item in return_invoice.items.all():
            # توليد رقم الحركة
            movement_number = f"RETURN-IN-{uuid.uuid4().hex[:8].upper()}"
            
            InventoryMovement.objects.create(
                movement_number=movement_number,
                date=return_invoice.date,
                product=item.product,
                warehouse=default_warehouse,
                movement_type='in',
                reference_type='sales_return',
                reference_id=return_invoice.id,
                quantity=item.quantity,
                unit_cost=item.unit_price,
                notes=f'مردود مبيعات - رقم {return_invoice.return_number}',
                created_by=user
            )
            
    except ImportError:
        # في حالة عدم وجود نموذج المخزون
        pass
    except Exception as e:
        print(f"خطأ في إنشاء حركة المخزون: {e}")
        # لا نوقف العملية في حالة فشل تسجيل الحركة المخزونية
        pass


class SalesInvoiceListView(LoginRequiredMixin, ListView):
    model = SalesInvoice
    template_name = 'sales/invoice_list.html'
    context_object_name = 'invoices'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = SalesInvoice.objects.all()
        
        # Search functionality
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(invoice_number__icontains=search) |
                Q(customer__name__icontains=search)
            )
        
        # Date filter
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
        
        # Payment type filter
        payment_type = self.request.GET.get('payment_type')
        if payment_type:
            queryset = queryset.filter(payment_type=payment_type)
        
        return queryset.select_related('customer', 'created_by')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Statistics
        invoices = SalesInvoice.objects.all()
        context['total_invoices'] = invoices.count()
        context['paid_invoices'] = invoices.filter(payment_type='cash').count()
        context['pending_invoices'] = invoices.filter(payment_type='credit').count()
        context['total_sales_amount'] = invoices.aggregate(
            total=Sum('total_amount')
        )['total'] or 0
        
        # Currency and company settings
        try:
            company_settings = CompanySettings.objects.first()
            if company_settings and company_settings.base_currency:
                context['base_currency'] = company_settings.base_currency
            else:
                context['base_currency'] = Currency.objects.filter(is_active=True).first()
        except:
            pass
        
        context['active_currencies'] = Currency.objects.filter(is_active=True)
        
        return context


@login_required
def sales_invoice_create(request):
    """إنشاء فاتورة مبيعات جديدة"""
    if request.method == 'POST':
        try:
            # helper to robustly parse decimals from various client locales (commas, arabic separators, spaces)
            def parse_decimal_input(val, name='value', default=Decimal('0')):
                try:
                    if val is None or val == '':
                        return default
                    s = str(val).strip()
                    # Arabic decimal separators and common comma thousands
                    s = s.replace('\u066b', '.')  # Arabic decimal separator if present
                    s = s.replace('\u066c', ',')  # Arabic thousands separator if present
                    # Replace comma with dot for decimal point, remove spaces
                    s = s.replace(',', '.')
                    s = s.replace(' ', '')
                    return Decimal(s)
                except Exception:
                    # Log parsing error in AuditLog for visibility
                    try:
                        from core.signals import log_user_activity
                        dummy = SalesInvoice()
                        log_user_activity(request, 'error', dummy, _('فشل تحليل قيمة رقمية للحقل %(name)s: %(val)s') % {'name': name, 'val': val})
                    except Exception:
                        pass
                    return default
            # سنحاول عدة مرات لتجنب تعارض الأرقام في حال السباق
            max_attempts = 5
            attempt = 0
            allow_manual = True
            while attempt < max_attempts:
                attempt += 1
                try:
                    with transaction.atomic():
                        # معالجة بيانات الفاتورة الأساسية
                        user = request.user
                        customer_id = request.POST.get('customer')
                        payment_type = request.POST.get('payment_type')
                        notes = request.POST.get('notes', '')
                        discount_amount = Decimal(request.POST.get('discount', '0'))

                        # التحقق من صلاحية تعديل رقم الفاتورة
                        manual_invoice = request.POST.get('invoice_number') if allow_manual else None
                        if manual_invoice and (user.is_superuser or user.is_staff or user.has_perm('sales.change_salesinvoice_number')):
                            invoice_number = manual_invoice
                        else:
                            invoice_number = None

                        # توليد رقم الفاتورة إذا لم يكن محدد
                        if not invoice_number:
                            try:
                                sequence = DocumentSequence.objects.get(document_type='sales_invoice')
                                invoice_number = sequence.get_next_number()
                            except DocumentSequence.DoesNotExist:
                                # توليد بديل إذا لم يوجد تسلسل
                                last_invoice = SalesInvoice.objects.order_by('-id').first()
                                if last_invoice:
                                    number = int(last_invoice.invoice_number.split('-')[-1]) + 1 if '-' in last_invoice.invoice_number else int(last_invoice.invoice_number) + 1
                                else:
                                    number = 1
                                invoice_number = f"SALES-{number:06d}"

                        # التحقق من صلاحية تعديل التاريخ
                        if user.is_superuser or user.is_staff or user.has_perm('sales.change_salesinvoice_date'):
                            invoice_date = request.POST.get('date', date.today())
                        else:
                            invoice_date = date.today()

                        # التحقق من البيانات المطلوبة
                        if not customer_id or not payment_type:
                            # سجل محاولة فاشلة في سجل النشاط لتتبع أخطاء الإدخال
                            try:
                                from core.signals import log_user_activity
                                dummy = SalesInvoice()
                                log_user_activity(
                                    request,
                                    'error',
                                    dummy,
                                    _('فشل إنشاء فاتورة: الحقول المطلوبة مفقودة (العميل أو طريقة الدفع)')
                                )
                            except Exception:
                                pass

                            messages.error(request, _('يرجى تعبئة جميع الحقول المطلوبة'))
                            return redirect('sales:invoice_add')

                        customer = get_object_or_404(CustomerSupplier, id=customer_id)

                        # معالجة بيانات المنتجات
                        products = request.POST.getlist('products[]')
                        quantities = request.POST.getlist('quantities[]')
                        prices = request.POST.getlist('prices[]')
                        tax_rates = request.POST.getlist('tax_rates[]')
                        tax_amounts = request.POST.getlist('tax_amounts[]')

                        # التحقق من وجود منتجات
                        if not products or not any(p for p in products if p):
                            # سجل محاولة فاشلة في سجل النشاط لتتبع أخطاء الإدخال
                            try:
                                from core.signals import log_user_activity
                                dummy = SalesInvoice()
                                log_user_activity(
                                    request,
                                    'error',
                                    dummy,
                                    _('فشل إنشاء فاتورة: لا توجد عناصر مضافة')
                                )
                            except Exception:
                                pass

                            messages.error(request, _('يرجى إضافة منتج واحد على الأقل'))
                            return redirect('sales:invoice_add')

                        # حساب المجاميع
                        subtotal = Decimal('0')
                        total_tax_amount = Decimal('0')

                        # إنشاء الفاتورة
                        # determine inclusive_tax flag: default True; if user has permission, use presence of checkbox
                        if user.is_superuser or user.has_perm('sales.can_toggle_invoice_tax'):
                            inclusive_tax_flag = 'inclusive_tax' in request.POST
                        else:
                            inclusive_tax_flag = True

                        invoice = SalesInvoice.objects.create(
                            invoice_number=invoice_number,
                            date=invoice_date,
                            customer=customer,
                            payment_type=payment_type,
                            discount_amount=discount_amount,
                            notes=notes,
                            created_by=user,
                            inclusive_tax=inclusive_tax_flag,
                            subtotal=0,  # سيتم تحديثها لاحقاً
                            tax_amount=0,  # سيتم تحديثها لاحقاً
                            total_amount=0  # سيتم تحديثها لاحقاً
                        )

                        # إذا كان المستخدم له صلاحية تغيير منشئ الفاتورة، تحقق من وجود حقل creator_user_id
                        try:
                            if user.is_superuser or user.has_perm('sales.can_change_invoice_creator'):
                                creator_user_id = request.POST.get('creator_user')
                                if creator_user_id:
                                    from django.contrib.auth import get_user_model
                                    U = get_user_model()
                                    try:
                                        chosen = U.objects.get(id=creator_user_id)
                                        invoice.created_by = chosen
                                        invoice.save()

                                        # سجل التغيير في السجل
                                        from core.signals import log_user_activity
                                        log_user_activity(
                                            request,
                                            'update',
                                            invoice,
                                            _('تم تغيير منشئ الفاتورة إلى %(name)s على يد %(user)s') % {
                                                'name': f"{chosen.first_name or ''} {chosen.last_name or chosen.username}",
                                                'user': user.username
                                            }
                                        )
                                    except Exception:
                                        pass
                        except Exception:
                            pass

                        # إضافة عناصر الفاتورة
                        for i, product_id in enumerate(products):
                            if product_id and i < len(quantities) and i < len(prices):
                                try:
                                    product = Product.objects.get(id=product_id)
                                    # parse quantity/price/tax robustly to accept '1.5' or '1,5' etc.
                                    quantity = parse_decimal_input(quantities[i], name='quantity', default=Decimal('0'))
                                    unit_price = parse_decimal_input(prices[i], name='price', default=Decimal('0'))
                                    tax_rate = parse_decimal_input(tax_rates[i], name='tax_rate', default=Decimal('0')) if i < len(tax_rates) and tax_rates[i] else Decimal('0')

                                    # Safeguard: if submitted unit_price differs from product.sale_price
                                    # and appears to be a cost/last-purchase/zero value, prefer product.sale_price
                                    try:
                                        submitted_price = unit_price
                                        product_sale = Decimal(str(product.sale_price))
                                        product_cost = Decimal(str(product.cost_price)) if product.cost_price is not None else None
                                        last_purchase = Decimal(str(product.get_last_purchase_price() or 0))

                                        # If submitted price is 0 or equals cost or equals last purchase price
                                        # but differs from the official sale price, correct it to sale_price.
                                        suspicious = False
                                        if submitted_price == 0:
                                            suspicious = True
                                        elif product_cost is not None and submitted_price == product_cost and submitted_price != product_sale:
                                            suspicious = True
                                        elif last_purchase is not None and submitted_price == last_purchase and submitted_price != product_sale:
                                            suspicious = True

                                        if suspicious and submitted_price != product_sale:
                                            # Log this correction to the AuditLog (via helper)
                                            try:
                                                from core.signals import log_user_activity
                                                # create a small description with field change
                                                desc = _('تغيير سعر الوحدة لمنتج %(code)s أثناء إنشاء الفاتورة: من %(old)s إلى سعر البيع الرسمي %(new)s') % {
                                                    'code': product.code,
                                                    'old': str(submitted_price),
                                                    'new': str(product_sale)
                                                }
                                                # attach note to invoice instance for logging context
                                                log_user_activity(request, 'update', product, desc)
                                            except Exception:
                                                pass

                                            # enforce sale price
                                            unit_price = product_sale
                                    except Exception:
                                        # if any error in price checks, proceed with submitted price
                                        pass

                                    # حساب مبلغ الضريبة لهذا السطر
                                    line_subtotal = quantity * unit_price
                                    line_tax_amount = line_subtotal * (tax_rate / Decimal('100'))
                                    line_total = line_subtotal + line_tax_amount

                                    # إنشاء عنصر الفاتورة
                                    SalesInvoiceItem.objects.create(
                                        invoice=invoice,
                                        product=product,
                                        quantity=quantity,
                                        unit_price=unit_price,
                                        tax_rate=tax_rate,
                                        tax_amount=line_tax_amount.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP),
                                        total_amount=line_total.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
                                    )

                                    # إنشاء حركة مخزون صادرة للمبيعات
                                    try:
                                        from inventory.models import InventoryMovement, Warehouse
                                        import uuid

                                        # الحصول على المستودع الافتراضي
                                        default_warehouse = Warehouse.objects.filter(is_active=True).first()
                                        if not default_warehouse:
                                            # إنشاء مستودع افتراضي إذا لم يكن موجوداً
                                            default_warehouse = Warehouse.objects.create(
                                                name='المستودع الرئيسي',
                                                code='MAIN',
                                                is_active=True
                                            )

                                        # توليد رقم الحركة
                                        movement_number = f"SALE-OUT-{uuid.uuid4().hex[:8].upper()}"

                                        InventoryMovement.objects.create(
                                            movement_number=movement_number,
                                            date=invoice_date,
                                            product=product,
                                            warehouse=default_warehouse,
                                            movement_type='out',
                                            reference_type='sales_invoice',
                                            reference_id=invoice.id,
                                            quantity=quantity,
                                            unit_cost=unit_price,
                                            notes=f'مبيعات - فاتورة رقم {invoice.invoice_number}',
                                            created_by=user
                                        )
                                    except ImportError:
                                        # في حالة عدم وجود نموذج المخزون
                                        pass
                                    except Exception as inventory_error:
                                        # في حالة حدوث خطأ في المخزون، لا نوقف إنشاء الفاتورة
                                        print(f"خطأ في إنشاء حركة المخزون: {inventory_error}")
                                        pass

                                    # إضافة إلى المجاميع
                                    subtotal += line_subtotal
                                    total_tax_amount += line_tax_amount

                                except (Product.DoesNotExist, ValueError, TypeError):
                                    continue

                        # تحديث مجاميع الفاتورة
                        invoice.subtotal = subtotal.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
                        # if invoice.inclusive_tax is False and user had permission to unset it, zero tax amounts
                        if invoice.inclusive_tax:
                            invoice.tax_amount = total_tax_amount.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
                            invoice.total_amount = (subtotal + total_tax_amount - discount_amount).quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
                        else:
                            invoice.tax_amount = Decimal('0').quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
                            invoice.total_amount = (subtotal - discount_amount).quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
                        invoice.save()

                        # إذا تم إدخال رقم يدوي يطابق البادئة، نقوم بدفع عداد التسلسل للأمام لتجنب التكرار لاحقاً
                        try:
                            if manual_invoice:
                                seq = DocumentSequence.objects.get(document_type='sales_invoice')
                                if manual_invoice.startswith(seq.prefix):
                                    tail = manual_invoice[len(seq.prefix):]
                                    if tail.isdigit():
                                        seq.advance_to_at_least(int(tail))
                        except Exception:
                            pass

                        # إنشاء حركة حساب للعميل
                        create_sales_invoice_account_transaction(invoice, request.user)

                        # إنشاء القيد المحاسبي
                        create_sales_invoice_journal_entry(invoice, request.user)

                        # تسجيل نشاط صريح لإنشاء الفاتورة (بالإضافة للإشارات العامة)
                        try:
                            from core.signals import log_user_activity
                            log_user_activity(
                                request,
                                'create',
                                invoice,
                                _('إنشاء فاتورة مبيعات رقم %(number)s') % {'number': invoice.invoice_number}
                            )
                        except Exception:
                            pass

                        # Log inclusive_tax value if the user had permission to toggle it (include both checked and unchecked)
                        try:
                            if user.is_superuser or user.has_perm('sales.can_toggle_invoice_tax'):
                                from core.signals import log_user_activity
                                log_user_activity(
                                    request,
                                    'update',
                                    invoice,
                                    _('تعيين خيار شامل ضريبة: %(value)s لفاتورة %(number)s') % {
                                        'value': str(invoice.inclusive_tax), 'number': invoice.invoice_number
                                    }
                                )
                        except Exception:
                            pass

                        messages.success(
                            request,
                            _('تم إنشاء فاتورة المبيعات رقم %(number)s بنجاح') % {'number': invoice.invoice_number}
                        )
                        return redirect('sales:invoice_detail', pk=invoice.pk)
                except IntegrityError as ie:
                    # على الأرجح تعارض في رقم الفاتورة، أعد المحاولة برقم جديد
                    if 'invoice_number' in str(ie):
                        # عطّل الرقم اليدوي في المحاولة القادمة وأعد المحاولة
                        allow_manual = False
                        if attempt < max_attempts:
                            continue
                        else:
                            raise
                    else:
                        raise

            # إذا وصلنا هنا ولم نرجع، نبلغ عن فشل عام
            messages.error(request, _('تعذر إنشاء الفاتورة بعد محاولات متعددة، يرجى المحاولة لاحقاً'))
            return redirect('sales:invoice_add')
        except Exception as e:
            messages.error(request, _('حدث خطأ أثناء حفظ الفاتورة: %(error)s') % {'error': str(e)})
            return redirect('sales:invoice_add')
    
    # GET request - عرض نموذج إنشاء الفاتورة
    try:
        context = {
            'customers': CustomerSupplier.objects.filter(type__in=['customer', 'both']),
            'today_date': date.today().isoformat(),
        }

        # إضافة بيانات المنتجات بتنسيق JSON للبحث
        products = Product.objects.filter(is_active=True).select_related('category')
        products_data = []
        for product in products:
            products_data.append({
                'id': product.id,
                'code': product.code,
                'name': product.name,
                'price': float(product.sale_price),
                'tax_rate': float(product.tax_rate),
                'category': product.category.name if product.category else ''
            })

        context['products_json'] = json.dumps(products_data)
        context['products'] = products  # إضافة المنتجات للـ modal

        # التحقق من صلاحيات المستخدم
        user = request.user
        context['can_edit_invoice_number'] = user.is_superuser or user.is_staff or user.has_perm('sales.change_salesinvoice_number')
        context['can_edit_date'] = user.is_superuser or user.is_staff or user.has_perm('sales.change_salesinvoice_date')
        # صلاحية تعديل خيار شمول الضريبة - استخدم في القالب لتجنّب استدعاءات دوال داخل قوالب
        context['can_toggle_invoice_tax'] = user.is_superuser or user.has_perm('sales.can_toggle_invoice_tax')

        # اسم المستخدم المنشئ (الاسم الأول + الاسم الأخير) لعرضه في القالب
        try:
            creator_full = f"{user.first_name or ''} {user.last_name or ''}".strip()
        except Exception:
            creator_full = user.username
        context['creator_full_name'] = creator_full
        # صلاحية تغيير منشئ الفاتورة وقائمة المستخدمين
        try:
            can_change_creator = user.is_superuser or user.has_perm('sales.can_change_invoice_creator')
        except Exception:
            can_change_creator = False
        context['can_change_creator'] = can_change_creator
        if can_change_creator:
            try:
                from django.contrib.auth import get_user_model
                U = get_user_model()
                context['all_users'] = U.objects.all()
            except Exception:
                context['all_users'] = []

        # سجل عرض صفحة إنشاء الفاتورة في سجل النشاط
        try:
            from core.signals import log_user_activity
            dummy = SalesInvoice()
            log_user_activity(
                request,
                'view',
                dummy,
                _('Viewed sales invoice creation page')
            )
        except Exception:
            pass

        # إضافة رقم الفاتورة المتوقع للعرض
        try:
            sequence = DocumentSequence.objects.get(document_type='sales_invoice')
            # استخدم معاينة الرقم التالي لتعكس أعلى رقم مستخدم فعلياً
            if hasattr(sequence, 'peek_next_number'):
                context['next_invoice_number'] = sequence.peek_next_number()
            else:
                context['next_invoice_number'] = sequence.get_formatted_number()
        except DocumentSequence.DoesNotExist:
            last_invoice = SalesInvoice.objects.order_by('-id').first()
            if last_invoice:
                number = int(last_invoice.invoice_number.split('-')[-1]) + 1 if '-' in last_invoice.invoice_number else int(last_invoice.invoice_number) + 1
            else:
                number = 1
            context['next_invoice_number'] = f"SALES-{number:06d}"

        # Currency settings
        try:
            company_settings = CompanySettings.objects.first()
            if company_settings and company_settings.base_currency:
                context['base_currency'] = company_settings.base_currency
            else:
                context['base_currency'] = Currency.objects.filter(is_active=True).first()
        except:
            pass

        return render(request, 'sales/invoice_add.html', context)
    except Exception as e:
        # سجل الاستثناء في اللوق وAuditLog ثم أعِد توجيه المستخدم بدل أن ترفع 500
        import logging
        logger = logging.getLogger(__name__)
        logger.exception("Error rendering sales invoice add page: %s", e)

        try:
            from core.signals import log_user_activity
            # استخدم كائن SalesInvoice وهمي لوصف الحدث
            dummy = SalesInvoice()
            log_user_activity(request, 'view', dummy, _('خطأ عند عرض صفحة إنشاء الفاتورة: %(error)s') % {'error': str(e)})
        except Exception:
            # لا نرمي أي استثناء إضافي أثناء تسجيل الخطأ
            pass

        messages.error(request, _('حدث خطأ أثناء تحميل صفحة إنشاء الفاتورة. تم تسجيل الخطأ لدى النظام.'))
        return redirect('sales:invoice_list')


class SalesInvoiceDetailView(LoginRequiredMixin, DetailView):
    model = SalesInvoice
    template_name = 'sales/invoice_detail.html'
    context_object_name = 'invoice'
    
    def get_queryset(self):
        # تحسين الاستعلام لتضمين البيانات المرتبطة
        return SalesInvoice.objects.select_related(
            'customer', 'created_by'
        ).prefetch_related(
            'items__product__category'
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # إضافة عناصر الفاتورة إلى السياق
        context['invoice_items'] = self.object.items.select_related('product__category').all()
        
        # Currency settings
        try:
            company_settings = CompanySettings.objects.first()
            if company_settings and company_settings.base_currency:
                context['base_currency'] = company_settings.base_currency
            else:
                context['base_currency'] = Currency.objects.filter(is_active=True).first()
        except:
            pass
        
        return context


class SalesInvoiceUpdateView(LoginRequiredMixin, UpdateView):
    model = SalesInvoice
    template_name = 'sales/invoice_edit.html'
    fields = ['invoice_number', 'date', 'customer', 'payment_type', 'notes']
    
    def get_success_url(self):
        return reverse_lazy('sales:invoice_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        # detect change to inclusive_tax and log activity
        try:
            old = SalesInvoice.objects.get(pk=form.instance.pk)
            old_inclusive = old.inclusive_tax
        except SalesInvoice.DoesNotExist:
            old_inclusive = None

        response = super().form_valid(form)

        try:
            new_inclusive = self.object.inclusive_tax
            if old_inclusive is not None and old_inclusive != new_inclusive:
                from core.signals import log_user_activity
                log_user_activity(
                    self.request,
                    'update',
                    self.object,
                    _('تغيير خيار شامل ضريبة من %(old)s إلى %(new)s لفاتورة %(number)s') % {
                        'old': str(old_inclusive), 'new': str(new_inclusive), 'number': self.object.invoice_number
                    }
                )
        except Exception:
            pass

        messages.success(self.request, 'تم تحديث فاتورة المبيعات بنجاح')
        return response


class SalesInvoiceDeleteView(LoginRequiredMixin, DeleteView):
    model = SalesInvoice
    template_name = 'sales/invoice_delete.html'
    success_url = reverse_lazy('sales:invoice_list')
    
    def delete(self, request, *args, **kwargs):
        invoice = self.get_object()
        invoice_number = invoice.invoice_number
        
        # حذف حركات المخزون المرتبطة (فقط إذا كانت موجودة)
        try:
            from inventory.models import InventoryMovement
            inventory_movements = InventoryMovement.objects.filter(
                reference_type='sales_invoice',
                reference_id=invoice.id
            )
            if inventory_movements.exists():
                movement_count = inventory_movements.count()
                inventory_movements.delete()
                print(f"تم حذف {movement_count} حركة مخزون للفاتورة {invoice_number}")
            else:
                print(f"لا توجد حركات مخزون للفاتورة {invoice_number} (فاتورة قديمة)")
        except ImportError:
            pass
        except Exception as e:
            print(f"خطأ في حذف حركات المخزون: {e}")
        
        # حذف قيود دفتر اليومية المرتبطة
        delete_transaction_by_reference('sales_invoice', invoice.id)
        
        # تسجيل النشاط قبل الحذف
        from core.signals import log_activity
        log_activity(
            user=request.user,
            action_type='DELETE',
            obj=invoice,
            description=f'تم حذف فاتورة مبيعات رقم: {invoice_number}',
            request=request
        )
        
        messages.success(request, f'تم حذف فاتورة المبيعات رقم {invoice_number} بنجاح')
        return super().delete(request, *args, **kwargs)


class SalesReturnListView(LoginRequiredMixin, ListView):
    model = SalesReturn
    template_name = 'sales/return_list.html'
    context_object_name = 'returns'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = SalesReturn.objects.all()
        
        # Search functionality
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(return_number__icontains=search) |
                Q(customer__name__icontains=search)
            )
        
        # Date filter
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
        
        # Customer filter
        customer = self.request.GET.get('customer')
        if customer:
            queryset = queryset.filter(customer_id=customer)
        
        return queryset.select_related('customer', 'original_invoice', 'created_by')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Statistics
        from django.utils import timezone
        from datetime import datetime, timedelta
        
        returns = SalesReturn.objects.all()
        context['total_returns'] = returns.count()
        context['total_returns_amount'] = returns.aggregate(
            total=Sum('total_amount')
        )['total'] or 0
        
        # Monthly and daily stats
        today = timezone.now().date()
        month_start = today.replace(day=1)
        context['monthly_returns'] = returns.filter(date__gte=month_start).count()
        context['daily_returns'] = returns.filter(date=today).count()
        
        # Customers for filter
        context['customers'] = CustomerSupplier.objects.filter(
            type__in=['customer', 'both']
        )
        
        # Currency settings
        try:
            company_settings = CompanySettings.objects.first()
            if company_settings and company_settings.base_currency:
                context['base_currency'] = company_settings.base_currency
            else:
                context['base_currency'] = Currency.objects.filter(is_active=True).first()
        except:
            pass
        
        return context


class SalesReturnCreateView(LoginRequiredMixin, CreateView):
    model = SalesReturn
    template_name = 'sales/return_add.html'
    fields = ['return_number', 'date', 'original_invoice', 'customer', 'notes']
    success_url = reverse_lazy('sales:return_list')
    
    def form_valid(self, form):
        from django.db import transaction
        
        print(f"POST data: {self.request.POST}")
        
        try:
            with transaction.atomic():
                # التحقق من البيانات المطلوبة
                if not form.cleaned_data.get('original_invoice'):
                    messages.error(self.request, 'يرجى اختيار الفاتورة الأصلية')
                    return self.form_invalid(form)
                
                # توليد رقم المرتجع إذا لم يكن محدد
                if not form.cleaned_data.get('return_number'):
                    try:
                        sequence = DocumentSequence.objects.get(document_type='sales_return')
                        form.instance.return_number = sequence.get_next_number()
                    except DocumentSequence.DoesNotExist:
                        last_return = SalesReturn.objects.order_by('-id').first()
                        if last_return:
                            number = int(last_return.return_number.split('-')[-1]) + 1 if '-' in last_return.return_number else int(last_return.return_number) + 1
                        else:
                            number = 1
                        form.instance.return_number = f"RETURN-{number:06d}"
                
                form.instance.created_by = self.request.user
                
                # معالجة بيانات المنتجات المرتجعة
                return_quantities = {}
                return_prices = {}
                
                for key, value in self.request.POST.items():
                    if key.startswith('return_quantities[') and key.endswith(']'):
                        product_id = key[18:-1]  # استخراج product_id
                        try:
                            quantity = Decimal(value) if value else Decimal('0')
                            if quantity > 0:
                                return_quantities[int(product_id)] = quantity
                        except (ValueError, TypeError):
                            continue
                    elif key.startswith('return_prices[') and key.endswith(']'):
                        product_id = key[14:-1]  # استخراج product_id
                        try:
                            price = Decimal(value) if value else Decimal('0')
                            if price >= 0:
                                return_prices[int(product_id)] = price
                        except (ValueError, TypeError):
                            continue
                
                # التحقق من وجود منتجات للإرجاع
                if not return_quantities:
                    messages.error(self.request, 'يرجى تحديد كمية للإرجاع لمنتج واحد على الأقل')
                    return self.form_invalid(form)
                
                # حساب المجاميع
                subtotal = Decimal('0')
                total_tax = Decimal('0')
                
                # حفظ المردود أولاً
                response = super().form_valid(form)
                
                # إنشاء عناصر المردود
                from .models import SalesReturnItem
                for product_id, quantity in return_quantities.items():
                    if product_id in return_prices:
                        try:
                            product = Product.objects.get(id=product_id)
                            unit_price = return_prices[product_id]
                            
                            # حساب الضريبة والإجمالي
                            line_subtotal = quantity * unit_price
                            tax_rate = product.tax_rate or Decimal('0')
                            tax_amount = line_subtotal * (tax_rate / Decimal('100'))
                            total_amount = line_subtotal + tax_amount
                            
                            # إنشاء عنصر المردود
                            SalesReturnItem.objects.create(
                                return_invoice=self.object,
                                product=product,
                                quantity=quantity,
                                unit_price=unit_price,
                                tax_rate=tax_rate,
                                tax_amount=tax_amount,
                                total_amount=total_amount
                            )
                            
                            subtotal += line_subtotal
                            total_tax += tax_amount
                            
                        except Product.DoesNotExist:
                            continue
                
                # تحديث مجاميع المردود
                self.object.subtotal = subtotal
                self.object.tax_amount = total_tax
                self.object.total_amount = subtotal + total_tax
                self.object.save()
                
                # إنشاء حركة حساب للعميل
                create_sales_return_account_transaction(self.object, self.request.user)
                
                # إنشاء حركات المخزون للمردود
                create_sales_return_inventory_movements(self.object, self.request.user)
                
                # إنشاء القيد المحاسبي
                create_sales_return_journal_entry(self.object, self.request.user)
                
                # تسجيل النشاط
                from core.signals import log_user_activity
                log_user_activity(
                    self.request,
                    'create',
                    self.object,
                    f'تم إنشاء مردود مبيعات رقم {self.object.return_number}'
                )
                
                messages.success(self.request, f'تم إنشاء مردود المبيعات رقم {self.object.return_number} بنجاح')
                return response
                
        except Exception as e:
            messages.error(self.request, f'حدث خطأ أثناء حفظ المردود: {str(e)}')
            return self.form_invalid(form)
    
    def form_invalid(self, form):
        print(f"Form errors: {form.errors}")
        messages.error(self.request, 'يرجى التحقق من البيانات المدخلة وإصلاح الأخطاء')
        return super().form_invalid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['invoices'] = SalesInvoice.objects.all()
        context['customers'] = CustomerSupplier.objects.filter(
            type__in=['customer', 'both']
        )
        
        # إعدادات العملة
        try:
            company_settings = CompanySettings.objects.first()
            if company_settings and company_settings.base_currency:
                context['base_currency'] = company_settings.base_currency
            else:
                context['base_currency'] = Currency.objects.filter(is_active=True).first()
        except:
            context['base_currency'] = None
        
        # الحصول على رقم المرتجع التالي
        try:
            sequence = DocumentSequence.objects.get(document_type='sales_return')
            context['next_return_number'] = sequence.get_formatted_number()
        except DocumentSequence.DoesNotExist:
            last_return = SalesReturn.objects.order_by('-id').first()
            if last_return:
                try:
                    number = int(last_return.return_number.split('-')[-1]) + 1 if '-' in last_return.return_number else int(last_return.return_number) + 1
                except (ValueError, IndexError):
                    number = 1
            else:
                number = 1
            context['next_return_number'] = f"SRET-{number:06d}"
        
        return context


class SalesReturnDetailView(LoginRequiredMixin, DetailView):
    model = SalesReturn
    template_name = 'sales/return_detail.html'
    context_object_name = 'return'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Currency settings
        try:
            company_settings = CompanySettings.objects.first()
            if company_settings and company_settings.base_currency:
                context['base_currency'] = company_settings.base_currency
            else:
                context['base_currency'] = Currency.objects.filter(is_active=True).first()
        except:
            pass
        
        return context


class SalesReturnUpdateView(LoginRequiredMixin, UpdateView):
    model = SalesReturn
    template_name = 'sales/return_edit.html'
    fields = ['return_number', 'date', 'original_invoice', 'customer', 'notes']
    
    def get_success_url(self):
        return reverse_lazy('sales:return_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, 'تم تحديث مردود المبيعات بنجاح')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['invoices'] = SalesInvoice.objects.all()
        context['customers'] = CustomerSupplier.objects.filter(
            type__in=['customer', 'both']
        )
        
        # Currency settings
        try:
            company_settings = CompanySettings.objects.first()
            if company_settings and company_settings.base_currency:
                context['base_currency'] = company_settings.base_currency
            else:
                context['base_currency'] = Currency.objects.filter(is_active=True).first()
        except:
            pass
        
        return context


class SalesCreditNoteListView(LoginRequiredMixin, ListView):
    model = SalesCreditNote
    template_name = 'sales/creditnote_list.html'
    context_object_name = 'creditnotes'
    paginate_by = 10

    def get_queryset(self):
        queryset = SalesCreditNote.objects.all()
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(note_number__icontains=search) |
                Q(customer__name__icontains=search)
            )
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
        return queryset.select_related('customer', 'created_by')


@login_required
def sales_creditnote_create(request):
    """إنشاء إشعار دائن للمبيعات"""
    if request.method == 'POST':
        try:
            with transaction.atomic():
                user = request.user
                customer_id = request.POST.get('customer')
                notes = request.POST.get('notes', '')

                if not customer_id:
                    messages.error(request, _('يرجى اختيار عميل'))
                    return redirect('sales:creditnote_add')

                customer = get_object_or_404(CustomerSupplier, id=customer_id)

                # توليد رقم الإشعار عبر DocumentSequence
                try:
                    seq = DocumentSequence.objects.get(document_type='credit_note')
                    note_number = seq.get_next_number()
                except DocumentSequence.DoesNotExist:
                    last = SalesCreditNote.objects.order_by('-id').first()
                    if last:
                        try:
                            number = int(last.note_number.split('-')[-1]) + 1
                        except Exception:
                            number = last.id + 1
                    else:
                        number = 1
                    note_number = f"CN-{number:06d}"

                credit = SalesCreditNote.objects.create(
                    note_number=note_number,
                    date=request.POST.get('date', date.today()),
                    customer=customer,
                    subtotal=Decimal(request.POST.get('subtotal', '0') or '0'),
                    tax_amount=Decimal(request.POST.get('tax_amount', '0') or '0'),
                    total_amount=Decimal(request.POST.get('total_amount', '0') or '0'),
                    notes=notes,
                    created_by=user
                )

                # سجل الـ AuditLog
                try:
                    from core.signals import log_user_activity
                    log_user_activity(
                        request,
                        'create',
                        credit,
                        _('إنشاء إشعار دائن رقم %(number)s') % {'number': credit.note_number}
                    )
                except Exception:
                    pass

                messages.success(request, _('تم إنشاء إشعار دائن رقم %(number)s') % {'number': credit.note_number})
                return redirect('sales:creditnote_detail', pk=credit.pk)
        except Exception as e:
            messages.error(request, _('حدث خطأ أثناء حفظ الإشعار: %(error)s') % {'error': str(e)})
            return redirect('sales:creditnote_add')

    # GET
    context = {
        'customers': CustomerSupplier.objects.filter(type__in=['customer', 'both']),
        'today_date': date.today().isoformat(),
    }
    try:
        seq = DocumentSequence.objects.get(document_type='credit_note')
        context['next_note_number'] = seq.peek_next_number() if hasattr(seq, 'peek_next_number') else seq.get_formatted_number()
    except DocumentSequence.DoesNotExist:
        last = SalesCreditNote.objects.order_by('-id').first()
        if last:
            try:
                number = int(last.note_number.split('-')[-1]) + 1
            except Exception:
                number = last.id + 1
        else:
            number = 1
        context['next_note_number'] = f"CN-{number:06d}"

    return render(request, 'sales/creditnote_add.html', context)


class SalesCreditNoteDetailView(LoginRequiredMixin, DetailView):
    model = SalesCreditNote
    template_name = 'sales/creditnote_detail.html'
    context_object_name = 'creditnote'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            company_settings = CompanySettings.objects.first()
            if company_settings and company_settings.base_currency:
                context['base_currency'] = company_settings.base_currency
            else:
                context['base_currency'] = Currency.objects.filter(is_active=True).first()
        except:
            pass
        return context


class SalesCreditNoteUpdateView(LoginRequiredMixin, UpdateView):
    model = SalesCreditNote
    template_name = 'sales/creditnote_edit.html'
    fields = ['note_number', 'date', 'customer', 'subtotal', 'tax_amount', 'total_amount', 'notes']
    
    def get_success_url(self):
        return reverse_lazy('sales:creditnote_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        # تسجيل النشاط
        try:
            from core.signals import log_user_activity
            log_user_activity(
                self.request,
                'update',
                self.object,
                _('تحديث إشعار دائن رقم %(number)s') % {'number': self.object.note_number}
            )
        except Exception:
            pass
        
        messages.success(self.request, _('تم تحديث إشعار الدائن بنجاح'))
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['customers'] = CustomerSupplier.objects.filter(type__in=['customer', 'both'])
        
        # Currency settings
        try:
            company_settings = CompanySettings.objects.first()
            if company_settings and company_settings.base_currency:
                context['base_currency'] = company_settings.base_currency
            else:
                context['base_currency'] = Currency.objects.filter(is_active=True).first()
        except:
            pass
        
        return context


class SalesCreditNoteDeleteView(LoginRequiredMixin, DeleteView):
    model = SalesCreditNote
    template_name = 'sales/creditnote_delete.html'
    success_url = reverse_lazy('sales:creditnote_list')
    
    def delete(self, request, *args, **kwargs):
        creditnote = self.get_object()
        note_number = creditnote.note_number
        
        # تسجيل النشاط قبل الحذف
        try:
            from core.signals import log_user_activity
            log_user_activity(
                request,
                'delete',
                creditnote,
                _('حذف إشعار دائن رقم %(number)s') % {'number': note_number}
            )
        except Exception:
            pass
        
        messages.success(request, _('تم حذف إشعار الدائن رقم %(number)s بنجاح') % {'number': note_number})
        return super().delete(request, *args, **kwargs)


class SalesReturnDeleteView(LoginRequiredMixin, DeleteView):
    model = SalesReturn
    template_name = 'sales/return_delete.html'
    success_url = reverse_lazy('sales:return_list')
    
    def delete(self, request, *args, **kwargs):
        return_invoice = self.get_object()
        return_number = return_invoice.return_number
        
        # حذف حركات المخزون المرتبطة (فقط إذا كانت موجودة)
        try:
            from inventory.models import InventoryMovement
            inventory_movements = InventoryMovement.objects.filter(
                reference_type='sales_return',
                reference_id=return_invoice.id
            )
            if inventory_movements.exists():
                movement_count = inventory_movements.count()
                inventory_movements.delete()
                print(f"تم حذف {movement_count} حركة مخزون للمردود {return_number}")
            else:
                print(f"لا توجد حركات مخزون للمردود {return_number} (مردود قديم)")
        except ImportError:
            pass
        except Exception as e:
            print(f"خطأ في حذف حركات المخزون: {e}")
        
        # تسجيل النشاط قبل الحذف
        from core.signals import log_activity
        log_activity(
            user=request.user,
            action_type='DELETE',
            obj=return_invoice,
            description=f'تم حذف مردود مبيعات رقم: {return_number}',
            request=request
        )
        
        messages.success(request, f'تم حذف مردود المبيعات رقم {return_number} بنجاح')
        return super().delete(request, *args, **kwargs)


def print_sales_invoice(request, pk):
    invoice = get_object_or_404(SalesInvoice, pk=pk)
    return HttpResponse(f"طباعة فاتورة المبيعات رقم {invoice.invoice_number}")  # Placeholder


@login_required
def pos_view(request):
    """شاشة نقطة البيع"""
    # التحقق من صلاحية الوصول لنقطة البيع
    if not request.user.has_pos_permission():
        messages.error(request, 'ليس لديك صلاحية للوصول إلى نقطة البيع')
        return redirect('core:dashboard')
    
    context = {
        'user_name': request.user.get_full_name() or request.user.username,
        'products': Product.objects.filter(is_active=True),
        'customers': CustomerSupplier.objects.filter(
            type__in=['customer', 'both'], 
            is_active=True
        ),
        'payment_types': SalesInvoice.PAYMENT_TYPES,
    }
    
    # إعدادات العملة
    try:
        company_settings = CompanySettings.objects.first()
        if company_settings and company_settings.base_currency:
            context['base_currency'] = company_settings.base_currency
        else:
            context['base_currency'] = Currency.objects.filter(is_active=True).first()
    except:
        context['base_currency'] = None
    
    return render(request, 'sales/pos.html', context)


@login_required
@require_http_methods(['POST'])
def pos_create_invoice(request):
    """إنشاء فاتورة من نقطة البيع"""
    try:
        # التحقق من صلاحية نقطة البيع
        if not hasattr(request.user, 'has_pos_permission') or not request.user.has_pos_permission():
            return JsonResponse({'success': False, 'message': 'ليس لديك صلاحية للوصول إلى نقطة البيع'})
        
        # التحقق من أن الطلب AJAX
        if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'طلب غير صحيح'})
        
        # التحقق من وجود البيانات
        if not request.body:
            return JsonResponse({'success': False, 'message': 'البيانات المرسلة فارغة'})
            
        data = json.loads(request.body)
        
        # التحقق من وجود البيانات المطلوبة
        if not data.get('items'):
            return JsonResponse({'success': False, 'message': 'لا توجد عناصر في الفاتورة'})
        
        if not data.get('total'):
            return JsonResponse({'success': False, 'message': 'الإجمالي غير صحيح'})
        
        with transaction.atomic():
            # توليد رقم الفاتورة
            try:
                sequence = DocumentSequence.objects.get(document_type='pos_invoice')
                invoice_number = sequence.get_next_number()
            except DocumentSequence.DoesNotExist:
                # في حالة عدم وجود تسلسل نقطة البيع، إنشاء واحد جديد
                try:
                    sequence = DocumentSequence.objects.create(
                        document_type='pos_invoice',
                        prefix='POS-',
                        digits=6,
                        current_number=1
                    )
                    invoice_number = sequence.get_next_number()
                except Exception as seq_error:
                    # في حالة فشل إنشاء التسلسل، استخدام رقم بسيط
                    print(f"فشل في إنشاء تسلسل pos_invoice: {seq_error}")
                    last_invoice = SalesInvoice.objects.filter(
                        invoice_number__startswith='POS-'
                    ).order_by('-id').first()
                    if last_invoice:
                        try:
                            last_number = int(last_invoice.invoice_number.split('-')[-1])
                            number = last_number + 1
                        except:
                            number = 1
                    else:
                        number = 1
                    invoice_number = f"POS-{number:06d}"
            
            # إنشاء الفاتورة
            customer_id = data.get('customer_id')
            customer = None
            if customer_id:
                try:
                    customer = CustomerSupplier.objects.get(id=customer_id)
                except CustomerSupplier.DoesNotExist:
                    customer = None
            
            # تحديد الصندوق المناسب لمستخدم POS
            pos_cashbox = None
            if request.user.user_type == 'pos_user':
                try:
                    from cashboxes.models import Cashbox
                    pos_cashbox = Cashbox.objects.filter(responsible_user=request.user).first()
                    
                    # إذا لم يكن له صندوق، إنشاء واحد تلقائياً
                    if not pos_cashbox:
                        # اسم الصندوق = اسم المستخدم
                        cashbox_name = request.user.username
                        
                        # الحصول على العملة الأساسية
                        from core.models import CompanySettings
                        company_settings = CompanySettings.get_settings()
                        currency = 'JOD'
                        if company_settings and company_settings.currency:
                            currency = company_settings.currency
                        
                        pos_cashbox = Cashbox.objects.create(
                            name=cashbox_name,
                            description=f"صندوق مستخدم نقطة البيع: {request.user.get_full_name() or request.user.username}",
                            balance=Decimal('0.000'),
                            currency=currency,
                            location=f"نقطة البيع - {request.user.username}",
                            responsible_user=request.user,
                            is_active=True
                        )
                        print(f"تم إنشاء صندوق جديد: {cashbox_name}")
                except Exception as cashbox_error:
                    print(f"خطأ في إعداد صندوق POS: {cashbox_error}")
            
            # التحقق من عدم تكرار رقم الفاتورة
            max_attempts = 10
            attempt = 0
            while attempt < max_attempts:
                try:
                    invoice = SalesInvoice.objects.create(
                        invoice_number=invoice_number,
                        customer=customer,
                        date=date.today(),
                        payment_type=data.get('payment_type', 'cash'),
                        cashbox=pos_cashbox,  # ربط الفاتورة بصندوق المستخدم
                        notes=data.get('notes', ''),
                        created_by=request.user,
                        subtotal=Decimal(str(data.get('subtotal', 0))),
                        tax_amount=Decimal(str(data.get('tax_amount', 0))),
                        discount_amount=Decimal(str(data.get('discount_amount', 0))),
                        total_amount=Decimal(str(data.get('total', 0))),
                    )
                    break
                except Exception as e:
                    if 'UNIQUE constraint failed' in str(e):
                        # في حالة تكرار رقم الفاتورة، توليد رقم جديد
                        attempt += 1
                        try:
                            sequence = DocumentSequence.objects.get(document_type='pos_invoice')
                            invoice_number = sequence.get_next_number()
                        except:
                            # رقم بديل
                            import time
                            timestamp = int(time.time())
                            invoice_number = f"POS-{timestamp}"
                        
                        if attempt >= max_attempts:
                            raise Exception('فشل في إنشاء رقم فاتورة فريد')
                    else:
                        raise e
            
            # إضافة عناصر الفاتورة
            for item_data in data.get('items', []):
                product = Product.objects.get(id=item_data['product_id'])
                
                SalesInvoiceItem.objects.create(
                    invoice=invoice,
                    product=product,
                    quantity=Decimal(str(item_data['quantity'])),
                    unit_price=Decimal(str(item_data['unit_price'])),
                    total_amount=Decimal(str(item_data['total'])),
                    tax_rate=Decimal(str(item_data.get('tax_rate', 0))),
                    tax_amount=Decimal(str(item_data.get('tax_amount', 0))),
                )
                
                # إنشاء حركة مخزون صادرة
                try:
                    from inventory.models import InventoryMovement, Warehouse
                    
                    # الحصول على المستودع الافتراضي
                    default_warehouse = Warehouse.objects.filter(is_active=True).first()
                    if not default_warehouse:
                        # إنشاء مستودع افتراضي إذا لم يكن موجوداً
                        default_warehouse = Warehouse.objects.create(
                            name='المستودع الرئيسي',
                            code='MAIN',
                            is_active=True
                        )
                    
                    # توليد رقم الحركة
                    import uuid
                    movement_number = f"POS-OUT-{uuid.uuid4().hex[:8].upper()}"
                    
                    InventoryMovement.objects.create(
                        movement_number=movement_number,
                        date=date.today(),
                        product=product,
                        warehouse=default_warehouse,
                        movement_type='out',
                        reference_type='sales_invoice',
                        reference_id=invoice.id,
                        quantity=Decimal(str(item_data['quantity'])),
                        unit_cost=Decimal(str(item_data.get('unit_price', 0))),
                        notes=f'مبيعات - فاتورة رقم {invoice.invoice_number}',
                        created_by=request.user
                    )
                except ImportError:
                    # في حالة عدم وجود نموذج المخزون
                    pass
                except Exception as inventory_error:
                    # في حالة حدوث خطأ في المخزون، لا نوقف إنشاء الفاتورة
                    print(f"خطأ في إنشاء حركة المخزون: {inventory_error}")
                    pass
            
            # إنشاء حركة حساب للعميل
            try:
                from accounts.models import AccountTransaction
                import uuid
                
                # إذا كان هناك عميل وطريقة الدفع ليست نقداً
                if customer and data.get('payment_type') != 'cash':
                    # حساب الإجمالي
                    total_amount = Decimal(str(data.get('total', 0)))
                    
                    # توليد رقم الحركة
                    transaction_number = f"POS-SALE-{uuid.uuid4().hex[:8].upper()}"
                    
                    # حساب الرصيد السابق
                    last_transaction = AccountTransaction.objects.filter(
                        customer_supplier=customer
                    ).order_by('-created_at').first()
                    
                    previous_balance = last_transaction.balance_after if last_transaction else Decimal('0')
                    
                    # إنشاء حركة مدينة للعميل (زيادة الذمم المدينة)
                    new_balance = previous_balance + total_amount
                    
                    AccountTransaction.objects.create(
                        transaction_number=transaction_number,
                        date=date.today(),
                        customer_supplier=customer,
                        transaction_type='sales_invoice',
                        direction='debit',
                        amount=total_amount,
                        reference_type='sales_invoice',
                        reference_id=invoice.id,
                        description=f'مبيعات - فاتورة رقم {invoice.invoice_number}',
                        balance_after=new_balance,
                        created_by=request.user
                    )
                    
            except ImportError:
                # في حالة عدم وجود نموذج الحسابات
                pass
            except Exception as account_error:
                print(f"خطأ في إنشاء حركة الحساب: {account_error}")
                # لا نوقف العملية في حالة فشل تسجيل الحركة المالية
                pass
            
            # إنشاء القيد المحاسبي للفاتورة
            try:
                create_sales_invoice_journal_entry(invoice, request.user)
            except Exception as journal_error:
                print(f"خطأ في إنشاء القيد المحاسبي: {journal_error}")
                # لا نوقف العملية في حالة فشل إنشاء القيد المحاسبي
                pass
            
            return JsonResponse({
                'success': True, 
                'message': 'تم إنشاء الفاتورة بنجاح',
                'invoice_id': invoice.id,
                'invoice_number': invoice.invoice_number
            })
            
    except json.JSONDecodeError as e:
        return JsonResponse({
            'success': False, 
            'message': 'خطأ في تحليل البيانات المرسلة'
        }, status=400)
    except Product.DoesNotExist:
        return JsonResponse({
            'success': False, 
            'message': 'أحد المنتجات غير موجود'
        }, status=404)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False, 
            'message': f'حدث خطأ أثناء إنشاء الفاتورة: {str(e)}'
        }, status=500)


@login_required
def pos_get_product(request, product_id):
    """الحصول على بيانات المنتج لنقطة البيع"""
    if not request.user.has_pos_permission():
        return JsonResponse({'success': False, 'message': 'ليس لديك صلاحية للوصول إلى نقطة البيع'})
    
    try:
        product = Product.objects.get(id=product_id, is_active=True)
        
        # حساب المخزون الحالي باستخدام property
        current_stock = product.current_stock
        
        return JsonResponse({
            'success': True,
            'product': {
                'id': product.id,
                'name': product.name,
                'price': float(product.sale_price),
                'stock': float(current_stock) if current_stock is not None else 0,
                'tax_rate': float(product.tax_rate or 0),
                'barcode': product.barcode or '',
                'track_inventory': True,  # افتراض أن جميع المنتجات تتبع المخزون
            }
        })
    except Product.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'المنتج غير موجود'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'حدث خطأ: {str(e)}'})


@login_required
def pos_search_products(request):
    """البحث عن المنتجات في نقطة البيع"""
    if not request.user.has_pos_permission():
        return JsonResponse({'success': False, 'message': 'ليس لديك صلاحية للوصول إلى نقطة البيع'})
    
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return JsonResponse({'products': []})
    
    try:
        products = Product.objects.filter(
            Q(name__icontains=query) | Q(barcode__icontains=query),
            is_active=True
        )[:20]
        
        products_data = []
        for product in products:
            # حساب المخزون الحالي
            current_stock = product.current_stock
            
            products_data.append({
                'id': product.id,
                'name': product.name,
                'price': float(product.sale_price),
                'stock': float(current_stock) if current_stock is not None else 0,
                'tax_rate': float(product.tax_rate or 0),
                'barcode': product.barcode or '',
                'track_inventory': True,  # افتراض أن جميع المنتجات تتبع المخزون
            })
        
        return JsonResponse({'products': products_data})
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'حدث خطأ في البحث: {str(e)}'})


class SalesReportView(LoginRequiredMixin, TemplateView):
    template_name = 'sales/sales_report.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        from django.utils import timezone
        from datetime import datetime, timedelta
        from django.db.models import Sum, Count
        
        # الحصول على التواريخ من الطلب
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        
        # التواريخ الافتراضية (الشهر الحالي)
        today = timezone.now().date()
        if not start_date:
            start_date = today.replace(day=1).strftime('%Y-%m-%d')
        if not end_date:
            end_date = today.strftime('%Y-%m-%d')
            
        # تحويل التواريخ لاستخدامها في الاستعلامات
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        # فواتير المبيعات في الفترة المحددة
        sales_invoices = SalesInvoice.objects.filter(
            date__gte=start_date_obj,
            date__lte=end_date_obj
        ).select_related('customer').order_by('-date')
        
        # إحصائيات المبيعات
        stats = {
            'total_invoices': sales_invoices.count(),
            'total_amount': sales_invoices.aggregate(total=Sum('total_amount'))['total'] or 0,
            'total_tax': sales_invoices.aggregate(total=Sum('tax_amount'))['total'] or 0,
            'total_discount': sales_invoices.aggregate(total=Sum('discount_amount'))['total'] or 0,
        }
        
        # مبيعات حسب العملاء
        customer_sales = sales_invoices.values('customer__name').annotate(
            total_amount=Sum('total_amount'),
            invoice_count=Count('id')
        ).order_by('-total_amount')[:10]  # أفضل 10 عملاء
        
        # مبيعات حسب اليوم
        daily_sales = sales_invoices.extra({'date': "date(date)"}).values('date').annotate(
            total_amount=Sum('total_amount'),
            invoice_count=Count('id')
        ).order_by('date')
        
        context.update({
            'start_date': start_date,
            'end_date': end_date,
            'sales_invoices': sales_invoices,
            'stats': stats,
            'customer_sales': customer_sales,
            'daily_sales': daily_sales,
        })
        
        return context


class SalesStatementView(LoginRequiredMixin, TemplateView):
    """عرض كشف المبيعات"""
    template_name = 'sales/sales_statement.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # فترة البحث الافتراضية (الشهر الحالي)
        today = timezone.now().date()
        start_date = today.replace(day=1)
        end_date = today
        
        # تطبيق الفلاتر من الطلب
        if self.request.GET.get('start_date'):
            start_date = datetime.strptime(self.request.GET.get('start_date'), '%Y-%m-%d').date()
        if self.request.GET.get('end_date'):
            end_date = datetime.strptime(self.request.GET.get('end_date'), '%Y-%m-%d').date()
        
        # جلب فواتير المبيعات مرتبة حسب التاريخ
        sales_invoices = SalesInvoice.objects.filter(
            date__range=[start_date, end_date]
        ).order_by('date', 'invoice_number')
        
        # حساب الرصيد التراكمي (دائن - إيرادات المبيعات)
        running_balance = Decimal('0')
        statement_data = []
        
        for invoice in sales_invoices:
            # قيمة الفاتورة قبل الضريبة وبعد الخصم
            credit_amount = invoice.subtotal - invoice.discount_amount
            running_balance += credit_amount
            
            statement_data.append({
                'date': invoice.date,
                'document_number': invoice.invoice_number,
                'description': 'فاتورة مبيعات',
                'credit': credit_amount,
                'balance': running_balance,
                'invoice': invoice
            })
        
        context.update({
            'start_date': start_date,
            'end_date': end_date,
            'statement_data': statement_data,
            'final_balance': running_balance,
        })
        
        return context


class SalesReturnStatementView(LoginRequiredMixin, TemplateView):
    """عرض كشف مردودات المبيعات"""
    template_name = 'sales/sales_return_statement.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # فترة البحث الافتراضية (الشهر الحالي)
        today = timezone.now().date()
        start_date = today.replace(day=1)
        end_date = today
        
        # تطبيق الفلاتر من الطلب
        if self.request.GET.get('start_date'):
            start_date = datetime.strptime(self.request.GET.get('start_date'), '%Y-%m-%d').date()
        if self.request.GET.get('end_date'):
            end_date = datetime.strptime(self.request.GET.get('end_date'), '%Y-%m-%d').date()
        
        # جلب مردودات المبيعات مرتبة حسب التاريخ
        sales_returns = SalesReturn.objects.filter(
            date__range=[start_date, end_date]
        ).order_by('date', 'return_number')
        
        # حساب الرصيد التراكمي (مدين - يقلل من الإيرادات)
        running_balance = Decimal('0')
        statement_data = []
        
        for return_item in sales_returns:
            # قيمة المردود قبل الضريبة وبعد الخصم
            debit_amount = return_item.subtotal
            running_balance += debit_amount
            
            statement_data.append({
                'date': return_item.date,
                'document_number': return_item.return_number,
                'description': 'مردود مبيعات',
                'debit': debit_amount,
                'balance': running_balance,
                'return_item': return_item
            })
        
        context.update({
            'start_date': start_date,
            'end_date': end_date,
            'statement_data': statement_data,
            'final_balance': running_balance,
        })
        
        return context


@login_required
@require_POST
def send_invoice_to_jofotara(request, pk):
    """إرسال فاتورة المبيعات إلى JoFotara"""
    try:
        # Get the invoice
        invoice = get_object_or_404(SalesInvoice, pk=pk)
        
        # Check if user has permission to send invoices
        if not request.user.has_perm('sales.can_send_to_jofotara'):
            return JsonResponse({
                'success': False,
                'error': 'ليس لديك صلاحية إرسال الفواتير إلى JoFotara'
            })
        
        # Import the utility function
        from settings.utils import send_sales_invoice_to_jofotara
        
        # Send the invoice
        result = send_sales_invoice_to_jofotara(invoice)
        
        if result['success']:
            # Update invoice with JoFotara UUID if available
            if 'uuid' in result:
                invoice.jofotara_uuid = result['uuid']
                invoice.jofotara_sent_at = timezone.now()
                invoice.save()
            
            messages.success(request, f'تم إرسال الفاتورة {invoice.invoice_number} إلى JoFotara بنجاح')
        else:
            messages.error(request, f'فشل في إرسال الفاتورة: {result.get("error", "خطأ غير معروف")}')
        
        return JsonResponse(result)
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error sending invoice to JoFotara: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'خطأ في النظام: {str(e)}'
        })


@login_required
@require_POST
def send_creditnote_to_jofotara(request, pk):
    """إرسال إشعار دائن إلى JoFotara"""
    try:
        # Get the credit note
        credit_note = get_object_or_404(SalesCreditNote, pk=pk)
        
        # Check if user has permission to send credit notes
        if not request.user.has_perm('sales.can_send_to_jofotara'):
            return JsonResponse({
                'success': False,
                'error': 'ليس لديك صلاحية إرسال الإشعارات الدائنة إلى JoFotara'
            })
        
        # Import the utility function
        from settings.utils import send_credit_note_to_jofotara
        
        # Send the credit note
        result = send_credit_note_to_jofotara(credit_note)
        
        if result['success']:
            # Update credit note with JoFotara UUID if available
            if 'uuid' in result:
                credit_note.jofotara_uuid = result['uuid']
                credit_note.jofotara_sent_at = timezone.now()
                credit_note.save()
            
            messages.success(request, f'تم إرسال الإشعار الدائن {credit_note.note_number} إلى JoFotara بنجاح')
        else:
            messages.error(request, f'فشل في إرسال الإشعار الدائن: {result.get("error", "خطأ غير معروف")}')
        
        return JsonResponse(result)
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error sending credit note to JoFotara: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'خطأ في النظام: {str(e)}'
        })


@login_required
@csrf_exempt
def get_invoices_for_returns(request):
    """API endpoint لجلب الفواتير المتاحة للمرتجعات مع البحث"""
    print(f"API called by user: {request.user}")
    print(f"Request method: {request.method}")
    print(f"Request GET params: {request.GET}")
    
    try:
        search_term = request.GET.get('search', '').strip()
        print(f"Search term: '{search_term}'")
        
        # جلب الفواتير مع إمكانية البحث
        invoices = SalesInvoice.objects.select_related('customer').all()
        print(f"Total invoices in database: {invoices.count()}")
        
        if search_term:
            invoices = invoices.filter(
                Q(invoice_number__icontains=search_term) |
                Q(customer__name__icontains=search_term)
            )
            print(f"Filtered invoices count: {invoices.count()}")
        
        # تحديد الحد الأقصى للنتائج
        invoices = invoices[:20]
        
        invoices_data = []
        for invoice in invoices:
            print(f"Processing invoice: {invoice.invoice_number}")
            # جلب عناصر الفاتورة
            items_data = []
            for item in invoice.items.select_related('product').all():
                items_data.append({
                    'product_id': item.product.id,
                    'product_name': item.product.name,
                    'product_code': item.product.code,
                    'quantity': float(item.quantity),
                    'unit_price': float(item.unit_price),
                    'tax_rate': float(item.tax_rate),
                    'tax_amount': float(item.tax_amount),
                    'total': float(item.total_amount)
                })
            
            invoices_data.append({
                'id': invoice.id,
                'invoice_number': invoice.invoice_number,
                'customer': invoice.customer.name if invoice.customer else '',
                'customer_id': invoice.customer.id if invoice.customer else None,
                'date': invoice.date.strftime('%Y-%m-%d'),
                'total': float(invoice.total_amount),
                'payment_type': invoice.get_payment_type_display(),
                'items': items_data
            })
        
        print(f"Returning {len(invoices_data)} invoices")
        return JsonResponse({
            'success': True,
            'invoices': invoices_data
        })
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error fetching invoices for returns: {str(e)}")
        print(f"Error in API: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': f'خطأ في النظام: {str(e)}'
        })


class SalesCreditNoteReportView(LoginRequiredMixin, ListView):
    """كشف مذكرات الدائن"""
    model = SalesCreditNote
    template_name = 'sales/creditnote_report.html'
    context_object_name = 'creditnotes'
    paginate_by = 50
    
    def get(self, request, *args, **kwargs):
        # تسجيل النشاط
        try:
            from core.signals import log_user_activity
            log_user_activity(
                request,
                'view',
                None,
                _('عرض كشف مذكرات الدائن')
            )
        except Exception:
            pass
        
        return super().get(request, *args, **kwargs)
    
    def get_queryset(self):
        queryset = SalesCreditNote.objects.select_related('customer', 'created_by').all()
        
        # فلترة حسب التاريخ
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        customer = self.request.GET.get('customer')
        
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
        if customer:
            queryset = queryset.filter(customer_id=customer)
            
        return queryset.order_by('-date', '-note_number')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # إضافة إجماليات
        queryset = self.get_queryset()
        context['total_amount'] = queryset.aggregate(
            total=Sum('total_amount')
        )['total'] or 0
        
        context['total_count'] = queryset.count()
        
        # إضافة قائمة العملاء للفلترة
        from customers.models import CustomerSupplier
        context['customers'] = CustomerSupplier.objects.filter(
            type__in=['customer', 'both']
        ).order_by('name')
        
        # إضافة قيم الفلترة الحالية
        context['filters'] = {
            'date_from': self.request.GET.get('date_from', ''),
            'date_to': self.request.GET.get('date_to', ''),
            'customer': self.request.GET.get('customer', ''),
        }
        
        try:
            company_settings = CompanySettings.objects.first()
            if company_settings and company_settings.base_currency:
                context['base_currency'] = company_settings.base_currency
        except Exception:
            pass
            
        return context
