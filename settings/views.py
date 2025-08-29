from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView, View
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from .models import Currency
from core.models import CompanySettings
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
        
        # التحقق من صلاحية التعديل
        context['can_edit'] = self.request.user.has_perm('core.change_documentsequence') or self.request.user.is_superuser
        
        return context

class CompanySettingsView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'settings/company.html'
    
    def test_func(self):
        """التحقق من أن المستخدم لديه صلاحية الوصول لإعدادات الشركة"""
        return self.request.user.has_system_management_permission()
    
    def handle_no_permission(self):
        """في حالة عدم وجود صلاحية، إعادة توجيه للصفحة الرئيسية مع رسالة خطأ"""
        messages.error(self.request, 'ليس لديك صلاحية للوصول لإعدادات الشركة.')
        return redirect('settings:index')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # الحصول على إعدادات الشركة
        company_settings = CompanySettings.objects.first()
        context['company_settings'] = company_settings
        
        # الحصول على العملة الأساسية المختارة أو العملة من إعدادات الشركة
        base_currency = None
        if company_settings and company_settings.currency:
            # محاولة العثور على العملة بناءً على رمزها
            try:
                base_currency = Currency.objects.get(code=company_settings.currency)
            except Currency.DoesNotExist:
                base_currency = Currency.get_base_currency()
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
                    # إنشاء إعدادات شركة جديدة
                    base_currency = Currency.get_base_currency() or Currency.objects.first()
                    company_settings = CompanySettings.objects.create(
                        pk=1,
                        company_name='Finspilot Accounting Software',
                        currency=base_currency.code if base_currency else 'JOD'
                    )
                
                # تحديث بيانات الشركة
                old_company_name = company_settings.company_name
                company_settings.company_name = request.POST.get('company_name', '')
                company_settings.tax_number = request.POST.get('tax_number', '')
                company_settings.phone = request.POST.get('phone', '')
                company_settings.email = request.POST.get('email', '')
                company_settings.address = request.POST.get('address', '')
                
                # تسجيل النشاط إذا تغير اسم الشركة
                if old_company_name != company_settings.company_name:
                    from core.models import AuditLog
                    AuditLog.objects.create(
                        user=request.user,
                        action_type='update',
                        content_type='CompanySettings',
                        object_id=company_settings.pk,
                        description=f'تم تحديث اسم الشركة من "{old_company_name}" إلى "{company_settings.company_name}"'
                    )
                
                # تحديث العملة الأساسية
                base_currency_id = request.POST.get('base_currency')
                if base_currency_id:
                    try:
                        base_currency = Currency.objects.get(id=base_currency_id)
                        # تحديث حقل currency في إعدادات الشركة برمز العملة
                        company_settings.currency = base_currency.code
                        # تحديث العملة الأساسية في نموذج العملة أيضاً
                        Currency.objects.filter(is_base_currency=True).update(is_base_currency=False)
                        base_currency.is_base_currency = True
                        base_currency.save()
                    except Currency.DoesNotExist:
                        messages.error(request, 'العملة المختارة غير موجودة!')
                        return redirect('settings:company')
                
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
    
    def dispatch(self, request, *args, **kwargs):
        """التحقق من الصلاحيات قبل السماح بالوصول"""
        if not (request.user.has_perm('core.change_documentsequence') or request.user.is_superuser):
            messages.error(request, _('ليس لديك صلاحية لتعديل تسلسل المستندات!'))
            return redirect('settings:document_sequences')
        return super().dispatch(request, *args, **kwargs)
    
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
            old_values = {
                'document_type': sequence.document_type,
                'prefix': sequence.prefix,
                'current_number': sequence.current_number,
                'digits': sequence.digits
            }
            
            sequence.document_type = document_type
            sequence.prefix = prefix
            sequence.current_number = current_number
            sequence.digits = digits
            sequence.save()
            
            # تسجيل النشاط في سجل الأنشطة
            from core.signals import log_activity
            document_type_name = dict(DocumentSequence.DOCUMENT_TYPES).get(document_type, document_type)
            description = f"تحديث تسلسل المستند: {document_type_name} - البادئة: {prefix}"
            log_activity(request.user, 'update', sequence, description, request)
            
            messages.success(request, f'تم تحديث تسلسل "{document_type_name}" بنجاح!')
            return redirect('settings:document_sequences')
            
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء تحديث التسلسل: {str(e)}')
            return render(request, self.template_name, context)


