from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView, View, DetailView
from django.contrib import messages
from django.urls import reverse_lazy
from decimal import Decimal
from .models import BankAccount, BankTransfer, BankTransaction
from settings.models import Currency, CompanySettings

def clean_decimal_input(value):
    """
    تنظيف المدخلات الرقمية من الفواصل والمسافات
    """
    if value is None:
        return '0'
    return str(value).replace(',', '').replace(' ', '').strip()

# Temporary placeholder views
class BankAccountListView(LoginRequiredMixin, TemplateView):
    template_name = 'banks/account_list.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        accounts = BankAccount.objects.all()
        context['accounts'] = accounts
        context['total_accounts'] = accounts.count()
        context['active_accounts'] = accounts.filter(is_active=True).count()
        context['inactive_accounts'] = accounts.filter(is_active=False).count()
        
        # إضافة العملات النشطة
        context['currencies'] = Currency.get_active_currencies()
        context['base_currency'] = Currency.get_base_currency()
        
        # حساب الأرصدة منفصلة لكل عملة
        balances_by_currency = {}
        for account in accounts:
            currency_code = account.currency  # CharField
            if currency_code not in balances_by_currency:
                balances_by_currency[currency_code] = 0
            balances_by_currency[currency_code] += account.balance
        
        context['balances_by_currency'] = balances_by_currency
        
        # حساب عدد العملات المختلفة المستخدمة في الحسابات
        context['currencies_count'] = len(balances_by_currency)
        
        # استخدام العملة الأساسية من إعدادات الشركة
        from settings.models import CompanySettings
        company_settings = CompanySettings.objects.first()
        if company_settings and company_settings.base_currency:
            base_currency_code = company_settings.base_currency.code
        elif context['base_currency']:
            base_currency_code = context['base_currency'].code
        else:
            base_currency_code = None
        
        context['total_balance'] = balances_by_currency.get(base_currency_code, 0) if base_currency_code else 0
        
        return context

class BankAccountCreateView(LoginRequiredMixin, View):
    template_name = 'banks/account_add.html'
    
    def get(self, request, *args, **kwargs):
        context = {
            'currencies': Currency.get_active_currencies(),
            'base_currency': Currency.get_base_currency()
        }
        return render(request, self.template_name, context)
    
    def post(self, request, *args, **kwargs):
        try:
            # استلام البيانات من النموذج
            name = request.POST.get('name', '').strip()
            bank_name = request.POST.get('bank_name', '').strip()
            account_number = request.POST.get('account_number', '').strip()
            iban = request.POST.get('iban', '').strip()
            swift_code = request.POST.get('swift_code', '').strip()
            balance = request.POST.get('balance', '0')
            currency_code = request.POST.get('currency', '')
            is_active = request.POST.get('is_active') == 'on'
            notes = request.POST.get('notes', '').strip()
            
            # التحقق من صحة البيانات
            if not name:
                messages.error(request, 'اسم الحساب مطلوب!')
                return render(request, self.template_name)
                
            if not bank_name:
                messages.error(request, 'اسم البنك مطلوب!')
                return render(request, self.template_name)
                
            if not account_number:
                messages.error(request, 'رقم الحساب مطلوب!')
                return render(request, self.template_name)
            
            # التحقق من عدم تكرار رقم الحساب
            if BankAccount.objects.filter(account_number=account_number).exists():
                messages.error(request, 'رقم الحساب موجود مسبقاً!')
                return render(request, self.template_name)
            
            # تحويل الرصيد إلى رقم
            try:
                balance = Decimal(str(balance))
            except (ValueError, Decimal.InvalidOperation):
                balance = Decimal('0.0')
            
            # الحصول على العملة من قاعدة البيانات
            currency_obj = Currency.objects.filter(code=currency_code).first()
            if not currency_obj:
                # إذا لم توجد العملة، استخدم العملة الأساسية من إعدادات الشركة
                from settings.models import CompanySettings
                company_settings = CompanySettings.objects.first()
                if company_settings and company_settings.base_currency:
                    currency_obj = company_settings.base_currency
                    currency_code = currency_obj.code
                else:
                    currency_obj = Currency.get_base_currency()
                    currency_code = currency_obj.code if currency_obj else ''
            
            # إنشاء الحساب البنكي
            account = BankAccount.objects.create(
                name=name,
                bank_name=bank_name,
                account_number=account_number,
                iban=iban,
                swift_code=swift_code,
                balance=balance,
                currency=currency_code,  # CharField
                is_active=is_active,
                notes=notes
            )
            
            messages.success(request, f'تم إنشاء الحساب البنكي "{account.name}" بنجاح!')
            return redirect('banks:account_list')
            
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء إنشاء الحساب: {str(e)}')
            return render(request, self.template_name)

