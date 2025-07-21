from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django import forms
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .models import User, UserGroup
from core.signals import log_user_activity


class UserCreateForm(forms.ModelForm):
    """نموذج إنشاء مستخدم جديد"""
    
    password1 = forms.CharField(
        label=_('كلمة المرور'),
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text=_('يجب أن تكون كلمة المرور 8 أحرف على الأقل')
    )
    password2 = forms.CharField(
        label=_('تأكيد كلمة المرور'),
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text=_('أدخل كلمة المرور مرة أخرى للتأكيد')
    )
    
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label=_('المجموعات')
    )
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'first_name', 'last_name', 
            'user_type', 'phone', 'department', 'is_active',
            'can_access_sales', 'can_access_purchases', 'can_access_inventory',
            'can_access_banks', 'can_access_reports', 'can_delete_invoices',
            'can_edit_dates', 'can_edit_invoice_numbers', 'cash_only',
            'credit_only', 'can_see_low_stock_alerts', 'can_access_pos', 'pos_only', 'groups'
        ]
        
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'user_type': forms.Select(attrs={'class': 'form-select'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input', 'checked': True}),
            'can_access_sales': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_access_purchases': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_access_inventory': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_access_banks': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_access_reports': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_delete_invoices': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_edit_dates': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_edit_invoice_numbers': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'cash_only': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'credit_only': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_see_low_stock_alerts': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_access_pos': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'pos_only': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        
        labels = {
            'username': _('اسم المستخدم'),
            'email': _('البريد الإلكتروني'),
            'first_name': _('الاسم الأول'),
            'last_name': _('الاسم الأخير'),
            'user_type': _('نوع المستخدم'),
            'phone': _('الهاتف'),
            'department': _('القسم'),
            'is_active': _('نشط'),
            'can_access_sales': _('الوصول للمبيعات'),
            'can_access_purchases': _('الوصول للمشتريات'),
            'can_access_inventory': _('الوصول للمخزون'),
            'can_access_banks': _('الوصول للبنوك'),
            'can_access_reports': _('الوصول للتقارير'),
            'can_delete_invoices': _('حذف الفواتير'),
            'can_edit_dates': _('تعديل التواريخ'),
            'can_edit_invoice_numbers': _('تعديل أرقام الفواتير'),
            'cash_only': _('كاش فقط'),
            'credit_only': _('ذمم فقط'),
            'can_see_low_stock_alerts': _('تنبيهات انخفاض المخزون'),
            'can_access_pos': _('الوصول لنقطة البيع'),
            'pos_only': _('نقطة البيع فقط'),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        # إخفاء بعض الخيارات حسب صلاحيات المستخدم المنشئ
        if self.request and not self.request.user.is_superuser:
            if 'user_type' in self.fields:
                # منع إنشاء superadmin من قبل مستخدم عادي
                choices = list(self.fields['user_type'].choices)
                self.fields['user_type'].choices = [c for c in choices if c[0] != 'superadmin']

    def clean_username(self):
        username = self.cleaned_data['username']
        
        # التحقق من عدم تكرار اسم المستخدم
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError(_('اسم المستخدم موجود بالفعل'))
            
        # التحقق من طول اسم المستخدم
        if len(username) < 3:
            raise forms.ValidationError(_('اسم المستخدم يجب أن يكون 3 أحرف على الأقل'))
            
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            # التحقق من عدم تكرار البريد الإلكتروني
            if User.objects.filter(email=email).exists():
                raise forms.ValidationError(_('البريد الإلكتروني موجود بالفعل'))
        return email

    def clean_password1(self):
        password1 = self.cleaned_data.get('password1')
        if len(password1) < 8:
            raise forms.ValidationError(_('كلمة المرور يجب أن تكون 8 أحرف على الأقل'))
        return password1

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(_('كلمتا المرور غير متطابقتين'))
        return password2
    
    def clean(self):
        cleaned_data = super().clean()
        cash_only = cleaned_data.get('cash_only')
        credit_only = cleaned_data.get('credit_only')
        pos_only = cleaned_data.get('pos_only')
        can_access_pos = cleaned_data.get('can_access_pos')
        
        # منع تفعيل كاش فقط وذمم فقط معاً
        if cash_only and credit_only:
            raise forms.ValidationError(_('لا يمكن تفعيل "كاش فقط" و "ذمم فقط" معاً'))
        
        # التحقق من منطق نقطة البيع
        if pos_only and not can_access_pos:
            # إذا كان نقطة البيع فقط، يجب تفعيل الوصول لنقطة البيع تلقائياً
            cleaned_data['can_access_pos'] = True
            
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user


class UserEditForm(forms.ModelForm):
    """نموذج تحرير المستخدم"""
    
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label=_('المجموعات')
    )
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'first_name', 'last_name', 
            'user_type', 'phone', 'department', 'is_active',
            'can_access_sales', 'can_access_purchases', 'can_access_inventory',
            'can_access_banks', 'can_access_reports', 'can_delete_invoices',
            'can_edit_dates', 'can_edit_invoice_numbers', 'cash_only',
            'credit_only', 'can_see_low_stock_alerts', 'can_access_pos', 'pos_only', 'groups'
        ]
        
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'user_type': forms.Select(attrs={'class': 'form-select'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_access_sales': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_access_purchases': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_access_inventory': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_access_banks': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_access_reports': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_delete_invoices': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_edit_dates': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_edit_invoice_numbers': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'cash_only': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'credit_only': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_see_low_stock_alerts': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_access_pos': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'pos_only': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        
        labels = {
            'username': _('اسم المستخدم'),
            'email': _('البريد الإلكتروني'),
            'first_name': _('الاسم الأول'),
            'last_name': _('الاسم الأخير'),
            'user_type': _('نوع المستخدم'),
            'phone': _('الهاتف'),
            'department': _('القسم'),
            'is_active': _('نشط'),
            'can_access_sales': _('الوصول للمبيعات'),
            'can_access_purchases': _('الوصول للمشتريات'),
            'can_access_inventory': _('الوصول للمخزون'),
            'can_access_banks': _('الوصول للبنوك'),
            'can_access_reports': _('الوصول للتقارير'),
            'can_delete_invoices': _('حذف الفواتير'),
            'can_edit_dates': _('تعديل التواريخ'),
            'can_edit_invoice_numbers': _('تعديل أرقام الفواتير'),
            'cash_only': _('كاش فقط'),
            'credit_only': _('ذمم فقط'),
            'can_see_low_stock_alerts': _('تنبيهات انخفاض المخزون'),
            'can_access_pos': _('الوصول لنقطة البيع'),
            'pos_only': _('نقطة البيع فقط'),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        # منع تعديل اسم المستخدم للمستخدم الأساسي
        if self.instance and self.instance.username == 'superadmin':
            self.fields['username'].widget.attrs['readonly'] = True
            self.fields['user_type'].widget.attrs['readonly'] = True
            
        # إخفاء بعض الخيارات حسب صلاحيات المستخدم المحرر
        if self.request and not self.request.user.is_superuser:
            if 'user_type' in self.fields:
                # منع تغيير النوع إلى superadmin
                choices = list(self.fields['user_type'].choices)
                self.fields['user_type'].choices = [c for c in choices if c[0] != 'superadmin']

    def clean_username(self):
        username = self.cleaned_data['username']
        
        # التحقق من عدم تكرار اسم المستخدم
        if User.objects.filter(username=username).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError(_('اسم المستخدم موجود بالفعل'))
            
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            # التحقق من عدم تكرار البريد الإلكتروني
            if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError(_('البريد الإلكتروني موجود بالفعل'))
        return email
    
    def clean(self):
        cleaned_data = super().clean()
        cash_only = cleaned_data.get('cash_only')
        credit_only = cleaned_data.get('credit_only')
        pos_only = cleaned_data.get('pos_only')
        can_access_pos = cleaned_data.get('can_access_pos')
        
        # منع تفعيل كاش فقط وذمم فقط معاً
        if cash_only and credit_only:
            raise forms.ValidationError(_('لا يمكن تفعيل "كاش فقط" و "ذمم فقط" معاً'))
        
        # التحقق من منطق نقطة البيع
        if pos_only and not can_access_pos:
            # إذا كان نقطة البيع فقط، يجب تفعيل الوصول لنقطة البيع تلقائياً
            cleaned_data['can_access_pos'] = True
            
        return cleaned_data

class UserListView(LoginRequiredMixin, ListView):
    model = User
    template_name = 'users/user_list.html'
    context_object_name = 'users'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = User.objects.all().order_by('-created_at')
        
        # إخفاء المستخدمين ذوي الصلاحيات العالية عن المستخدمين العاديين
        # أو عند تفعيل الخيار من قبل الـ superadmin
        if not self.request.user.is_superuser:
            # إخفاء المستخدمين ذوي الصلاحيات العالية عن المستخدمين العاديين دائماً
            queryset = queryset.filter(is_superuser=False)
        else:
            # للـ superadmin، التحقق من إعداد الجلسة
            hide_superusers = self.request.session.get('hide_superusers', False)
            if hide_superusers:
                queryset = queryset.filter(is_superuser=False)
                
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # إضافة معلومات للـ superadmin فقط
        if self.request.user.is_superuser:
            context['is_superuser'] = True
            context['hide_superusers'] = self.request.session.get('hide_superusers', False)
        else:
            context['is_superuser'] = False
            
        return context

class UserCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = User
    form_class = UserCreateForm
    template_name = 'users/user_add.html'
    success_url = reverse_lazy('users:user_list')
    
    def test_func(self):
        """التحقق من صلاحية المستخدم لإنشاء المستخدمين"""
        return self.request.user.is_admin
    
    def get_form_kwargs(self):
        """إضافة request للنموذج"""
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs
    
    def form_valid(self, form):
        """معالجة النموذج عند صحته"""
        try:
            user = form.save()
            # تعيين صلاحيات إضافية حسب نوع المستخدم
            if user.user_type in ['admin', 'superadmin']:
                user.is_staff = True
                if user.user_type == 'superadmin':
                    user.is_superuser = True
                user.save()
            
            messages.success(
                self.request, 
                _('تم إنشاء المستخدم "{}" بنجاح. يمكنه الآن تسجيل الدخول للنظام.').format(user.username)
            )
            
            # تسجيل النشاط
            log_user_activity(
                self.request,
                'create',
                user,
                f'تم إنشاء مستخدم جديد: {user.username} ({user.get_full_name()})'
            )
        except Exception as e:
            messages.error(
                self.request,
                _('حدث خطأ أثناء إنشاء المستخدم: {}').format(str(e))
            )
            return super().form_invalid(form)
        
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        """إضافة بيانات إضافية للقالب"""
        context = super().get_context_data(**kwargs)
        
        # نصائح للمستخدم
        context['creation_tips'] = [
            'اختر اسم مستخدم واضح وسهل التذكر',
            'استخدم كلمة مرور قوية تحتوي على أرقام وحروف',
            'حدد الصلاحيات بحذر حسب دور المستخدم',
            'تأكد من صحة البريد الإلكتروني للتواصل',
        ]
        
        return context

class UserUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = User
    form_class = UserEditForm
    template_name = 'users/user_edit.html'
    success_url = reverse_lazy('users:user_list')
    context_object_name = 'user_to_edit'
    
    def test_func(self):
        """التحقق من صلاحية المستخدم لتعديل المستخدمين"""
        return self.request.user.is_admin
    
    def get_form_kwargs(self):
        """إضافة request للنموذج"""
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs
    
    def form_valid(self, form):
        """معالجة النموذج عند صحته"""
        user = form.save()
        messages.success(
            self.request, 
            _('تم تحديث بيانات المستخدم "{}" بنجاح').format(user.username)
        )
        
        # تسجيل النشاط
        log_user_activity(
            self.request,
            'update',
            user,
            f'تم تحديث بيانات المستخدم: {user.username} ({user.get_full_name()})'
        )
        
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        """إضافة بيانات إضافية للقالب"""
        context = super().get_context_data(**kwargs)
        user_to_edit = self.get_object()
        
        # التحقق من إمكانية التعديل
        context['can_edit'] = (
            user_to_edit != self.request.user or  # يمكن تعديل الآخرين
            not user_to_edit.is_superuser or      # أو تعديل مستخدم عادي
            self.request.user.is_superuser        # أو المستخدم الحالي superuser
        )
        
        # تحذيرات التعديل
        context['edit_warnings'] = []
        if user_to_edit == self.request.user:
            context['edit_warnings'].append('تقوم بتعديل بياناتك الشخصية')
        if user_to_edit.username == 'superadmin':
            context['edit_warnings'].append('هذا هو المستخدم الأساسي للنظام')
            
        return context

class UserDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = User
    template_name = 'users/user_delete.html'
    success_url = reverse_lazy('users:user_list')
    context_object_name = 'user_to_delete'
    
    def test_func(self):
        """التحقق من صلاحية المستخدم لحذف المستخدمين"""
        return self.request.user.is_admin
    
    def get_object(self, queryset=None):
        """الحصول على المستخدم المراد حذفه"""
        user = get_object_or_404(User, pk=self.kwargs['pk'])
        return user
    
    def get_context_data(self, **kwargs):
        """إضافة بيانات إضافية للقالب"""
        context = super().get_context_data(**kwargs)
        user_to_delete = self.get_object()
        
        # إحصائيات المستخدم (يمكن توسيعها لاحقاً)
        context['user_stats'] = {
            'last_login': user_to_delete.last_login,
            'date_joined': user_to_delete.date_joined,
            'is_staff': user_to_delete.is_staff,
            'is_superuser': user_to_delete.is_superuser,
        }
        
        # التحقق من إمكانية الحذف
        context['can_delete'] = (
            user_to_delete.username != 'superadmin' and 
            user_to_delete != self.request.user and
            not user_to_delete.is_superuser  # منع حذف أي مستخدم superuser نهائياً
        )
        
        # أسباب عدم إمكانية الحذف
        context['delete_warnings'] = []
        if user_to_delete.username == 'superadmin':
            context['delete_warnings'].append('المستخدم الأساسي للنظام محمي من الحذف')
        if user_to_delete == self.request.user:
            context['delete_warnings'].append('لا يمكن للمستخدم حذف حسابه الخاص')
        if user_to_delete.is_superuser:
            context['delete_warnings'].append('لا يمكن حذف المستخدمين ذوي صلاحيات Superuser')
            
        return context
    
    def delete(self, request, *args, **kwargs):
        """حذف المستخدم مع التحقق من القيود"""
        user = self.get_object()
        
        # منع حذف المستخدم الحالي
        if user == request.user:
            messages.error(request, _('لا يمكنك حذف نفسك'))
            return self.get(request, *args, **kwargs)
        
        # منع حذف المستخدم الأساسي superadmin
        if user.username == 'superadmin':
            messages.error(request, _('لا يمكن حذف المستخدم الأساسي'))
            return self.get(request, *args, **kwargs)
        
        # منع حذف أي مستخدم له صلاحيات superuser
        if user.is_superuser:
            messages.error(request, _('لا يمكن حذف المستخدمين ذوي صلاحيات Superuser'))
            return self.get(request, *args, **kwargs)
        
        username = user.username
        messages.success(request, _('تم حذف المستخدم "{}" بنجاح').format(username))
        
        # تسجيل النشاط
        log_user_activity(
            request,
            'delete',
            user,
            f'تم حذف المستخدم: {username}'
        )
        
        return super().delete(request, *args, **kwargs)

class UserGroupListView(LoginRequiredMixin, ListView):
    """عرض قائمة مجموعات المستخدمين"""
    model = Group
    template_name = 'users/group_list.html'
    context_object_name = 'groups'
    
    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # إضافة إحصائيات للمجموعات
        for group in context['groups']:
            group.user_count = group.user_set.count()
            group.permission_count = group.permissions.count()
        return context


class GroupCreateForm(forms.ModelForm):
    """نموذج إنشاء مجموعة جديدة"""
    
    permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label=_('الصلاحيات')
    )
    
    class Meta:
        model = Group
        fields = ['name', 'permissions']
        labels = {
            'name': _('اسم المجموعة'),
        }
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('أدخل اسم المجموعة')
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # تنظيم الصلاحيات حسب التطبيق
        self.fields['permissions'].queryset = Permission.objects.select_related('content_type').order_by('content_type__app_label', 'name')


class UserGroupCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """عرض إنشاء مجموعة جديدة"""
    model = Group
    form_class = GroupCreateForm
    template_name = 'users/group_add.html'
    success_url = reverse_lazy('users:group_list')
    
    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser
    
    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, _('تم إنشاء المجموعة بنجاح'))
            return response
        except Exception as e:
            messages.error(self.request, _('حدث خطأ أثناء إنشاء المجموعة: {}').format(str(e)))
            return self.form_invalid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # تجميع الصلاحيات حسب التطبيق
        permissions_by_app = {}
        for permission in Permission.objects.select_related('content_type').order_by('content_type__app_label', 'name'):
            app_label = permission.content_type.app_label
            if app_label not in permissions_by_app:
                permissions_by_app[app_label] = []
            permissions_by_app[app_label].append(permission)
        context['permissions_by_app'] = permissions_by_app
        return context


class GroupEditForm(forms.ModelForm):
    """نموذج تعديل مجموعة"""
    
    permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label=_('الصلاحيات')
    )
    
    class Meta:
        model = Group
        fields = ['name', 'permissions']
        labels = {
            'name': _('اسم المجموعة'),
        }
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('أدخل اسم المجموعة')
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['permissions'].queryset = Permission.objects.select_related('content_type').order_by('content_type__app_label', 'name')


class UserGroupUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """عرض تعديل مجموعة"""
    model = Group
    form_class = GroupEditForm
    template_name = 'users/group_edit.html'
    success_url = reverse_lazy('users:group_list')
    
    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser
    
    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, _('تم تحديث المجموعة بنجاح'))
            return response
        except Exception as e:
            messages.error(self.request, _('حدث خطأ أثناء تحديث المجموعة: {}').format(str(e)))
            return self.form_invalid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # تجميع الصلاحيات حسب التطبيق
        permissions_by_app = {}
        for permission in Permission.objects.select_related('content_type').order_by('content_type__app_label', 'name'):
            app_label = permission.content_type.app_label
            if app_label not in permissions_by_app:
                permissions_by_app[app_label] = []
            permissions_by_app[app_label].append(permission)
        context['permissions_by_app'] = permissions_by_app
        context['group_users'] = self.object.user_set.all()
        return context


class UserGroupDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """عرض حذف مجموعة"""
    model = Group
    template_name = 'users/group_delete.html'
    success_url = reverse_lazy('users:group_list')
    
    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser
    
    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        
        # منع حذف مجموعات النظام الأساسية
        system_groups = ['superadmin', 'admin', 'staff']
        if self.object.name.lower() in system_groups:
            messages.error(request, _('لا يمكن حذف مجموعات النظام الأساسية'))
            return redirect('users:group_list')
        
        return super().dispatch(request, *args, **kwargs)
    
    def delete(self, request, *args, **kwargs):
        try:
            group_name = self.object.name
            user_count = self.object.user_set.count()
            
            if user_count > 0:
                messages.warning(request, _('تحذير: هذه المجموعة تحتوي على {} مستخدم سيفقدون صلاحيات المجموعة').format(user_count))
            
            response = super().delete(request, *args, **kwargs)
            messages.success(request, _('تم حذف المجموعة "{}" بنجاح').format(group_name))
            return response
        except Exception as e:
            messages.error(request, _('حدث خطأ أثناء حذف المجموعة: {}').format(str(e)))
            return redirect('users:group_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['group_users'] = self.object.user_set.all()
        context['user_count'] = self.object.user_set.count()
        context['permission_count'] = self.object.permissions.count()
        return context

@login_required
@require_POST
def toggle_superuser_visibility(request):
    """تبديل إظهار/إخفاء المستخدمين ذوي الصلاحيات العالية"""
    # التحقق من أن المستخدم الحالي هو superadmin
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'غير مسموح'}, status=403)
    
    # الحصول على الحالة الحالية من الجلسة
    current_state = request.session.get('hide_superusers', False)
    new_state = not current_state
    
    # حفظ الحالة الجديدة في الجلسة
    request.session['hide_superusers'] = new_state
    
    return JsonResponse({
        'success': True, 
        'hide_superusers': new_state,
        'message': _('تم إخفاء المستخدمين ذوي الصلاحيات العالية') if new_state else _('تم إظهار المستخدمين ذوي الصلاحيات العالية')
    })
