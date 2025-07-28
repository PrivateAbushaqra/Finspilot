from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, View
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
from .models import Currency, CompanySettings
import json

class SettingsView(LoginRequiredMixin, TemplateView):
    template_name = 'settings/index.html'

class DocumentSequenceView(LoginRequiredMixin, TemplateView):
    template_name = 'settings/document_sequences.html'
    
    def get_context_data(self, **kwargs):
        from core.models import DocumentSequence
        
        context = super().get_context_data(**kwargs)
        
        # الحصول على جميع تسلسلات المستندات من قاعدة البيانات
        sequences = DocumentSequence.objects.all().order_by('document_type')
        context['sequences'] = sequences
        
        return context

class CompanySettingsView(LoginRequiredMixin, TemplateView):
    template_name = 'settings/company.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # الحصول على إعدادات الشركة
        company_settings = CompanySettings.objects.first()
        context['company_settings'] = company_settings
        
        # الحصول على العملة الأساسية المختارة فقط (بدون إنشاء عملة افتراضية)
        base_currency = None
        if company_settings and company_settings.base_currency:
            base_currency = company_settings.base_currency
        else:
            base_currency = Currency.get_base_currency()
        
        # الحصول على جميع العملات النشطة
        context['currencies'] = Currency.get_active_currencies()
        context['base_currency'] = base_currency
        
        return context
    
    def post(self, request, *args, **kwargs):
        try:
            with transaction.atomic():
                # الحصول على إعدادات الشركة (أو إنشاؤها إذا لم تكن موجودة)
                try:
                    company_settings = CompanySettings.objects.get(pk=1)
                except CompanySettings.DoesNotExist:
                    company_settings = CompanySettings.objects.create(
                        pk=1,
                        company_name='Finspilot Accounting Software',
                        base_currency=Currency.get_base_currency() or Currency.objects.first()
                    )
                
                # تحديث بيانات الشركة
                company_settings.company_name = request.POST.get('company_name', '')
                company_settings.company_name_en = request.POST.get('company_name_en', '')
                company_settings.tax_number = request.POST.get('tax_number', '')
                company_settings.commercial_registration = request.POST.get('commercial_registration', '')
                company_settings.phone = request.POST.get('phone', '')
                company_settings.email = request.POST.get('email', '')
                company_settings.address = request.POST.get('address', '')
                company_settings.website = request.POST.get('website', '')
                
                # تحديث العملة الأساسية
                base_currency_id = request.POST.get('base_currency')
                if base_currency_id:
                    try:
                        base_currency = Currency.objects.get(id=base_currency_id)
                        company_settings.base_currency = base_currency
                        # تحديث العملة الأساسية في نموذج العملة أيضاً
                        Currency.objects.filter(is_base_currency=True).update(is_base_currency=False)
                        base_currency.is_base_currency = True
                        base_currency.save()
                    except Currency.DoesNotExist:
                        messages.error(request, 'العملة المختارة غير موجودة!')
                        return redirect('settings:company')
                
                company_settings.show_currency_symbol = 'show_currency_symbol' in request.POST
                
                # إعدادات الجلسة والأمان (فقط للـ superuser)
                if request.user.is_superuser:
                    # تحديث إعدادات الجلسة
                    session_timeout = request.POST.get('session_timeout_minutes')
                    if session_timeout:
                        try:
                            timeout_value = int(session_timeout)
                            if 5 <= timeout_value <= 1440:  # التحقق من النطاق المسموح
                                company_settings.session_timeout_minutes = timeout_value
                        except (ValueError, TypeError):
                            pass
                    
                    # تحديث checkbox settings
                    company_settings.enable_session_timeout = 'enable_session_timeout' in request.POST
                    company_settings.logout_on_browser_close = 'logout_on_browser_close' in request.POST
                    
                    company_settings.enable_session_timeout = 'enable_session_timeout' in request.POST
                    company_settings.logout_on_browser_close = 'logout_on_browser_close' in request.POST
                
                # حفظ الشعار إذا تم رفعه
                if 'logo' in request.FILES:
                    company_settings.logo = request.FILES['logo']
                
                # حفظ الإعدادات
                company_settings.save()
                messages.success(request, 'تم حفظ إعدادات الشركة بنجاح!')
                
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء حفظ الإعدادات: {str(e)}')
        
        return redirect('settings:company')