class DocumentSequenceAddView(LoginRequiredMixin, View):
    template_name = 'settings/document_sequence_add.html'
    
    def dispatch(self, request, *args, **kwargs):
        """التحقق من الصلاحيات قبل السماح بالوصول"""
        if not (request.user.has_perm('core.add_documentsequence') or request.user.is_superuser):
            messages.error(request, _('ليس لديك صلاحية لإضافة تسلسل مستندات جديد!'))
            return redirect('settings:document_sequences')
        return super().dispatch(request, *args, **kwargs)
    
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
            
            # تسجيل النشاط في سجل الأنشطة
            from core.signals import log_activity
            document_type_name = dict(DocumentSequence.DOCUMENT_TYPES).get(document_type, document_type)
            description = f"إضافة تسلسل مستند جديد: {document_type_name} - البادئة: {prefix}"
            log_activity(request.user, 'create', sequence, description, request)
            
            messages.success(request, f'تم إضافة تسلسل "{document_type_name}" بنجاح!')
            return redirect('settings:document_sequences')
            
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء إنشاء التسلسل: {str(e)}')
            return render(request, self.template_name, context)

# النسخة المكررة من الكلاسات أعلاه تم حذفها

class DocumentSequenceDeleteView(LoginRequiredMixin, View):
    
    def dispatch(self, request, *args, **kwargs):
        """التحقق من الصلاحيات قبل السماح بالوصول"""
        if not (request.user.has_perm('core.delete_documentsequence') or request.user.is_superuser):
            messages.error(request, _('ليس لديك صلاحية لحذف تسلسل المستندات!'))
            return redirect('settings:document_sequences')
        return super().dispatch(request, *args, **kwargs)
    
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
            # تسجيل النشاط قبل الحذف
            from core.signals import log_activity
            description = f"حذف تسلسل المستند: {document_type_name} - البادئة: {sequence.prefix}"
            log_activity(request.user, 'delete', sequence, description, request)
            
            sequence.delete()
            messages.success(request, f'تم حذف تسلسل "{document_type_name}" بنجاح!')
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء حذف التسلسل: {str(e)}')
        
        return redirect('settings:document_sequences')


def get_document_settings_ajax(request, document_type):
    """API endpoint للحصول على إعدادات مستند محدد"""
    try:
        from .models import DocumentPrintSettings
        
        settings = DocumentPrintSettings.objects.get(document_type=document_type, is_active=True)
        
        data = {
            'success': True,
            'settings': {
                'document_type': settings.document_type,
                'document_name_ar': settings.document_name_ar,
                'document_name_en': settings.document_name_en,
                'paper_size': settings.paper_size,
                'orientation': settings.orientation,
                'header_left_content': settings.header_left_content,
                'header_center_content': settings.header_center_content,
                'header_right_content': settings.header_right_content,
                'footer_left_content': settings.footer_left_content,
                'footer_center_content': settings.footer_center_content,
                'footer_right_content': settings.footer_right_content,
                'show_logo': settings.show_logo,
                'logo_position': settings.logo_position,
                'show_company_info': settings.show_company_info,
                'show_date_time': settings.show_date_time,
                'show_page_numbers': settings.show_page_numbers,
            }
        }
        
        return JsonResponse(data)
        
    except DocumentPrintSettings.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'إعدادات المستند غير موجودة'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


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