class BankAccountUpdateView(LoginRequiredMixin, View):
    template_name = 'banks/account_edit.html'
    
    def get(self, request, pk, *args, **kwargs):
        account = get_object_or_404(BankAccount, pk=pk)
        # معالجة الرصيد إذا كان None
        if account.balance is None:
            account.balance = 0.000
        # إذا تم تمرير بيانات مدخلة (من post عند ظهور خطأ)، استخدمها
        initial = kwargs.get('initial', None)
        context = {
            'account': account,
            'currencies': Currency.get_active_currencies(),
            'base_currency': Currency.get_base_currency(),
        }
        if initial:
            context['initial'] = initial
        return render(request, self.template_name, context)
    
    def post(self, request, pk, *args, **kwargs):
        try:
            account = get_object_or_404(BankAccount, pk=pk)
            # استلام البيانات من النموذج
            name = request.POST.get('name', '').strip()
            bank_name = request.POST.get('bank_name', '').strip()
            account_number = request.POST.get('account_number', '').strip()
            iban = request.POST.get('iban', '').strip()
            swift_code = request.POST.get('swift_code', '').strip()
            balance = request.POST.get('balance', '0')
            currency_code = request.POST.get('currency', '')
            is_active = request.POST.get('is_active') == 'on'
            notes = request.POST.get('notes', '').strip()
            # التحقق من صحة البيانات
            if not name or not bank_name or not account_number:
                if not name:
                    messages.error(request, 'اسم الحساب مطلوب!')
                if not bank_name:
                    messages.error(request, 'اسم البنك مطلوب!')
                if not account_number:
                    messages.error(request, 'رقم الحساب مطلوب!')
                initial = {
                    'name': name,
                    'bank_name': bank_name,
                    'account_number': account_number,
                    'iban': iban,
                    'swift_code': swift_code,
                    'balance': balance,
                    'currency': currency_code,
                    'is_active': is_active,
                    'notes': notes,
                }
                return self.get(request, pk, initial=initial)
            # التحقق من عدم تكرار رقم الحساب (ما عدا الحساب الحالي)
            existing_account = BankAccount.objects.filter(
                account_number=account_number
            ).exclude(pk=pk).first()
            if existing_account:
                messages.error(request, 'رقم الحساب موجود مسبقاً!')
                initial = {
                    'name': name,
                    'bank_name': bank_name,
                    'account_number': account_number,
                    'iban': iban,
                    'swift_code': swift_code,
                    'balance': balance,
                    'currency': currency_code,
                    'is_active': is_active,
                    'notes': notes,
                }
                return self.get(request, pk, initial=initial)
            # تحويل الرصيد إلى رقم
            try:
                balance = Decimal(str(balance))
            except (ValueError, Decimal.InvalidOperation):
                balance = account.balance  # إبقاء الرصيد الحالي في حالة الخطأ
            # تحديث الحساب
            account.name = name
            account.bank_name = bank_name
            account.account_number = account_number
            account.iban = iban
            account.swift_code = swift_code
            account.balance = balance
            account.currency = currency_code
            account.is_active = is_active
            account.notes = notes
            account.save()
            messages.success(request, f'تم تحديث الحساب البنكي "{account.name}" بنجاح!')
            return redirect('banks:account_list')
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء تحديث الحساب: {str(e)}')
            initial = {
                'name': request.POST.get('name', ''),
                'bank_name': request.POST.get('bank_name', ''),
                'account_number': request.POST.get('account_number', ''),
                'iban': request.POST.get('iban', ''),
                'swift_code': request.POST.get('swift_code', ''),
                'balance': request.POST.get('balance', '0'),
                'currency': request.POST.get('currency', ''),
                'is_active': request.POST.get('is_active') == 'on',
                'notes': request.POST.get('notes', ''),
            }
            return self.get(request, pk, initial=initial)

class BankAccountDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        from django.db import transaction
        try:
            account = BankAccount.objects.get(pk=pk)
            account_name = account.name
            
            # التحقق من عدم وجود رصيد في الحساب
            if account.balance != 0:
                if request.user.is_superuser:
                    messages.error(request, f'لا يمكن حذف الحساب "{account_name}" لأن الرصيد غير صفر ({account.balance:.3f}). يمكنك حذف جميع حركات الحساب أولاً باستخدام زر الممحاة، أو تحويل الرصيد لحساب آخر.')
                else:
                    messages.error(request, f'لا يمكن حذف الحساب "{account_name}" لأن الرصيد غير صفر ({account.balance:.3f}). يجب تحويل الرصيد لحساب آخر أولاً.')
                return redirect('banks:account_list')
            
            # التحقق من وجود معاملات مرتبطة بالحساب (فقط إذا كان الرصيد غير صفر)
            # إذا كان الرصيد صفر، يمكن حذف الحساب حتى لو كان له معاملات (تحويلات مثلاً)
            from .models import BankTransaction
            bank_transactions = BankTransaction.objects.filter(bank=account)
            
            # نسمح بالحذف إذا كان الرصيد صفر، حتى لو كان هناك معاملات
            # لأن هذا يعني أن المستخدم قام بتحويل جميع الأموال بنجاح
            if bank_transactions.exists() and account.balance != 0:
                # حفظ معرف الحساب في الجلسة لعرض صفحة الحركات
                request.session['delete_account_id'] = account.pk
                request.session['delete_account_name'] = account_name
                if request.user.is_superuser:
                    messages.warning(request, f'لا يمكن حذف الحساب "{account_name}" لأن هناك {bank_transactions.count()} حركة مالية ورصيد غير صفر ({account.balance:.3f}). يمكنك استخدام زر الممحاة لحذف جميع الحركات أولاً.')
                else:
                    messages.warning(request, f'لا يمكن حذف الحساب "{account_name}" لأن هناك {bank_transactions.count()} حركة مالية ورصيد غير صفر ({account.balance:.3f}). يجب تحويل الرصيد أو حذف جميع الحركات أولاً.')
                return redirect('banks:account_transactions', pk=account.pk)
            
            # التحقق من وجود تحويلات مرتبطة بالحساب (فقط إذا كان الرصيد غير صفر)
            # إذا كان الرصيد صفر، يمكن حذف الحساب حتى لو كان له تحويلات
            bank_transfers_from = BankTransfer.objects.filter(from_account=account)
            bank_transfers_to = BankTransfer.objects.filter(to_account=account)
            
            if (bank_transfers_from.exists() or bank_transfers_to.exists()) and account.balance != 0:
                transfers_count = bank_transfers_from.count() + bank_transfers_to.count()
                messages.error(request, f'لا يمكن حذف الحساب "{account_name}" لأن هناك {transfers_count} تحويل بنكي ورصيد غير صفر ({account.balance:.3f}). يجب تحويل الرصيد أو حذف جميع التحويلات أولاً.')
                return redirect('banks:account_list')
            
            # التحقق من وجود تحويلات بين البنوك والصناديق (فقط إذا كان الرصيد غير صفر)
            from cashboxes.models import CashboxTransfer
            cashbox_transfers_from = CashboxTransfer.objects.filter(from_bank=account)
            cashbox_transfers_to = CashboxTransfer.objects.filter(to_bank=account)
            
            if (cashbox_transfers_from.exists() or cashbox_transfers_to.exists()) and account.balance != 0:
                transfers_count = cashbox_transfers_from.count() + cashbox_transfers_to.count()
                messages.error(request, f'لا يمكن حذف الحساب "{account_name}" لأن هناك {transfers_count} تحويل بين البنوك والصناديق ورصيد غير صفر ({account.balance:.3f}). يجب تحويل الرصيد أو حذف جميع التحويلات أولاً.')
                return redirect('banks:account_list')
            
            # إذا مرت جميع الفحوصات، يمكن حذف الحساب
            with transaction.atomic():
                # إذا كان الرصيد صفر، حذف المعاملات والتحويلات أولاً
                if account.balance == 0:
                    # حذف المعاملات المرتبطة
                    from .models import BankTransaction
                    BankTransaction.objects.filter(bank=account).delete()
                    
                    # حذف التحويلات المرتبطة
                    BankTransfer.objects.filter(from_account=account).delete()
                    BankTransfer.objects.filter(to_account=account).delete()
                    
                    # حذف تحويلات الصناديق المرتبطة
                    from cashboxes.models import CashboxTransfer
                    CashboxTransfer.objects.filter(from_bank=account).delete()
                    CashboxTransfer.objects.filter(to_bank=account).delete()
                
                # حذف الحساب
                account.delete()
                messages.success(request, f'تم حذف الحساب البنكي "{account_name}" بنجاح!')
            
        except BankAccount.DoesNotExist:
            messages.error(request, 'الحساب البنكي غير موجود!')
        except Exception as e:
            # التعامل مع أخطاء المفاتيح الخارجية المحمية
            error_message = str(e)
            if "Cannot delete some instances" in error_message and "protected foreign keys" in error_message:
                messages.error(request, f'لا يمكن حذف الحساب "{account_name}" لأن هناك بيانات مرتبطة به في النظام. يُنصح بإلغاء تفعيل الحساب بدلاً من حذفه.')
            else:
                messages.error(request, f'حدث خطأ أثناء حذف الحساب: {error_message}')
        
        return redirect('banks:account_list')