class CurrencyListView(LoginRequiredMixin, TemplateView):
    template_name = 'settings/currency_list.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['currencies'] = Currency.objects.all().order_by('-is_base_currency', 'name')
        context['base_currency'] = Currency.get_base_currency()
        return context


class CurrencyAddView(LoginRequiredMixin, View):
    template_name = 'settings/currency_add.html'
    
    def get(self, request, *args, **kwargs):
        context = {
            'currency_choices': Currency.CURRENCY_CHOICES
        }
        return render(request, self.template_name, context)
    
    def post(self, request, *args, **kwargs):
        try:
            with transaction.atomic():
                code = request.POST.get('code')
                name = request.POST.get('name', '')
                symbol = request.POST.get('symbol', '')
                exchange_rate_str = request.POST.get('exchange_rate', '1.0000')
                decimal_places_str = request.POST.get('decimal_places', '2')
                is_base_currency = 'is_base_currency' in request.POST
                is_active = 'is_active' in request.POST
                
                # التحقق من عدم وجود العملة مسبقاً
                if Currency.objects.filter(code=code).exists():
                    messages.error(request, f'العملة {code} موجودة بالفعل!')
                    return redirect('settings:currency_add')
                
                # التحقق من صحة سعر الصرف
                try:
                    exchange_rate = float(exchange_rate_str) if exchange_rate_str.strip() else 1.0
                    if exchange_rate <= 0:
                        messages.error(request, 'سعر الصرف يجب أن يكون أكبر من صفر!')
                        return redirect('settings:currency_add')
                except ValueError:
                    messages.error(request, 'سعر الصرف يجب أن يكون رقماً صحيحاً!')
                    return redirect('settings:currency_add')
                
                # التحقق من صحة عدد الأرقام العشرية
                try:
                    decimal_places = int(decimal_places_str) if decimal_places_str.strip() else 2
                    if decimal_places < 0 or decimal_places > 6:
                        messages.error(request, 'عدد الأرقام العشرية يجب أن يكون بين 0 و 6!')
                        return redirect('settings:currency_add')
                except ValueError:
                    messages.error(request, 'عدد الأرقام العشرية يجب أن يكون رقماً صحيحاً!')
                    return redirect('settings:currency_add')
                
                # إنشاء العملة الجديدة
                currency = Currency.objects.create(
                    code=code,
                    name=name,
                    symbol=symbol,
                    exchange_rate=exchange_rate,
                    is_base_currency=is_base_currency,
                    is_active=is_active,
                    decimal_places=decimal_places
                )
                
                messages.success(request, f'تم إضافة العملة {currency.name} بنجاح!')
                return redirect('settings:currency_list')
                
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء إضافة العملة: {str(e)}')
            return redirect('settings:currency_add')


class CurrencyEditView(LoginRequiredMixin, View):
    template_name = 'settings/currency_edit.html'
    
    def get(self, request, currency_id, *args, **kwargs):
        currency = get_object_or_404(Currency, id=currency_id)
        context = {
            'currency': currency,
            'currency_choices': Currency.CURRENCY_CHOICES
        }
        return render(request, self.template_name, context)
    
    def post(self, request, currency_id, *args, **kwargs):
        try:
            with transaction.atomic():
                currency = get_object_or_404(Currency, id=currency_id)
                
                # الحصول على البيانات من النموذج
                name = request.POST.get('name', currency.name)
                symbol = request.POST.get('symbol', currency.symbol)
                exchange_rate_str = request.POST.get('exchange_rate', str(currency.exchange_rate))
                decimal_places_str = request.POST.get('decimal_places', str(currency.decimal_places))
                is_base_currency = 'is_base_currency' in request.POST
                is_active = 'is_active' in request.POST
                
                # التحقق من صحة سعر الصرف
                try:
                    exchange_rate = float(exchange_rate_str) if exchange_rate_str.strip() else currency.exchange_rate
                    if exchange_rate <= 0:
                        messages.error(request, 'سعر الصرف يجب أن يكون أكبر من صفر!')
                        return redirect('settings:currency_edit', currency_id=currency_id)
                except ValueError:
                    messages.error(request, 'سعر الصرف يجب أن يكون رقماً صحيحاً!')
                    return redirect('settings:currency_edit', currency_id=currency_id)
                
                # التحقق من صحة عدد الأرقام العشرية
                try:
                    decimal_places = int(decimal_places_str) if decimal_places_str.strip() else currency.decimal_places
                    if decimal_places < 0 or decimal_places > 6:
                        messages.error(request, 'عدد الأرقام العشرية يجب أن يكون بين 0 و 6!')
                        return redirect('settings:currency_edit', currency_id=currency_id)
                except ValueError:
                    messages.error(request, 'عدد الأرقام العشرية يجب أن يكون رقماً صحيحاً!')
                    return redirect('settings:currency_edit', currency_id=currency_id)
                
                # تحديث بيانات العملة
                currency.name = name
                currency.symbol = symbol
                currency.exchange_rate = exchange_rate
                currency.is_base_currency = is_base_currency
                currency.is_active = is_active
                currency.decimal_places = decimal_places
                
                currency.save()
                
                messages.success(request, f'تم تحديث العملة {currency.name} بنجاح!')
                return redirect('settings:currency_list')
                
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء تحديث العملة: {str(e)}')
            return redirect('settings:currency_edit', currency_id=currency_id)