class SuperadminManagementView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """صفحة إدارة النظام - خاصة بالسوبر أدمين والمدراء"""
    template_name = 'settings/superadmin_management.html'
    
    def test_func(self):
        """السماح فقط لمن يملك إذن إدارة النظام صراحة أو سوبر يوزر"""
        user = self.request.user
        # السماح للسوبر يوزر دائماً
        if user.is_superuser:
            return True
        # السماح فقط لمن لديه الإذن الصريح
        return user.has_perm('users.can_access_system_management')

    def handle_no_permission(self):
        """في حالة عدم وجود صلاحية، إعادة توجيه للصفحة الرئيسية مع رسالة خطأ"""
        messages.error(self.request, 'ليس لديك صلاحية للوصول لهذه الصفحة. مخصصة للسوبر أدمين فقط.')
        return redirect('settings:index')

    def get_context_data(self, **kwargs):
        from .models import SuperadminSettings
        
        context = super().get_context_data(**kwargs)
        
        # الحصول على إعدادات السوبر أدمين
        superadmin_settings = SuperadminSettings.get_settings()
        context['superadmin_settings'] = superadmin_settings
        
        # الحصول على إعدادات الشركة (من core.models)
        company_settings = CompanySettings.get_settings()
        context['company_settings'] = company_settings
        
        return context
    
    def post(self, request):
        from .models import SuperadminSettings
        
        try:
            with transaction.atomic():
                # الحصول على أو إنشاء إعدادات السوبر أدمين
                settings = SuperadminSettings.get_settings()
                old_settings = {
                    'system_title': settings.system_title,
                    'system_subtitle': settings.system_subtitle,
                    'primary_color': settings.primary_color,
                    'secondary_color': settings.secondary_color,
                    'accent_color': settings.accent_color,
                    'background_opacity': str(settings.background_opacity),
                    'show_company_info': settings.show_company_info,
                }
                
                # تحديث إعدادات السوبر أدمين
                settings.system_title = request.POST.get('system_title', settings.system_title)
                settings.system_subtitle = request.POST.get('system_subtitle', settings.system_subtitle)
                settings.primary_color = request.POST.get('primary_color', settings.primary_color)
                settings.secondary_color = request.POST.get('secondary_color', settings.secondary_color)
                settings.accent_color = request.POST.get('accent_color', settings.accent_color)
                settings.show_company_info = request.POST.get('show_company_info') == 'on'
                
                # تحديث شفافية الخلفية
                try:
                    opacity = float(request.POST.get('background_opacity', settings.background_opacity))
                    if 0.1 <= opacity <= 1.0:
                        settings.background_opacity = opacity
                except (ValueError, TypeError):
                    pass
                
                # تحديث الصور
                if 'app_logo' in request.FILES:
                    settings.app_logo = request.FILES['app_logo']
                
                if 'background_image' in request.FILES:
                    settings.background_image = request.FILES['background_image']
                
                # تسجيل من قام بالتحديث
                settings.updated_by = request.user
                settings.save()
                
                # تسجيل النشاط - إعدادات السوبر أدمين
                from core.signals import log_activity
                changes = []
                new_settings = {
                    'system_title': settings.system_title,
                    'system_subtitle': settings.system_subtitle,
                    'primary_color': settings.primary_color,
                    'secondary_color': settings.secondary_color,
                    'accent_color': settings.accent_color,
                    'background_opacity': str(settings.background_opacity),
                    'show_company_info': settings.show_company_info,
                }
                
                for key, old_value in old_settings.items():
                    new_value = new_settings[key]
                    if str(old_value) != str(new_value):
                        changes.append(f"{key}: {old_value} → {new_value}")
                
                if changes or 'app_logo' in request.FILES or 'background_image' in request.FILES:
                    if 'app_logo' in request.FILES:
                        changes.append(f"تم تحديث شعار النظام")
                    if 'background_image' in request.FILES:
                        changes.append(f"تم تحديث صورة الخلفية")
                    
                    description = f"تحديث إعدادات السوبر أدمين: {', '.join(changes)}"
                    log_activity(request.user, 'update', settings, description, request)
                
                # تحديث إعدادات الشركة إذا كانت موجودة (استخدام core.models.CompanySettings)
                company_settings = CompanySettings.get_settings()
                if any([
                    request.POST.get('company_name'),
                    request.POST.get('email'),
                    request.POST.get('phone'),
                    request.POST.get('address'),
                    request.POST.get('website'),
                    'company_logo' in request.FILES
                ]):
                    company_changes = []
                    
                    if request.POST.get('company_name') and request.POST.get('company_name') != company_settings.company_name:
                        old_name = company_settings.company_name
                        company_settings.company_name = request.POST.get('company_name')
                        company_changes.append(f"اسم الشركة: {old_name} → {company_settings.company_name}")
                    
                    if request.POST.get('email') and request.POST.get('email') != company_settings.email:
                        old_email = company_settings.email
                        company_settings.email = request.POST.get('email')
                        company_changes.append(f"البريد الإلكتروني: {old_email} → {company_settings.email}")
                    
                    if request.POST.get('phone') and request.POST.get('phone') != company_settings.phone:
                        old_phone = company_settings.phone
                        company_settings.phone = request.POST.get('phone')
                        company_changes.append(f"الهاتف: {old_phone} → {company_settings.phone}")
                    
                    if request.POST.get('address') and request.POST.get('address') != company_settings.address:
                        old_address = company_settings.address
                        company_settings.address = request.POST.get('address')
                        company_changes.append(f"العنوان: {old_address} → {company_settings.address}")
                    
                    if request.POST.get('website') and request.POST.get('website') != company_settings.website:
                        old_website = company_settings.website
                        company_settings.website = request.POST.get('website')
                        company_changes.append(f"الموقع الإلكتروني: {old_website} → {company_settings.website}")
                    
                    if 'company_logo' in request.FILES:
                        company_settings.logo = request.FILES['company_logo']
                        company_changes.append("تم تحديث شعار الشركة للطباعة")
                    
                    company_settings.save()
                    
                    # تسجيل النشاط - إعدادات الشركة
                    if company_changes:
                        description = f"تحديث إعدادات الشركة من صفحة السوبر أدمين: {', '.join(company_changes)}"
                        log_activity(request.user, 'update', company_settings, description, request)
                
                messages.success(request, 'تم تحديث إعدادات النظام بنجاح!')
                
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء تحديث الإعدادات: {str(e)}')
        
        # معالجة إعدادات الجلسة والأمان - ضمن transaction منفصل
        try:
            with transaction.atomic():
                company_settings = CompanySettings.get_settings()
                
                if company_settings:
                    session_changes = []
                    
                    # تحديث إعدادات الجلسة
                    session_timeout = request.POST.get('session_timeout_minutes')
                    
                    if session_timeout:
                        try:
                            timeout_value = int(session_timeout)
                            
                            if 5 <= timeout_value <= 1440:  # التحقق من النطاق المسموح
                                old_timeout = company_settings.session_timeout_minutes
                                company_settings.session_timeout_minutes = timeout_value
                                # تسجيل النشاط إذا تغيرت القيمة
                                if old_timeout != timeout_value:
                                    session_changes.append(f"مدة انتهاء الجلسة: {old_timeout} → {timeout_value} دقيقة")
                            else:
                                messages.error(request, 'مدة انتهاء الجلسة يجب أن تكون بين 5 و 1440 دقيقة')
                                return redirect('settings:superadmin_management')
                        except ValueError as e:
                            messages.error(request, 'قيمة غير صالحة لمدة انتهاء الجلسة')
                            return redirect('settings:superadmin_management')
                    
                    # تحديث إعداد تفعيل انتهاء الجلسة
                    old_enable_timeout = company_settings.enable_session_timeout
                    company_settings.enable_session_timeout = 'enable_session_timeout' in request.POST
                    
                    # تحديث إعداد تسجيل الخروج عند إغلاق المتصفح
                    old_logout_on_close = company_settings.logout_on_browser_close
                    company_settings.logout_on_browser_close = 'logout_on_browser_close' in request.POST
                    
                    # حفظ التغييرات
                    company_settings.save()
                    
                    # تسجيل النشاط للتغييرات في إعدادات الجلسة
                    from core.models import AuditLog
                    
                    if session_changes:
                        AuditLog.objects.create(
                            user=request.user,
                            action_type='update',
                            content_type='CompanySettings',
                            object_id=company_settings.pk,
                            description=f'تم تحديث إعدادات الجلسة: {", ".join(session_changes)}'
                        )
                    
                    if old_enable_timeout != company_settings.enable_session_timeout:
                        status = 'تم تفعيل' if company_settings.enable_session_timeout else 'تم إلغاء تفعيل'
                        AuditLog.objects.create(
                            user=request.user,
                            action_type='update',
                            content_type='CompanySettings',
                            object_id=company_settings.pk,
                            description=f'{status} انتهاء الجلسة التلقائي'
                        )
                        session_changes.append(f"تفعيل انتهاء الجلسة التلقائي: {status}")
                    
                    if old_logout_on_close != company_settings.logout_on_browser_close:
                        status = 'تم تفعيل' if company_settings.logout_on_browser_close else 'تم إلغاء تفعيل'
                        AuditLog.objects.create(
                            user=request.user,
                            action_type='update',
                            content_type='CompanySettings',
                            object_id=company_settings.pk,
                            description=f'{status} تسجيل الخروج عند إغلاق المتصفح'
                        )
                        session_changes.append(f"تسجيل الخروج عند إغلاق المتصفح: {status}")
                    
                    # إشعار بنجاح التحديث
                    if session_changes:
                        messages.success(request, f'تم تحديث إعدادات الأمان والجلسة: {", ".join(session_changes)}')
                    else:
                        messages.success(request, 'تم حفظ الإعدادات بنجاح!')
        
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء تحديث إعدادات الجلسة: {str(e)}')
            import traceback
            print(f"خطأ في تحديث إعدادات الجلسة: {str(e)}")
            print(traceback.format_exc())
        
        return redirect('settings:superadmin_management')