class BankTransferListView(LoginRequiredMixin, TemplateView):
    template_name = 'banks/transfer_list.html'
    
    def get_context_data(self, **kwargs):
        from cashboxes.models import CashboxTransfer
        from django.db.models import Sum
        from datetime import datetime
        
        context = super().get_context_data(**kwargs)
        
        # الحصول على التحويلات البنكية
        bank_transfers = BankTransfer.objects.select_related('from_account', 'to_account', 'created_by').all()
        
        # الحصول على التحويلات بين البنوك والصناديق
        bank_cashbox_transfers = CashboxTransfer.objects.select_related(
            'from_bank', 'to_bank', 'from_cashbox', 'to_cashbox', 'created_by'
        ).filter(transfer_type__in=['bank_to_cashbox', 'cashbox_to_bank'])
        
        # حساب الإحصائيات
        total_transfers = bank_transfers.count() + bank_cashbox_transfers.count()
        
        # إجمالي المبالغ والرسوم للتحويلات البنكية
        bank_totals = bank_transfers.aggregate(
            total_amount=Sum('amount'),
            total_fees=Sum('fees')
        )
        
        # إجمالي المبالغ والرسوم للتحويلات البنك/صندوق
        cashbox_totals = bank_cashbox_transfers.aggregate(
            total_amount=Sum('amount'),
            total_fees=Sum('fees')
        )
        
        total_amounts = (bank_totals['total_amount'] or 0) + (cashbox_totals['total_amount'] or 0)
        total_fees = (bank_totals['total_fees'] or 0) + (cashbox_totals['total_fees'] or 0)
        
        # تحويلات هذا الشهر
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        this_month_bank = bank_transfers.filter(
            date__month=current_month,
            date__year=current_year
        ).count()
        
        this_month_cashbox = bank_cashbox_transfers.filter(
            date__month=current_month,
            date__year=current_year
        ).count()
        
        this_month_transfers = this_month_bank + this_month_cashbox
        
        context['bank_transfers'] = bank_transfers
        context['bank_cashbox_transfers'] = bank_cashbox_transfers
        context['total_transfers'] = total_transfers
        context['total_amounts'] = total_amounts
        context['total_fees'] = total_fees
        context['this_month_transfers'] = this_month_transfers
        
        return context