class CurrencyDeleteView(LoginRequiredMixin, View):
    def post(self, request, currency_id, *args, **kwargs):
        try:
            currency = get_object_or_404(Currency, id=currency_id)
            
            # التحقق من أن العملة ليست العملة الأساسية
            if currency.is_base_currency:
                messages.error(request, 'لا يمكن حذف العملة الأساسية!')
                return redirect('settings:currency_list')
            
            currency_name = currency.name
            currency.delete()
            
            messages.success(request, f'تم حذف العملة {currency_name} بنجاح!')
            
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء حذف العملة: {str(e)}')
        
        return redirect('settings:currency_list')


class SetBaseCurrencyView(LoginRequiredMixin, View):
    def post(self, request, currency_id, *args, **kwargs):
        try:
            with transaction.atomic():
                currency = get_object_or_404(Currency, id=currency_id)
                
                # إلغاء العملة الأساسية السابقة
                Currency.objects.filter(is_base_currency=True).update(is_base_currency=False)
                
                # تعيين العملة الجديدة كعملة أساسية
                currency.is_base_currency = True
                currency.exchange_rate = 1.0000  # العملة الأساسية دائماً سعر صرفها 1
                currency.save()
                
                # تحديث إعدادات الشركة
                company_settings = CompanySettings.objects.first()
                if company_settings:
                    company_settings.base_currency = currency
                    company_settings.save()
                
                messages.success(request, f'تم تعيين {currency.name} كعملة أساسية!')
                
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء تعيين العملة الأساسية: {str(e)}')
        
        return redirect('settings:currency_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # الحصول على إعدادات الشركة أو إنشاء إعدادات افتراضية
        company_settings = CompanySettings.objects.first()
        context['company_settings'] = company_settings
        
        # الحصول على جميع العملات النشطة
        context['currencies'] = Currency.get_active_currencies()
        context['base_currency'] = Currency.get_base_currency()
        
        return context
    
    def post(self, request, *args, **kwargs):
        try:
            with transaction.atomic():
                # الحصول على أو إنشاء إعدادات الشركة
                company_settings, created = CompanySettings.objects.get_or_create(
                    pk=1,
                    defaults={
                        'company_name': 'Finspilot Accounting Software',
                        'base_currency': Currency.get_base_currency()
                    }
                )
                
                # تحديث بيانات الشركة
                company_settings.company_name = request.POST.get('company_name', '')
                company_settings.company_name_en = request.POST.get('company_name_en', '')
                company_settings.tax_number = request.POST.get('tax_number', '')
                company_settings.commercial_registration = request.POST.get('commercial_registration', '')
                company_settings.phone = request.POST.get('phone', '')
                company_settings.email = request.POST.get('email', '')
                company_settings.address = request.POST.get('address', '')
                company_settings.website = request.POST.get('website', '')
                
                # تحديث العملة الأساسية
                base_currency_id = request.POST.get('base_currency')
                if base_currency_id:
                    try:
                        base_currency = Currency.objects.get(id=base_currency_id)
                        company_settings.base_currency = base_currency
                        # تحديث العملة الأساسية في نموذج العملة أيضاً
                        Currency.objects.filter(is_base_currency=True).update(is_base_currency=False)
                        base_currency.is_base_currency = True
                        base_currency.save()
                    except Currency.DoesNotExist:
                        messages.error(request, 'العملة المختارة غير موجودة!')
                        return redirect('settings:company')
                
                company_settings.show_currency_symbol = 'show_currency_symbol' in request.POST
                
                # حفظ الشعار إذا تم رفعه
                if 'logo' in request.FILES:
                    company_settings.logo = request.FILES['logo']
                
                company_settings.save()
                
                messages.success(request, 'تم حفظ إعدادات الشركة بنجاح!')
                
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء حفظ الإعدادات: {str(e)}')
        
        return redirect('settings:company')


class DocumentSequenceEditView(LoginRequiredMixin, View):
    template_name = 'settings/document_sequence_edit.html'
    
    def get(self, request, *args, **kwargs):
        from core.models import DocumentSequence
        
        seq_id = kwargs.get('seq_id')
        
        try:
            sequence = DocumentSequence.objects.get(id=seq_id)
        except DocumentSequence.DoesNotExist:
            messages.error(request, 'التسلسل المطلوب غير موجود!')
            return redirect('settings:document_sequences')
        
        context = {
            'sequence': sequence,
            'document_types': DocumentSequence.DOCUMENT_TYPES
        }
        return render(request, self.template_name, context)
    
    def post(self, request, *args, **kwargs):
        from core.models import DocumentSequence
        
        seq_id = kwargs.get('seq_id')
        
        try:
            sequence = DocumentSequence.objects.get(id=seq_id)
        except DocumentSequence.DoesNotExist:
            messages.error(request, 'التسلسل المطلوب غير موجود!')
            return redirect('settings:document_sequences')
        
        # استلام البيانات من النموذج
        document_type = request.POST.get('document_type', '').strip()
        prefix = request.POST.get('prefix', '').strip()
        current_number = request.POST.get('current_number', '1')
        digits = request.POST.get('digits', '6')
        
        # إعداد السياق لحالات الخطأ
        context = {
            'sequence': sequence,
            'document_types': DocumentSequence.DOCUMENT_TYPES
        }
        
        # التحقق من صحة البيانات
        try:
            current_number = int(current_number)
            if current_number < 1:
                raise ValueError
        except ValueError:
            messages.error(request, 'الرقم الحالي يجب أن يكون رقماً صحيحاً أكبر من 0!')
            return render(request, self.template_name, context)
        
        try:
            digits = int(digits)
            if digits < 1 or digits > 10:
                raise ValueError
        except ValueError:
            messages.error(request, 'عدد الخانات يجب أن يكون بين 1 و 10!')
            return render(request, self.template_name, context)
        
        if not document_type:
            messages.error(request, 'نوع المستند مطلوب!')
            return render(request, self.template_name, context)
        
        if not prefix:
            messages.error(request, 'البادئة مطلوبة!')
            return render(request, self.template_name, context)
        
        # التحقق من أن نوع المستند صالح
        valid_types = [choice[0] for choice in DocumentSequence.DOCUMENT_TYPES]
        if document_type not in valid_types:
            messages.error(request, 'نوع المستند المختار غير صالح!')
            return render(request, self.template_name, context)
        
        # التحقق من عدم تكرار نوع المستند (إلا إذا كان نفس التسلسل)
        if (document_type != sequence.document_type and 
            DocumentSequence.objects.filter(document_type=document_type).exists()):
            document_type_name = dict(DocumentSequence.DOCUMENT_TYPES).get(document_type, document_type)
            messages.error(request, f'تسلسل "{document_type_name}" موجود بالفعل!')
            return render(request, self.template_name, context)
        
        # تحديث التسلسل
        try:
            sequence.document_type = document_type
            sequence.prefix = prefix
            sequence.current_number = current_number
            sequence.digits = digits
            sequence.save()
            
            document_type_name = dict(DocumentSequence.DOCUMENT_TYPES).get(document_type, document_type)
            messages.success(request, f'تم تحديث تسلسل "{document_type_name}" بنجاح!')
            return redirect('settings:document_sequences')
            
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء تحديث التسلسل: {str(e)}')
            return render(request, self.template_name, context)


class DocumentSequenceAddView(LoginRequiredMixin, View):
    template_name = 'settings/document_sequence_add.html'
    
    def get(self, request, *args, **kwargs):
        from core.models import DocumentSequence
        
        # تمرير أنواع المستندات من النموذج
        context = {
            'document_types': DocumentSequence.DOCUMENT_TYPES
        }
        return render(request, self.template_name, context)
    
    def post(self, request, *args, **kwargs):
        from core.models import DocumentSequence
        
        document_type = request.POST.get('document_type', '').strip()
        prefix = request.POST.get('prefix', '').strip()
        starting_number = request.POST.get('starting_number', '1')
        digits = request.POST.get('digits', '6')
        
        # إعداد السياق لحالات الخطأ
        context = {'document_types': DocumentSequence.DOCUMENT_TYPES}
        
        # التحقق من صحة البيانات
        try:
            starting_number = int(starting_number)
            if starting_number < 1:
                raise ValueError
        except ValueError:
            messages.error(request, 'الرقم البدائي يجب أن يكون رقماً صحيحاً أكبر من 0!')
            return render(request, self.template_name, context)
        
        try:
            digits = int(digits)
            if digits < 1 or digits > 10:
                raise ValueError
        except ValueError:
            messages.error(request, 'عدد الخانات يجب أن يكون بين 1 و 10!')
            return render(request, self.template_name, context)
        
        if not document_type:
            messages.error(request, 'نوع المستند مطلوب!')
            return render(request, self.template_name, context)
        
        if not prefix:
            messages.error(request, 'البادئة مطلوبة!')
            return render(request, self.template_name, context)
        
        # التحقق من أن نوع المستند صالح
        valid_types = [choice[0] for choice in DocumentSequence.DOCUMENT_TYPES]
        if document_type not in valid_types:
            messages.error(request, 'نوع المستند المختار غير صالح!')
            return render(request, self.template_name, context)
        
        # التحقق من عدم تكرار نوع المستند
        if DocumentSequence.objects.filter(document_type=document_type).exists():
            document_type_name = dict(DocumentSequence.DOCUMENT_TYPES).get(document_type, document_type)
            messages.error(request, f'تسلسل "{document_type_name}" موجود بالفعل!')
            return render(request, self.template_name, context)
        
        # إنشاء التسلسل الجديد
        try:
            sequence = DocumentSequence.objects.create(
                document_type=document_type,
                prefix=prefix,
                digits=digits,
                current_number=starting_number
            )
            
            # الحصول على اسم نوع المستند للعرض
            document_type_name = dict(DocumentSequence.DOCUMENT_TYPES).get(document_type, document_type)
            
            messages.success(request, f'تم إضافة تسلسل "{document_type_name}" بنجاح!')
            return redirect('settings:document_sequences')
            
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء إنشاء التسلسل: {str(e)}')
            return render(request, self.template_name, context)

# النسخة المكررة من الكلاسات أعلاه تم حذفها

class DocumentSequenceDeleteView(LoginRequiredMixin, View):
    
    def post(self, request, *args, **kwargs):
        from core.models import DocumentSequence
        
        seq_id = kwargs.get('seq_id')
        
        try:
            sequence = DocumentSequence.objects.get(id=seq_id)
        except DocumentSequence.DoesNotExist:
            messages.error(request, 'التسلسل المطلوب حذفه غير موجود!')
            return redirect('settings:document_sequences')
        
        # التحقق من أن التسلسل غير مستخدم (يمكن إضافة المزيد من التحققات هنا)
        document_type_name = sequence.get_document_type_display()
        
        try:
            sequence.delete()
            messages.success(request, f'تم حذف تسلسل "{document_type_name}" بنجاح!')
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء حذف التسلسل: {str(e)}')
        
        return redirect('settings:document_sequences')


def get_company_currency_ajax(request):
    """API للحصول على معلومات العملة الأساسية للشركة"""
    try:
        company_settings = CompanySettings.objects.first()
        
        if not company_settings or not company_settings.base_currency:
            return JsonResponse({
                'error': 'إعدادات الشركة أو العملة الأساسية غير موجودة'
            }, status=404)
        
        currency = company_settings.base_currency
        
        data = {
            'code': currency.code,
            'name': currency.name,
            'symbol': currency.symbol,
            'show_symbol': company_settings.show_currency_symbol,
        }
        
        return JsonResponse(data)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