class DocumentPrintSettingsView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """عرض إدارة إعدادات طباعة المستندات"""
    template_name = 'settings/document_print_settings.html'
    
    def test_func(self):
        """التحقق من صلاحيات المستخدم"""
        return self.request.user.has_system_management_permission()
    
    def handle_no_permission(self):
        messages.error(self.request, _('ليس لديك صلاحية للوصول لإعدادات الطباعة.'))
        return redirect('settings:index')
    
    def get_context_data(self, **kwargs):
        from .models import DocumentPrintSettings, CompanySettings
        
        context = super().get_context_data(**kwargs)
        
        # الحصول على جميع إعدادات الطباعة
        print_settings = DocumentPrintSettings.objects.filter(is_active=True).order_by('document_name_ar')
        context['print_settings'] = print_settings
        
        # قائمة المستندات المتاحة للطباعة
        document_types = [
            {'key': 'invoice', 'name_ar': _('فاتورة مبيعات'), 'name_en': _('Sales Invoice')},
                {'key': 'credit_note', 'name_ar': _('إشعار دائن'), 'name_en': _('Credit Note')},
                {'key': 'debit_note', 'name_ar': _('إشعار مدين'), 'name_en': _('Debit Note')},
            {'key': 'purchase_order', 'name_ar': _('أمر شراء'), 'name_en': _('Purchase Order')},
            {'key': 'receipt', 'name_ar': _('إيصال استلام'), 'name_en': _('Receipt')},
            {'key': 'payment_voucher', 'name_ar': _('إذن صرف'), 'name_en': _('Payment Voucher')},
            {'key': 'journal_entry', 'name_ar': _('قيد محاسبي'), 'name_en': _('Journal Entry')},
            {'key': 'customer_statement', 'name_ar': _('كشف حساب عميل'), 'name_en': _('Customer Statement')},
            {'key': 'supplier_statement', 'name_ar': _('كشف حساب مورد'), 'name_en': _('Supplier Statement')},
            {'key': 'inventory_report', 'name_ar': _('تقرير المخزون'), 'name_en': _('Inventory Report')},
            {'key': 'financial_report', 'name_ar': _('تقرير مالي'), 'name_en': _('Financial Report')},
        ]
        context['document_types'] = document_types
        
        # الحصول على إعدادات النظام للشعار
        try:
            general_settings = CompanySettings.objects.first()
        except CompanySettings.DoesNotExist:
            general_settings = None
        context['general_settings'] = general_settings
        
        return context

    def post(self, request, *args, **kwargs):
        from .models import DocumentPrintSettings
        from core.models import AuditLog
        
        try:
            action = request.POST.get('action')
            
            if action == 'save_settings':
                document_type = request.POST.get('document_type')
                
                if not document_type:
                    messages.error(request, _('يجب تحديد نوع المستند'))
                    return redirect('settings:document_print_settings')
                
                # الحصول على الإعدادات أو إنشاء جديدة
                settings, created = DocumentPrintSettings.objects.get_or_create(
                    document_type=document_type,
                    defaults={
                        'document_name_ar': request.POST.get('document_name_ar', document_type),
                        'document_name_en': request.POST.get('document_name_en', document_type),
                        'created_by': request.user
                    }
                )
                
                # تحديث البيانات
                settings.document_name_ar = request.POST.get('document_name_ar', settings.document_name_ar)
                settings.document_name_en = request.POST.get('document_name_en', settings.document_name_en)
                settings.paper_size = request.POST.get('paper_size', 'A4')
                
                # إعدادات الرأس
                settings.header_left_content = request.POST.get('header_left_content', '')
                settings.header_center_content = request.POST.get('header_center_content', '')
                settings.header_right_content = request.POST.get('header_right_content', '')
                
                # إعدادات الشعار
                settings.show_logo = 'show_logo' in request.POST
                settings.logo_position = request.POST.get('logo_position', 'center')
                
                # إعدادات التذييل
                settings.footer_left_content = request.POST.get('footer_left_content', '')
                settings.footer_center_content = request.POST.get('footer_center_content', '')
                settings.footer_right_content = request.POST.get('footer_right_content', '')
                
                # إعدادات إضافية
                settings.show_company_info = 'show_company_info' in request.POST
                settings.show_date_time = 'show_date_time' in request.POST
                settings.show_page_numbers = 'show_page_numbers' in request.POST
                settings.is_default = 'is_default' in request.POST
                
                settings.updated_by = request.user
                settings.save()
                
                # تسجيل النشاط
                AuditLog.objects.create(
                    user=request.user,
                    action_type='update' if not created else 'create',
                    content_type='DocumentPrintSettings',
                    description=f'{"تم إنشاء" if created else "تم تحديث"} إعدادات طباعة المستند: {settings.document_name_ar}'
                )
                
                messages.success(request, _('تم حفظ إعدادات الطباعة بنجاح'))
                
            elif action == 'delete_settings':
                document_id = request.POST.get('document_id')
                
                try:
                    settings = DocumentPrintSettings.objects.get(id=document_id)
                    document_name = settings.document_name_ar
                    settings.delete()
                    
                    # تسجيل النشاط
                    AuditLog.objects.create(
                        user=request.user,
                        action_type='delete',
                        content_type='DocumentPrintSettings',
                        description=f'تم حذف إعدادات طباعة المستند: {document_name}'
                    )
                    
                    messages.success(request, _('تم حذف إعدادات الطباعة بنجاح'))
                    
                except DocumentPrintSettings.DoesNotExist:
                    messages.error(request, _('الإعدادات غير موجودة'))
        
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء حفظ الإعدادات: {str(e)}')
            import traceback
            print(f"خطأ في حفظ إعدادات الطباعة: {str(e)}")
            print(traceback.format_exc())
        
        return redirect('settings:document_print_settings')