class BankTransferCreateView(LoginRequiredMixin, View):
    template_name = 'banks/transfer_add.html'
    
    def get(self, request, *args, **kwargs):
        from core.models import DocumentSequence
        from cashboxes.models import Cashbox
        
        context = {
            'accounts': BankAccount.objects.filter(is_active=True),
            'cashboxes': Cashbox.objects.filter(is_active=True),
            'currencies': Currency.get_active_currencies(),
            'base_currency': Currency.get_base_currency()
        }
        
        # التحقق من وجود تسلسل التحويلات البنكية
        try:
            sequence = DocumentSequence.objects.get(document_type='bank_transfer')
            context['transfer_sequence'] = sequence
        except DocumentSequence.DoesNotExist:
            context['transfer_sequence'] = None
            messages.warning(request, 'تحذير: لم يتم إعداد تسلسل أرقام التحويلات البنكية! يرجى إضافة تسلسل "التحويل بين الحسابات البنكية" من صفحة الإعدادات قبل إنشاء أي تحويل.')
        
        return render(request, self.template_name, context)
    
    def post(self, request, *args, **kwargs):
        # فحص نوع التحويل أولاً
        transfer_type = request.POST.get('transfer_type', 'bank_to_bank')
        
        if transfer_type == 'bank_to_bank':
            return self._handle_bank_to_bank_transfer(request)
        elif transfer_type == 'bank_to_cashbox':
            return self._handle_bank_to_cashbox_transfer(request)
        elif transfer_type == 'cashbox_to_bank':
            return self._handle_cashbox_to_bank_transfer(request)
        else:
            messages.error(request, 'نوع التحويل غير صحيح!')
            return redirect('banks:transfer_add')
    
    def _handle_bank_to_bank_transfer(self, request):
        """معالجة التحويل بين البنوك"""
        try:
            # استلام البيانات من النموذج
            date = request.POST.get('date', '').strip()
            from_account_id = request.POST.get('from_account', '').strip()
            to_account_id = request.POST.get('to_account', '').strip()
            amount = request.POST.get('amount', '0')
            fees = request.POST.get('fees', '0')
            exchange_rate = request.POST.get('exchange_rate', '1')
            description = request.POST.get('description', '').strip()
            
            # إعداد السياق لحالات الخطأ
            from cashboxes.models import Cashbox
            context = {
                'accounts': BankAccount.objects.filter(is_active=True),
                'cashboxes': Cashbox.objects.filter(is_active=True),
                'currencies': Currency.get_active_currencies(),
                'base_currency': Currency.get_base_currency()
            }
            
            # التحقق من صحة البيانات
            if not date:
                messages.error(request, 'تاريخ التحويل مطلوب!')
                return render(request, self.template_name, context)
            
            if not from_account_id or not to_account_id:
                messages.error(request, 'يجب اختيار حساب المرسل وحساب المستقبل!')
                return render(request, self.template_name, context)
            
            if from_account_id == to_account_id:
                messages.error(request, 'لا يمكن التحويل من الحساب إلى نفسه!')
                return render(request, self.template_name, context)
            
            # التحقق من وجود الحسابات
            try:
                from_account = BankAccount.objects.get(id=from_account_id, is_active=True)
                to_account = BankAccount.objects.get(id=to_account_id, is_active=True)
            except BankAccount.DoesNotExist:
                messages.error(request, 'أحد الحسابات المختارة غير موجود أو غير نشط!')
                return render(request, self.template_name, context)
            
            # تحويل المبالغ إلى أرقام
            try:
                amount = Decimal(clean_decimal_input(amount))
                if amount <= 0:
                    raise ValueError
            except (ValueError, Decimal.InvalidOperation):
                messages.error(request, 'مبلغ التحويل يجب أن يكون رقماً موجباً!')
                return render(request, self.template_name, context)
            
            try:
                fees = Decimal(clean_decimal_input(fees))
                if fees < 0:
                    raise ValueError
            except (ValueError, Decimal.InvalidOperation):
                messages.error(request, 'رسوم التحويل يجب أن تكون رقماً غير سالب!')
                return render(request, self.template_name, context)
            
            try:
                exchange_rate = Decimal(clean_decimal_input(exchange_rate))
                if exchange_rate <= 0:
                    raise ValueError
            except (ValueError, Decimal.InvalidOperation):
                messages.error(request, 'سعر الصرف يجب أن يكون رقماً موجباً!')
                return render(request, self.template_name, context)
            
            # التحقق من كفاية الرصيد
            total_amount = amount + fees
            if from_account.balance < total_amount:
                messages.error(request, f'رصيد الحساب "{from_account.name}" غير كافي! الرصيد الحالي: {from_account.balance:.3f}, المبلغ المطلوب: {total_amount:.3f}')
                return render(request, self.template_name, context)
            
            # إنشاء التحويل البنكي داخل معاملة
            from core.models import DocumentSequence
            from django.db import transaction
            
            with transaction.atomic():
                # الحصول على رقم التحويل من نظام تسلسل المستندات داخل المعاملة
                try:
                    sequence = DocumentSequence.objects.get(document_type='bank_transfer')
                    transfer_number = sequence.get_next_number()
                except DocumentSequence.DoesNotExist:
                    messages.error(request, 'لم يتم إعداد تسلسل أرقام التحويلات البنكية! يرجى إضافة تسلسل "التحويل بين الحسابات البنكية" من صفحة الإعدادات.')
                    return render(request, self.template_name, context)
                
                # إنشاء التحويل البنكي
                transfer = BankTransfer.objects.create(
                    transfer_number=transfer_number,
                    date=date,
                    from_account=from_account,
                    to_account=to_account,
                    amount=amount,
                    fees=fees,
                    exchange_rate=exchange_rate,
                    description=description,
                    created_by=request.user
                )
                
                # إنشاء معاملات البنك بدلاً من التعديل المباشر للأرصدة
                
                # إنشاء حركة الخصم من الحساب المرسل
                BankTransaction.objects.create(
                    bank=from_account,
                    transaction_type='withdrawal',
                    amount=total_amount,
                    description=f'تحويل إلى حساب {to_account.name} - رقم التحويل: {transfer_number}',
                    reference_number=transfer_number,
                    date=date,
                    created_by=request.user
                )
                
                # إنشاء حركة الإيداع للحساب المستقبل
                BankTransaction.objects.create(
                    bank=to_account,
                    transaction_type='deposit',
                    amount=amount * exchange_rate,
                    description=f'تحويل من حساب {from_account.name} - رقم التحويل: {transfer_number}',
                    reference_number=transfer_number,
                    date=date,
                    created_by=request.user
                )
                
                # لا حاجة لاستدعاء sync_balance هنا - سيتم تلقائياً عند save() للـ BankTransaction
            
            messages.success(request, f'تم إنشاء التحويل البنكي "{transfer.transfer_number}" بنجاح!')
            return redirect('banks:transfer_list')
            
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء إنشاء التحويل: {str(e)}')
            return render(request, self.template_name, context)

class BankCashboxTransferCreateView(LoginRequiredMixin, View):
    template_name = 'banks/bank_cashbox_transfer_add.html'
    
    def get(self, request, *args, **kwargs):
        from cashboxes.models import Cashbox
        from core.models import DocumentSequence
        
        context = {
            'banks': BankAccount.objects.filter(is_active=True),
            'cashboxes': Cashbox.objects.filter(is_active=True),
            'currencies': Currency.get_active_currencies(),
            'base_currency': Currency.get_base_currency()
        }
        
        # الحصول على رقم التحويل التالي
        try:
            sequence = DocumentSequence.objects.get(document_type='bank_cash_transfer')
            context['transfer_sequence'] = sequence
        except DocumentSequence.DoesNotExist:
            messages.error(request, 'لم يتم إعداد تسلسل أرقام التحويلات بين البنوك والصناديق! يرجى إضافة تسلسل "التحويل بين البنوك والصناديق" من صفحة الإعدادات.')
        
        return render(request, self.template_name, context)
    
    def post(self, request, *args, **kwargs):
        from cashboxes.models import Cashbox, CashboxTransfer, CashboxTransaction
        from banks.models import BankTransaction
        from core.models import DocumentSequence
        from django.db import transaction
        from datetime import datetime, timedelta
        
        try:
            # حماية من الطلبات المكررة - التحقق من وجود طلب مشابه في آخر 10 ثوان
            current_time = datetime.now()
            recent_time = current_time - timedelta(seconds=10)
            
            # استلام البيانات من النموذج
            date = request.POST.get('date', '').strip()
            transfer_type = request.POST.get('transfer_type', '').strip()
            bank_id = request.POST.get('bank', '').strip()
            cashbox_id = request.POST.get('cashbox', '').strip()
            amount = request.POST.get('amount', '0')
            fees = request.POST.get('fees', '0')
            exchange_rate = request.POST.get('exchange_rate', '1')
            description = request.POST.get('description', '').strip()
            check_number = request.POST.get('check_number', '').strip()
            check_date = request.POST.get('check_date', '').strip()
            check_bank_name = request.POST.get('check_bank_name', '').strip()
            
            # التحقق من وجود تحويل مشابه حديث
            try:
                amount_decimal = Decimal(str(amount))
                recent_transfer = CashboxTransfer.objects.filter(
                    transfer_type=transfer_type,
                    amount=amount_decimal,
                    created_by=request.user,
                    created_at__gte=recent_time
                ).first()
                
                if recent_transfer:
                    messages.warning(request, 'تم إنشاء تحويل مشابه مؤخراً! يرجى التحقق من قائمة التحويلات.')
                    return redirect('banks:transfer_list')
            except (ValueError, Decimal.InvalidOperation):
                pass  # سيتم التعامل مع الخطأ لاحقاً
            
            # إعداد السياق لحالات الخطأ
            context = {
                'banks': BankAccount.objects.filter(is_active=True),
                'cashboxes': Cashbox.objects.filter(is_active=True),
                'currencies': Currency.get_active_currencies(),
                'base_currency': Currency.get_base_currency()
            }
            
            # التحقق من صحة البيانات
            if not date:
                messages.error(request, 'تاريخ التحويل مطلوب!')
                return render(request, self.template_name, context)
            
            if not transfer_type or transfer_type not in ['bank_to_cashbox', 'cashbox_to_bank']:
                messages.error(request, 'يجب اختيار نوع التحويل!')
                return render(request, self.template_name, context)
            
            if not bank_id or not cashbox_id:
                messages.error(request, 'يجب اختيار البنك والصندوق!')
                return render(request, self.template_name, context)
            
            if not check_number:
                messages.error(request, 'رقم الشيك مطلوب!')
                return render(request, self.template_name, context)
            
            if not check_date:
                messages.error(request, 'تاريخ الشيك مطلوب!')
                return render(request, self.template_name, context)
            
            if not check_bank_name:
                messages.error(request, 'اسم البنك للشيك مطلوب!')
                return render(request, self.template_name, context)
            
            # التحقق من وجود البنك والصندوق
            try:
                bank = BankAccount.objects.get(id=bank_id, is_active=True)
                cashbox = Cashbox.objects.get(id=cashbox_id, is_active=True)
            except (BankAccount.DoesNotExist, Cashbox.DoesNotExist):
                messages.error(request, 'البنك أو الصندوق المختار غير موجود أو غير نشط!')
                return render(request, self.template_name, context)
            
            # تحويل المبالغ إلى أرقام
            try:
                amount = Decimal(clean_decimal_input(amount))
                if amount <= 0:
                    raise ValueError
            except (ValueError, Decimal.InvalidOperation):
                messages.error(request, 'مبلغ التحويل يجب أن يكون رقماً موجباً!')
                return render(request, self.template_name, context)
            
            try:
                fees = Decimal(clean_decimal_input(fees))
                if fees < 0:
                    raise ValueError
            except (ValueError, Decimal.InvalidOperation):
                messages.error(request, 'رسوم التحويل يجب أن تكون رقماً غير سالب!')
                return render(request, self.template_name, context)
            
            try:
                exchange_rate = Decimal(clean_decimal_input(exchange_rate))
                if exchange_rate <= 0:
                    raise ValueError
            except (ValueError, Decimal.InvalidOperation):
                messages.error(request, 'سعر الصرف يجب أن يكون رقماً موجباً!')
                return render(request, self.template_name, context)
            
            # التحقق من كفاية الرصيد
            total_amount = amount + fees
            if transfer_type == 'bank_to_cashbox' and bank.balance < total_amount:
                messages.error(request, f'رصيد البنك "{bank.name}" غير كافي! الرصيد الحالي: {bank.balance:.3f}, المبلغ المطلوب: {total_amount:.3f}')
                return render(request, self.template_name, context)
            elif transfer_type == 'cashbox_to_bank' and cashbox.balance < total_amount:
                messages.error(request, f'رصيد الصندوق "{cashbox.name}" غير كافي! الرصيد الحالي: {cashbox.balance:.3f}, المبلغ المطلوب: {total_amount:.3f}')
                return render(request, self.template_name, context)
            
            # إنشاء التحويل
            with transaction.atomic():
                # الحصول على رقم التحويل من نظام تسلسل المستندات داخل المعاملة
                try:
                    sequence = DocumentSequence.objects.get(document_type='bank_cash_transfer')
                    transfer_number = sequence.get_next_number()
                except DocumentSequence.DoesNotExist:
                    messages.error(request, 'لم يتم إعداد تسلسل أرقام التحويلات بين البنوك والصناديق! يرجى إضافة تسلسل "التحويل بين البنوك والصناديق" من صفحة الإعدادات.')
                    return render(request, self.template_name, context)
                
                if transfer_type == 'bank_to_cashbox':
                    # إنشاء تحويل من البنك إلى الصندوق
                    transfer = CashboxTransfer.objects.create(
                        transfer_number=transfer_number,
                        transfer_type=transfer_type,
                        date=date,
                        from_bank=bank,
                        to_cashbox=cashbox,
                        amount=amount,
                        fees=fees,
                        exchange_rate=exchange_rate,
                        description=f"{description} - شيك رقم: {check_number} - بنك: {check_bank_name}",
                        created_by=request.user
                    )
                    
                    # إضافة حركة البنك (بدون تعديل الرصيد مباشرة)
                    BankTransaction.objects.create(
                        bank=bank,
                        transaction_type='withdrawal',
                        amount=total_amount,
                        description=f'تحويل إلى صندوق {cashbox.name} - شيك: {check_number}',
                        reference_number=check_number,
                        date=date,
                        created_by=request.user
                    )
                    
                    # مزامنة رصيد البنك من المعاملات
                    bank.sync_balance()
                    
                    # إضافة حركة الصندوق
                    CashboxTransaction.objects.create(
                        cashbox=cashbox,
                        transaction_type='transfer_in',
                        date=date,
                        amount=amount * exchange_rate,
                        description=f'تحويل من بنك {bank.name} - شيك: {check_number}',
                        related_transfer=transfer,
                        created_by=request.user
                    )
                    
                    # تحديث رصيد الصندوق (يمكن الإبقاء عليه لأن الصناديق لا تعتمد على نظام المعاملات)
                    cashbox.balance += (amount * exchange_rate)
                    cashbox.save()
                    
                else:  # cashbox_to_bank
                    # إنشاء تحويل من الصندوق إلى البنك
                    transfer = CashboxTransfer.objects.create(
                        transfer_number=transfer_number,
                        transfer_type=transfer_type,
                        date=date,
                        from_cashbox=cashbox,
                        to_bank=bank,
                        amount=amount,
                        fees=fees,
                        exchange_rate=exchange_rate,
                        description=f"{description} - شيك رقم: {check_number} - بنك: {check_bank_name}",
                        created_by=request.user
                    )
                    
                    # إضافة حركة الصندوق
                    CashboxTransaction.objects.create(
                        cashbox=cashbox,
                        transaction_type='transfer_out',
                        date=date,
                        amount=-total_amount,
                        description=f'تحويل إلى بنك {bank.name} - شيك: {check_number}',
                        related_transfer=transfer,
                        created_by=request.user
                    )
                    
                    # إضافة حركة البنك
                    BankTransaction.objects.create(
                        bank=bank,
                        transaction_type='deposit',
                        amount=amount * exchange_rate,
                        description=f'تحويل من صندوق {cashbox.name} - شيك: {check_number}',
                        reference_number=check_number,
                        date=date,
                        created_by=request.user
                    )
                    
                    # تحديث الأرصدة من خلال حساب المعاملات
                    # تحديث رصيد الصندوق بالطريقة الصحيحة (سيتم تطبيق هذا لاحقاً عند إصلاح الصناديق)
                    cashbox.balance -= total_amount
                    cashbox.save()
                    
                    # تحديث رصيد البنك بناءً على المعاملات الفعلية
                    bank.sync_balance()
            
            messages.success(request, f'تم إنشاء التحويل "{transfer.transfer_number}" بنجاح!')
            return redirect('banks:transfer_list')
            
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء إنشاء التحويل: {str(e)}')
            return render(request, self.template_name, context)