class PrintDesignView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """عرض تصميم صفحات الطباعة المحسن"""
    template_name = 'settings/print_design.html'
    
    def test_func(self):
        """التحقق من صلاحيات المستخدم"""
        return self.request.user.has_system_management_permission()
    
    def handle_no_permission(self):
        messages.error(self.request, _('ليس لديك صلاحية للوصول لتصميم الطباعة.'))
        return redirect('settings:index')
    
    def get_context_data(self, **kwargs):
        from .models import DocumentPrintSettings, CompanySettings

        context = super().get_context_data(**kwargs)

        # الحصول على جميع إعدادات الطباعة
        print_settings = DocumentPrintSettings.objects.filter(is_active=True).order_by('document_name_ar')
        context['print_settings'] = print_settings

        # قائمة المستندات المتاحة للإضافة
        document_types = [
            {'key': 'invoice', 'name_ar': _('فاتورة مبيعات'), 'name_en': _('Sales Invoice')},
            {'key': 'credit_note', 'name_ar': _('إشعار دائن'), 'name_en': _('Credit Note')},
            {'key': 'debit_note', 'name_ar': _('إشعار مدين'), 'name_en': _('Debit Note')},
            {'key': 'purchase_order', 'name_ar': _('أمر شراء'), 'name_en': _('Purchase Order')},
            {'key': 'receipt', 'name_ar': _('إيصال استلام'), 'name_en': _('Receipt')},
            {'key': 'payment_voucher', 'name_ar': _('إذن صرف'), 'name_en': _('Payment Voucher')},
            {'key': 'journal_entry', 'name_ar': _('قيد محاسبي'), 'name_en': _('Journal Entry')},
            {'key': 'customer_statement', 'name_ar': _('كشف حساب عميل'), 'name_en': _('Customer Statement')},
            {'key': 'supplier_statement', 'name_ar': _('كشف حساب مورد'), 'name_en': _('Supplier Statement')},
            {'key': 'inventory_report', 'name_ar': _('تقرير المخزون'), 'name_en': _('Inventory Report')},
            {'key': 'financial_report', 'name_ar': _('تقرير مالي'), 'name_en': _('Financial Report')},
        ]
        context['document_types'] = document_types
        
        # قائمة المستندات الموجودة
        existing_documents = list(print_settings.values_list('document_type', flat=True))
        context['existing_documents'] = existing_documents
        
        # الحصول على إعدادات النظام للشعار
        try:
            general_settings = CompanySettings.objects.first()
        except CompanySettings.DoesNotExist:
            general_settings = None
        context['general_settings'] = general_settings
        
        return context

    def post(self, request, *args, **kwargs):
        from .models import DocumentPrintSettings
        from core.models import AuditLog
        
        try:
            action = request.POST.get('action')
            
            if action == 'save_settings':
                document_type = request.POST.get('document_type')
                
                if not document_type:
                    return JsonResponse({'success': False, 'error': 'يجب تحديد نوع المستند'})
                
                # الحصول على الإعدادات أو إنشاء جديدة
                settings, created = DocumentPrintSettings.objects.get_or_create(
                    document_type=document_type,
                    defaults={
                        'document_name_ar': request.POST.get('document_name_ar', document_type),
                        'document_name_en': request.POST.get('document_name_en', document_type),
                        'margins': 20,
                        'orientation': 'portrait',
                        'created_by': request.user
                    }
                )
                
                # تحديث البيانات
                settings.document_name_ar = request.POST.get('document_name_ar', settings.document_name_ar)
                settings.document_name_en = request.POST.get('document_name_en', settings.document_name_en)
                settings.paper_size = request.POST.get('paper_size', 'A4')
                settings.orientation = request.POST.get('orientation', 'portrait')
                
                # إعدادات الهوامش
                try:
                    margins_value = int(request.POST.get('margins', 20))
                    settings.margins = margins_value
                except (ValueError, TypeError):
                    settings.margins = 20
                
                # إعدادات الرأس
                settings.header_left_content = request.POST.get('header_left_content', '')
                settings.header_center_content = request.POST.get('header_center_content', '')
                settings.header_right_content = request.POST.get('header_right_content', '')
                
                # إعدادات الشعار
                settings.show_logo = request.POST.get('show_logo') == 'true'
                settings.logo_position = request.POST.get('logo_position', 'center')
                
                # إعدادات التذييل
                settings.footer_left_content = request.POST.get('footer_left_content', '')
                settings.footer_center_content = request.POST.get('footer_center_content', '')
                settings.footer_right_content = request.POST.get('footer_right_content', '')
                
                settings.updated_by = request.user
                settings.save()
                
                # تسجيل النشاط
                AuditLog.objects.create(
                    user=request.user,
                    action_type='update' if not created else 'create',
                    content_type='DocumentPrintSettings',
                    description=f'{"تم إنشاء" if created else "تم تحديث"} تصميم طباعة المستند: {settings.document_name_ar}'
                )
                
                return JsonResponse({'success': True, 'message': 'تم حفظ التصميم بنجاح'})
                
            elif action == 'delete_settings':
                document_id = request.POST.get('document_id')
                
                try:
                    settings = DocumentPrintSettings.objects.get(id=document_id)
                    document_name = settings.document_name_ar
                    settings.delete()
                    
                    # تسجيل النشاط
                    AuditLog.objects.create(
                        user=request.user,
                        action_type='delete',
                        content_type='DocumentPrintSettings',
                        description=f'تم حذف تصميم طباعة المستند: {document_name}'
                    )
                    
                    return JsonResponse({'success': True, 'message': 'تم حذف التصميم بنجاح'})
                    
                except DocumentPrintSettings.DoesNotExist:
                    return JsonResponse({'success': False, 'error': 'الإعدادات غير موجودة'})
        
        except Exception as e:
            import traceback
            print(f"خطأ في حفظ تصميم الطباعة: {str(e)}")
            print(traceback.format_exc())
            return JsonResponse({'success': False, 'error': str(e)})