class BankAccountDetailView(LoginRequiredMixin, DetailView):
    """عرض تفاصيل الحساب البنكي"""
    model = BankAccount
    template_name = 'banks/account_detail.html'
    context_object_name = 'account'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        account = self.get_object()
        
        # الحصول على الحركات الأخيرة للحساب
        from .models import BankTransaction
        recent_transactions = BankTransaction.objects.filter(
            bank=account
        ).order_by('-date', '-created_at')[:20]
        
        # الحصول على التحويلات المرتبطة بالحساب
        transfers_from = BankTransfer.objects.filter(from_account=account)[:10]
        transfers_to = BankTransfer.objects.filter(to_account=account)[:10]
        
        # إحصائيات الحساب
        from django.db.models import Sum, Count
        from datetime import datetime, timedelta
        
        # إحصائيات الشهر الحالي
        current_month = datetime.now().replace(day=1)
        
        this_month_deposits = BankTransaction.objects.filter(
            bank=account,
            transaction_type='deposit',
            date__gte=current_month
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        this_month_withdrawals = BankTransaction.objects.filter(
            bank=account,
            transaction_type='withdrawal',
            date__gte=current_month
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        context.update({
            'recent_transactions': recent_transactions,
            'transfers_from': transfers_from,
            'transfers_to': transfers_to,
            'this_month_deposits': this_month_deposits,
            'this_month_withdrawals': this_month_withdrawals,
            'currencies': Currency.get_active_currencies(),
        })
        
        return context




class BankTransferDetailView(LoginRequiredMixin, DetailView):
    """عرض تفاصيل التحويل البنكي"""
    model = BankTransfer
    template_name = 'banks/transfer_detail.html'
    context_object_name = 'transfer'


class BankTransferUpdateView(LoginRequiredMixin, UpdateView):
    """تعديل التحويل البنكي"""
    model = BankTransfer
    template_name = 'banks/transfer_edit.html'
    fields = ['date', 'amount', 'fees', 'exchange_rate', 'description']
    success_url = reverse_lazy('banks:transfer_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['accounts'] = BankAccount.objects.filter(is_active=True)
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'تم تحديث التحويل بنجاح!')
        return super().form_valid(form)


class CashboxTransferDetailView(LoginRequiredMixin, DetailView):
    """عرض تفاصيل التحويل بين البنك والصندوق"""
    template_name = 'banks/cashbox_transfer_detail.html'
    context_object_name = 'transfer'
    
    def get_object(self):
        from cashboxes.models import CashboxTransfer
        return get_object_or_404(CashboxTransfer, pk=self.kwargs['pk'])


class CashboxTransferUpdateView(LoginRequiredMixin, UpdateView):
    """تعديل التحويل بين البنك والصندوق"""
    template_name = 'banks/cashbox_transfer_edit.html'
    fields = ['date', 'amount', 'fees', 'exchange_rate', 'description']
    success_url = reverse_lazy('banks:transfer_list')
    
    def get_object(self):
        from cashboxes.models import CashboxTransfer
        return get_object_or_404(CashboxTransfer, pk=self.kwargs['pk'])
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from cashboxes.models import Cashbox
        context['banks'] = BankAccount.objects.filter(is_active=True)
        context['cashboxes'] = Cashbox.objects.filter(is_active=True)
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'تم تحديث التحويل بنجاح!')
        return super().form_valid(form)

class BankTransferDeleteView(LoginRequiredMixin, View):
    """حذف التحويل البنكي مع إعادة ضبط الأرصدة"""
    
    def post(self, request, pk, *args, **kwargs):
        from django.http import JsonResponse
        from django.db import transaction
        
        try:
            # الحصول على التحويل
            transfer = BankTransfer.objects.get(id=pk)
            
            # التحقق من الصلاحيات (يمكن إضافة منطق إضافي هنا)
            if not request.user.is_authenticated:
                return JsonResponse({'error': 'غير مصرح لك بهذا الإجراء'}, status=403)
            
            # حفظ بيانات التحويل قبل الحذف
            transfer_number = transfer.transfer_number
            from_account = transfer.from_account
            to_account = transfer.to_account
            amount = transfer.amount
            fees = transfer.fees
            total_amount = amount + fees
            
            with transaction.atomic():
                # حذف المعاملات البنكية المرتبطة أولاً
                from .models import BankTransaction
                BankTransaction.objects.filter(
                    reference_number=transfer_number
                ).delete()
                
                # حذف التحويل
                transfer.delete()
                
                # إعادة مزامنة الأرصدة بناءً على المعاملات المتبقية
                from_account.sync_balance()
                to_account.sync_balance()
            
            messages.success(request, f'تم حذف التحويل "{transfer_number}" بنجاح وتم إعادة ضبط الأرصدة.')
            return JsonResponse({'success': True})
            
        except BankTransfer.DoesNotExist:
            return JsonResponse({'error': 'التحويل غير موجود'}, status=404)
        except Exception as e:
            return JsonResponse({'error': f'حدث خطأ أثناء حذف التحويل: {str(e)}'}, status=500)


class CashboxTransferDeleteView(LoginRequiredMixin, View):
    """حذف التحويل بين البنك والصندوق مع إعادة ضبط الأرصدة"""
    
    def post(self, request, pk, *args, **kwargs):
        from django.http import JsonResponse
        from django.db import transaction
        from cashboxes.models import CashboxTransfer, CashboxTransaction
        from .models import BankTransaction
        
        try:
            # الحصول على التحويل
            transfer = CashboxTransfer.objects.get(id=pk)
            
            # التحقق من الصلاحيات
            if not request.user.is_authenticated:
                return JsonResponse({'error': 'غير مصرح لك بهذا الإجراء'}, status=403)
            
            # حفظ بيانات التحويل قبل الحذف
            transfer_number = transfer.transfer_number
            transfer_type = transfer.transfer_type
            amount = transfer.amount
            fees = transfer.fees
            total_amount = amount + fees
            exchange_rate = transfer.exchange_rate
            
            with transaction.atomic():
                # حذف المعاملات المرتبطة أولاً
                BankTransaction.objects.filter(
                    reference_number__icontains=transfer_number.split('-')[0] if '-' in transfer_number else transfer_number
                ).delete()
                
                CashboxTransaction.objects.filter(
                    related_transfer=transfer
                ).delete()
                
                # حذف التحويل
                transfer.delete()
                
                # إعادة مزامنة الأرصدة
                if transfer_type == 'bank_to_cashbox':
                    transfer.from_bank.sync_balance()
                    # للصناديق نحتاج لإعادة حساب الرصيد يدوياً (إذا لم يكن لديها sync_balance)
                    cashbox = transfer.to_cashbox
                    cashbox.save()  # سيؤدي لإعادة حساب الرصيد إذا كان مطبقاً
                    
                elif transfer_type == 'cashbox_to_bank':
                    transfer.to_bank.sync_balance()
                    # للصناديق نحتاج لإعادة حساب الرصيد يدوياً
                    cashbox = transfer.from_cashbox
                    cashbox.save()  # سيؤدي لإعادة حساب الرصيد إذا كان مطبقاً
            
            messages.success(request, f'تم حذف التحويل "{transfer_number}" بنجاح وتم إعادة ضبط الأرصدة.')
            return JsonResponse({'success': True})
            
        except CashboxTransfer.DoesNotExist:
            return JsonResponse({'error': 'التحويل غير موجود'}, status=404)
        except Exception as e:
            return JsonResponse({'error': f'حدث خطأ أثناء حذف التحويل: {str(e)}'}, status=500)

class BankAccountToggleStatusView(LoginRequiredMixin, View):
    """تفعيل/إلغاء تفعيل الحساب البنكي"""
    def post(self, request, pk, *args, **kwargs):
        try:
            account = BankAccount.objects.get(pk=pk)
            account_name = account.name
            
            # تبديل حالة التفعيل
            account.is_active = not account.is_active
            account.save()
            
            if account.is_active:
                messages.success(request, f'تم تفعيل الحساب البنكي "{account_name}" بنجاح!')
            else:
                messages.success(request, f'تم إلغاء تفعيل الحساب البنكي "{account_name}" بنجاح!')
            
        except BankAccount.DoesNotExist:
            messages.error(request, 'الحساب البنكي غير موجود!')
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء تغيير حالة الحساب: {str(e)}')
        
        return redirect('banks:account_list')

class BankAccountTransactionsView(LoginRequiredMixin, TemplateView):
    """عرض وإدارة حركات الحساب البنكي"""
    template_name = 'banks/account_transactions.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        account_id = self.kwargs.get('pk')
        account = get_object_or_404(BankAccount, pk=account_id)
        
        # الحصول على جميع الحركات
        from .models import BankTransaction
        transactions = BankTransaction.objects.filter(bank=account).order_by('-date', '-created_at')
        
        # معلومات من الجلسة إذا كان هذا جزء من عملية حذف
        delete_mode = self.request.session.get('delete_account_id') == account.pk
        
        context.update({
            'account': account,
            'transactions': transactions,
            'transactions_count': transactions.count(),
            'delete_mode': delete_mode,
            'can_delete_account': transactions.count() == 0 and account.balance == 0,
        })
        
        return context

class BankTransactionDeleteView(LoginRequiredMixin, View):
    """حذف حركة بنكية مع إعادة ضبط الرصيد"""
    
    def post(self, request, pk, *args, **kwargs):
        from django.http import JsonResponse
        from django.db import transaction
        from .models import BankTransaction
        
        try:
            # الحصول على المعاملة
            bank_transaction = BankTransaction.objects.get(id=pk)
            bank_account = bank_transaction.bank
            transaction_info = {
                'type': bank_transaction.get_transaction_type_display(),
                'amount': float(bank_transaction.amount),
                'date': bank_transaction.date.strftime('%Y-%m-%d'),
                'description': bank_transaction.description
            }
            
            with transaction.atomic():
                # التحقق إذا كانت المعاملة جزء من تحويل
                reference_number = bank_transaction.reference_number
                
                if reference_number:
                    # البحث عن التحويل المرتبط
                    from banks.models import BankTransfer
                    related_transfer = BankTransfer.objects.filter(transfer_number=reference_number).first()
                    
                    if related_transfer:
                        # إذا وُجد تحويل، احذف جميع المعاملات المرتبطة به
                        affected_accounts = {related_transfer.from_account, related_transfer.to_account}
                        
                        # حذف جميع المعاملات المرتبطة بهذا التحويل
                        BankTransaction.objects.filter(reference_number=reference_number).delete()
                        
                        # حذف التحويل نفسه
                        related_transfer.delete()
                        
                        # إعادة مزامنة جميع الحسابات المتأثرة
                        for account in affected_accounts:
                            account.sync_balance()
                    else:
                        # لا يوجد تحويل مرتبط، ربما معاملة تحويل منفردة
                        # ابحث عن معاملات أخرى بنفس reference_number واحذفها جميعاً
                        related_transactions = BankTransaction.objects.filter(reference_number=reference_number)
                        affected_accounts = set()
                        
                        for rel_trans in related_transactions:
                            affected_accounts.add(rel_trans.bank)
                        
                        # حذف جميع المعاملات المرتبطة
                        related_transactions.delete()
                        
                        # إعادة مزامنة جميع الحسابات المتأثرة
                        for account in affected_accounts:
                            account.sync_balance()
                else:
                    # معاملة عادية غير مرتبطة بتحويل
                    bank_transaction.delete()
                    bank_account.sync_balance()
            
            return JsonResponse({
                'success': True, 
                'message': f'تم حذف المعاملة ({transaction_info["type"]} - {transaction_info["amount"]}) بنجاح وتم إعادة ضبط الرصيد.',
                'new_balance': float(bank_account.balance)
            })
            
        except BankTransaction.DoesNotExist:
            return JsonResponse({'error': 'المعاملة غير موجودة'}, status=404)
        except Exception as e:
            return JsonResponse({'error': f'حدث خطأ أثناء حذف المعاملة: {str(e)}'}, status=500)

class BankAccountForceDeleteView(LoginRequiredMixin, View):
    """حذف الحساب البنكي بالقوة بعد إزالة جميع الحركات"""
    
    def post(self, request, pk, *args, **kwargs):
        from django.db import transaction
        try:
            account = BankAccount.objects.get(pk=pk)
            account_name = account.name
            
            # التحقق من صلاحية الحذف
            if account.balance != 0:
                messages.error(request, f'لا يمكن حذف الحساب لأن الرصيد غير صفر: {account.balance}')
                return redirect('banks:account_transactions', pk=pk)
            
            # التحقق من عدم وجود معاملات
            from .models import BankTransaction
            if BankTransaction.objects.filter(bank=account).exists():
                messages.error(request, 'لا يمكن حذف الحساب لأن هناك معاملات مرتبطة به')
                return redirect('banks:account_transactions', pk=pk)
            
            # التحقق من التحويلات
            bank_transfers_from = BankTransfer.objects.filter(from_account=account)
            bank_transfers_to = BankTransfer.objects.filter(to_account=account)
            
            if (bank_transfers_from.exists() or bank_transfers_to.exists()) and account.balance != 0:
                transfers_count = bank_transfers_from.count() + bank_transfers_to.count()
                messages.error(request, f'لا يمكن حذف الحساب لأن هناك {transfers_count} تحويل بنكي ورصيد غير صفر ({account.balance:.3f})')
                return redirect('banks:account_transactions', pk=pk)
            
            # التحقق من تحويلات الصناديق
            from cashboxes.models import CashboxTransfer
            cashbox_transfers_from = CashboxTransfer.objects.filter(from_bank=account)
            cashbox_transfers_to = CashboxTransfer.objects.filter(to_bank=account)
            
            if (cashbox_transfers_from.exists() or cashbox_transfers_to.exists()) and account.balance != 0:
                transfers_count = cashbox_transfers_from.count() + cashbox_transfers_to.count()
                messages.error(request, f'لا يمكن حذف الحساب لأن هناك {transfers_count} تحويل بين البنوك والصناديق ورصيد غير صفر ({account.balance:.3f})')
                return redirect('banks:account_transactions', pk=pk)
            
            # إذا مرت جميع الفحوصات، حذف الحساب
            with transaction.atomic():
                # إذا كان الرصيد صفر، حذف المعاملات والتحويلات أولاً
                if account.balance == 0:
                    # حذف المعاملات المرتبطة
                    from .models import BankTransaction
                    BankTransaction.objects.filter(bank=account).delete()
                    
                    # حذف التحويلات المرتبطة
                    BankTransfer.objects.filter(from_account=account).delete()
                    BankTransfer.objects.filter(to_account=account).delete()
                    
                    # حذف تحويلات الصناديق المرتبطة
                    from cashboxes.models import CashboxTransfer
                    CashboxTransfer.objects.filter(from_bank=account).delete()
                    CashboxTransfer.objects.filter(to_bank=account).delete()
                
                # حذف الحساب
                account.delete()
                
                # مسح بيانات الجلسة
                if 'delete_account_id' in request.session:
                    del request.session['delete_account_id']
                if 'delete_account_name' in request.session:
                    del request.session['delete_account_name']
                
                messages.success(request, f'تم حذف الحساب البنكي "{account_name}" بنجاح!')
            
            return redirect('banks:account_list')
            
        except BankAccount.DoesNotExist:
            messages.error(request, 'الحساب البنكي غير موجود!')
            return redirect('banks:account_list')
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء حذف الحساب: {str(e)}')
            return redirect('banks:account_transactions', pk=pk)

class ClearAccountTransactionsView(LoginRequiredMixin, View):
    """حذف جميع حركات الحساب - للـ Superadmin فقط"""
    
    def post(self, request, pk):
        # التحقق من صلاحية Superadmin
        if not request.user.is_superuser:
            messages.error(request, 'غير مسموح لك بهذا الإجراء!')
            return redirect('banks:account_list')
        
        try:
            account = get_object_or_404(BankAccount, pk=pk)
            
            # حساب العناصر المراد حذفها
            transactions_count = BankTransaction.objects.filter(bank=account).count()
            
            # حذف التحويلات المرتبطة بالحساب
            bank_transfers_from = BankTransfer.objects.filter(from_account=account)
            bank_transfers_to = BankTransfer.objects.filter(to_account=account)
            transfers_count = bank_transfers_from.count() + bank_transfers_to.count()
            
            # حذف تحويلات البنك-الصندوق المرتبطة
            from cashboxes.models import CashboxTransfer
            cashbox_transfers_from = CashboxTransfer.objects.filter(from_bank=account)
            cashbox_transfers_to = CashboxTransfer.objects.filter(to_bank=account)
            cashbox_transfers_count = cashbox_transfers_from.count() + cashbox_transfers_to.count()
            
            # تنفيذ الحذف داخل معاملة قاعدة البيانات
            from django.db import transaction
            with transaction.atomic():
                # جمع جميع الحسابات المتأثرة
                affected_accounts = set([account])
                
                # إضافة الحسابات المتأثرة بالتحويلات البنكية
                for transfer in bank_transfers_from:
                    affected_accounts.add(transfer.to_account)
                for transfer in bank_transfers_to:
                    affected_accounts.add(transfer.from_account)
                
                # إضافة الحسابات المتأثرة بتحويلات البنك-الصندوق
                for transfer in cashbox_transfers_from:
                    affected_accounts.add(account)
                for transfer in cashbox_transfers_to:
                    affected_accounts.add(transfer.from_bank)
                
                # حذف جميع حركات الحساب
                BankTransaction.objects.filter(bank=account).delete()
                
                # حذف التحويلات البنكية المرتبطة
                bank_transfers_from.delete()
                bank_transfers_to.delete()
                
                # حذف تحويلات البنك-الصندوق المرتبطة
                cashbox_transfers_from.delete()
                cashbox_transfers_to.delete()
                
                # إعادة مزامنة جميع الحسابات المتأثرة
                for affected_account in affected_accounts:
                    affected_account.sync_balance()
            
            # رسالة النجاح الشاملة
            total_deleted = transactions_count + transfers_count + cashbox_transfers_count
            details = []
            if transactions_count > 0:
                details.append(f'{transactions_count} حركة مالية')
            if transfers_count > 0:
                details.append(f'{transfers_count} تحويل بنكي')
            if cashbox_transfers_count > 0:
                details.append(f'{cashbox_transfers_count} تحويل بنك-صندوق')
            
            details_text = ' و '.join(details) if details else 'لا توجد عناصر'
            
            messages.success(
                request, 
                f'تم حذف {details_text} من حساب "{account.name}" وإعادة تعيين الرصيد إلى {account.initial_balance:.3f}'
            )
            
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء حذف الحركات: {str(e)}')
        
        return redirect('banks:account_list')