class JoFotaraSettingsView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """عرض إعدادات الربط الإلكتروني مع دائرة ضريبة الدخل والمبيعات (JoFotara)"""
    template_name = 'settings/jofotara_settings.html'
    
    def test_func(self):
        """التحقق من صلاحيات المستخدم - Superadmin فقط"""
        return self.request.user.is_superuser
    
    def handle_no_permission(self):
        messages.error(self.request, _('ليس لديك صلاحية للوصول لإعدادات JoFotara.'))
        return redirect('settings:index')
    
    def get_context_data(self, **kwargs):
        from .models import JoFotaraSettings
        
        context = super().get_context_data(**kwargs)
        
        # الحصول على إعدادات JoFotara أو إنشاء إعدادات فارغة
        settings = JoFotaraSettings.objects.first()
        if not settings:
            settings = JoFotaraSettings()
        context['jofotara_settings'] = settings
        
        return context
    
    def post(self, request, *args, **kwargs):
        from .models import JoFotaraSettings
        from core.models import AuditLog
        
        try:
            action = request.POST.get('action')
            
            if action == 'save_settings':
                # الحصول على الإعدادات أو إنشاء جديدة
                settings, created = JoFotaraSettings.objects.get_or_create(
                    defaults={}
                )
                
                # تحديث البيانات
                settings.api_url = request.POST.get('api_url', '')
                settings.client_id = request.POST.get('client_id', '')
                settings.client_secret = request.POST.get('client_secret', '')
                settings.is_active = request.POST.get('is_active') == 'on'
                settings.use_mock_api = request.POST.get('use_mock_api') == 'on'
                settings.save()
                
                # تسجيل النشاط
                AuditLog.objects.create(
                    user=request.user,
                    action_type='update' if not created else 'create',
                    content_type='JoFotaraSettings',
                    description=f'{"تم إنشاء" if created else "تم تحديث"} إعدادات JoFotara'
                )
                
                messages.success(request, _('تم حفظ إعدادات JoFotara بنجاح'))
                return redirect('settings:jofotara_settings')
                
            elif action == 'test_connection':
                # اختبار الاتصال مع API
                settings = JoFotaraSettings.objects.first()
                if not settings:
                    return JsonResponse({'success': False, 'error': 'لم يتم العثور على إعدادات JoFotara'})
                
                # استدعاء دالة اختبار الاتصال
                from .utils import test_jofotara_connection
                result = test_jofotara_connection()
                
                return JsonResponse(result)
        
        except Exception as e:
            import traceback
            print(f"خطأ في حفظ إعدادات JoFotara: {str(e)}")
            print(traceback.format_exc())
            messages.error(request, f'خطأ: {str(e)}')
            return redirect('settings:jofotara_settings')
