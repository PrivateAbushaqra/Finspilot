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
from django.db.models.deletion import ProtectedError
from .models import User, UserGroup, UserGroupMembership
from core.signals import log_user_activity


class UserCreateForm(forms.ModelForm):
    """نموذج إنشاء مستخدم جديد"""
    
    password1 = forms.CharField(
        label=_('Password'),
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text=_('Password must be at least 8 characters long')
    )
    password2 = forms.CharField(
        label=_('Confirm Password'),
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text=_('Enter the password again to confirm')
    )
    
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label=_('Groups')
    )
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'first_name', 'last_name', 
            'user_type', 'phone', 'department', 'pos_warehouse', 'is_active', 'is_superuser', 'groups'
        ]
        
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'user_type': forms.Select(attrs={'class': 'form-select'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.TextInput(attrs={'class': 'form-control'}),
            'pos_warehouse': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input', 'checked': True}),
            'is_superuser': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        
        labels = {
            'username': _('Username'),
            'email': _('Email'),
            'first_name': _('First Name'),
            'last_name': _('Last Name'),
            'user_type': _('User Type'),
            'phone': _('Phone'),
            'department': _('Department'),
            'pos_warehouse': _('POS Warehouse'),
            'is_active': _('Active'),
            'is_superuser': _('Superuser'),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        # تصفية المجموعات لإخفاء مجموعات السوبر أدمين عن المستخدمين العاديين
        if self.request and not self.request.user.is_superuser:
            # تحديد صلاحيات السوبر أدمين التي يجب إخفاء المجموعات التي تحتويها
            superadmin_permissions = [
                'add_user', 'change_user', 'delete_user', 'view_user',
                'add_group', 'change_group', 'delete_group', 'view_group',
                'add_permission', 'change_permission', 'delete_permission', 'view_permission'
            ]
            
            # فلترة المجموعات للمستخدمين غير السوبر أدمين
            available_groups = []
            for group in Group.objects.all():
                group_permissions = group.permissions.values_list('codename', flat=True)
                has_superadmin_perms = any(perm in group_permissions for perm in superadmin_permissions)
                if not has_superadmin_perms:
                    available_groups.append(group.id)
            
            # تحديث queryset للمجموعات
            self.fields['groups'].queryset = Group.objects.filter(id__in=available_groups)
        
        # إخفاء بعض الخيارات حسب صلاحيات المستخدم المنشئ
        if self.request and not self.request.user.is_superuser:
            if 'user_type' in self.fields:
                # منع إنشاء superadmin من قبل مستخدم عادي
                choices = list(self.fields['user_type'].choices)
                self.fields['user_type'].choices = [c for c in choices if c[0] != 'superadmin']
            
            # إخفاء حقل is_superuser عن المستخدمين غير المصرح لهم
            if 'is_superuser' in self.fields:
                del self.fields['is_superuser']

        # Make first_name required for new users
        if 'first_name' in self.fields:
            self.fields['first_name'].required = True
            # ensure HTML required attribute is present on widget
            try:
                self.fields['first_name'].widget.attrs.update({'required': 'required'})
            except Exception:
                pass

    def clean_first_name(self):
        """Ensure first name is provided."""
        first_name = self.cleaned_data.get('first_name', '')
        if not first_name or not str(first_name).strip():
            raise forms.ValidationError(_('First name is required'))
        return first_name

    def clean_username(self):
        username = self.cleaned_data['username']
        
        # التحقق من عدم تكرار اسم المستخدم
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError(_('Username already exists'))
            
        # التحقق من طول اسم المستخدم
        if len(username) < 3:
            raise forms.ValidationError(_('Username must be at least 3 characters long'))
            
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            # التحقق من عدم تكرار البريد الإلكتروني
            if User.objects.filter(email=email).exists():
                raise forms.ValidationError(_('Email already exists'))
        return email

    def clean_password1(self):
        password1 = self.cleaned_data.get('password1')
        if len(password1) < 8:
            raise forms.ValidationError(_('Password must be at least 8 characters long'))
        return password1

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(_('Passwords do not match'))
        return password2
    
    def clean(self):
        cleaned_data = super().clean()
        # تم إزالة التحقق من الحقول المحذوفة
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
        label=_('Groups')
    )
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'first_name', 'last_name', 
            'user_type', 'phone', 'department', 'pos_warehouse', 'is_active', 'is_superuser', 'groups'
        ]
        
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'user_type': forms.Select(attrs={'class': 'form-select'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.TextInput(attrs={'class': 'form-control'}),
            'pos_warehouse': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_superuser': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        
        labels = {
            'username': _('Username'),
            'email': _('Email'),
            'first_name': _('First Name'),
            'last_name': _('Last Name'),
            'user_type': _('User Type'),
            'phone': _('Phone'),
            'department': _('Department'),
            'pos_warehouse': _('POS Warehouse'),
            'is_active': _('Active'),
            'is_superuser': _('Superuser'),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        # تصفية المجموعات لإخفاء مجموعات السوبر أدمين عن المستخدمين العاديين
        if self.request and not self.request.user.is_superuser:
            # تحديد صلاحيات السوبر أدمين التي يجب إخفاء المجموعات التي تحتويها
            superadmin_permissions = [
                'add_user', 'change_user', 'delete_user', 'view_user',
                'add_group', 'change_group', 'delete_group', 'view_group',
                'add_permission', 'change_permission', 'delete_permission', 'view_permission'
            ]
            
            # فلترة المجموعات للمستخدمين غير السوبر أدمين
            available_groups = []
            for group in Group.objects.all():
                group_permissions = group.permissions.values_list('codename', flat=True)
                has_superadmin_perms = any(perm in group_permissions for perm in superadmin_permissions)
                if not has_superadmin_perms:
                    available_groups.append(group.id)
            
            # تحديث queryset للمجموعات
            self.fields['groups'].queryset = Group.objects.filter(id__in=available_groups)
        
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
            
            # إخفاء حقل is_superuser عن المستخدمين غير المصرح لهم
            if 'is_superuser' in self.fields:
                del self.fields['is_superuser']

    def clean_username(self):
        username = self.cleaned_data['username']
        
        # التحقق من عدم تكرار اسم المستخدم
        if User.objects.filter(username=username).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError(_('Username already exists'))
            
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            # التحقق من عدم تكرار البريد الإلكتروني
            if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError(_('Email already exists'))
        return email
    
    def clean(self):
        cleaned_data = super().clean()
        # تم إزالة التحقق من الحقول المحذوفة
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
        permissions_by_app = {}
        # Add Revenues & Expenses permissions with custom permissions
        revenues_content_types = ContentType.objects.filter(app_label='revenues_expenses')
        revenues_permissions = Permission.objects.filter(content_type__in=revenues_content_types)
        for perm in revenues_permissions:
            app_label = perm.content_type.app_label
            if app_label not in permissions_by_app:
                permissions_by_app[app_label] = []

            # Use a translation map for these codenames (custom permissions)
            if perm.codename == 'can_add_sectors':
                perm.translated_name = _('Add Sectors')
            elif perm.codename == 'can_edit_sectors':
                perm.translated_name = _('Edit Sectors')
            elif perm.codename == 'can_delete_sectors':
                perm.translated_name = _('Delete Sectors')
            elif perm.codename == 'can_view_sectors':
                perm.translated_name = _('View Sectors')
            elif perm.codename == 'can_add_categories':
                perm.translated_name = _('Add Revenue/Expense Categories')
            elif perm.codename == 'can_edit_categories':
                perm.translated_name = _('Edit Revenue/Expense Categories')
            elif perm.codename == 'can_delete_categories':
                perm.translated_name = _('Delete Revenue/Expense Categories')
            elif perm.codename == 'can_view_categories':
                perm.translated_name = _('View Revenue/Expense Categories')
            elif perm.codename == 'can_add_entries':
                perm.translated_name = _('Add Revenue/Expense Entries')
            elif perm.codename == 'can_edit_entries':
                perm.translated_name = _('Edit Revenue/Expense Entries')
            elif perm.codename == 'can_delete_entries':
                perm.translated_name = _('Delete Revenue/Expense Entries')
            elif perm.codename == 'can_view_entries':
                perm.translated_name = _('View Revenue/Expense Entries')
            else:
                perm.translated_name = perm.name

            permissions_by_app[app_label].append(perm)
        
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
            user.save()
            
            messages.success(
                self.request,
                _('User "{}" created successfully. They can now log in to the system.').format(user.username)
            )
            
            # تسجيل النشاط
            log_user_activity(
                self.request,
                'create',
                user,
                _('Created new user: {} ({})').format(user.username, user.get_full_name())
            )
        except Exception as e:
            messages.error(
                self.request,
                _('An error occurred while creating the user: {}').format(str(e))
            )
            return super().form_invalid(form)
        
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        """إضافة بيانات إضافية للقالب"""
        context = super().get_context_data(**kwargs)
        
        # نصائح للمستخدم (قابلة للترجمة)
        context['creation_tips'] = [
            _('Choose a clear, easy-to-remember username'),
            _('Use a strong password including letters and numbers'),
            _('Assign permissions carefully according to user role'),
            _('Ensure the email address is valid for contact'),
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
            _('User "{}" updated successfully').format(user.username)
        )

        # تسجيل النشاط
        log_user_activity(
            self.request,
            'update',
            user,
            _('Updated user: {} ({})').format(user.username, user.get_full_name())
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
            context['edit_warnings'].append(_('You are editing your own profile'))
        if user_to_edit.username == 'superadmin':
            context['edit_warnings'].append(_('This is the main system user'))
            
        return context

class UserDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = User
    template_name = 'users/user_delete.html'
    success_url = reverse_lazy('users:user_list')
    context_object_name = 'user_to_delete'
    
    def test_func(self):
        """التحقق من صلاحية المستخدم لحذف المستخدمين"""
        # السماح فقط لمن لديه صلاحية حذف المستخدمين أو سوبرأدمين
        user = self.request.user
        return user.is_superuser or user.has_perm('users.delete_user')
    
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
        can_delete_basic = (
            user_to_delete.username != 'superadmin' and 
            user_to_delete != self.request.user and
            not user_to_delete.is_superuser
        )
        
        # فحص السجلات المرتبطة
        related_objects = {}
        has_protected_relations = False
        
        if can_delete_basic:
            try:
                # فحص قيود اليومية
                from journal.models import JournalEntry
                journal_count = JournalEntry.objects.filter(created_by=user_to_delete).count()
                if journal_count > 0:
                    related_objects['Journal Entries'] = journal_count
                    has_protected_relations = True
                
                # فحص سجلات المراجعة
                from core.models import AuditLog
                audit_count = AuditLog.objects.filter(user=user_to_delete).count()
                if audit_count > 0:
                    related_objects['Audit Logs'] = audit_count
                
                # يمكن إضافة فحوصات أخرى هنا للنماذج الأخرى
                
            except Exception:
                # في حالة حدوث خطأ في الفحص، نفترض وجود علاقات محمية
                has_protected_relations = True
        
        context['can_delete'] = can_delete_basic and not has_protected_relations
        context['related_objects'] = related_objects
        
        # Reasons why deletion is not allowed
        context['delete_warnings'] = []
        if user_to_delete.username == 'superadmin':
            context['delete_warnings'].append(_('Primary system user is protected from deletion'))
        if user_to_delete == self.request.user:
            context['delete_warnings'].append(_('You cannot delete your own account'))
        if user_to_delete.is_superuser:
            context['delete_warnings'].append(_('Cannot delete users with Superuser privileges'))
        if has_protected_relations and related_objects:
            relations_text = "، ".join([f"{count} {name}" for name, count in related_objects.items()])
            context['delete_warnings'].append(_('User is linked to: {}').format(relations_text))
            context['delete_warnings'].append(_('You can deactivate the user instead of deleting to preserve historical records'))
            
        return context
    
    def delete(self, request, *args, **kwargs):
        """حذف المستخدم مع التحقق من القيود والحماية من ProtectedError"""
        user = self.get_object()
        # منع حذف المستخدم الحالي
        if user == request.user:
            messages.error(request, _('You cannot delete yourself'))
            return self.get(request, *args, **kwargs)
        # منع حذف المستخدم الأساسي superadmin
        if user.username == 'superadmin':
            messages.error(request, _('Cannot delete the superadmin user'))
            return self.get(request, *args, **kwargs)
        # منع حذف أي مستخدم له صلاحيات superuser
        if user.is_superuser:
            messages.error(request, _('Cannot delete users with Superuser privileges'))
            return self.get(request, *args, **kwargs)
        
        username = user.username
        
        try:
            # تسجيل النشاط في سجل الأنشطة قبل الحذف
            from core.signals import log_view_activity
            log_view_activity(
                request,
                'delete',
                user,
                _('Deleted user: {}').format(username)
            )
            
            # محاولة حذف المستخدم
            result = super().delete(request, *args, **kwargs)
            messages.success(request, _('User "{}" deleted successfully').format(username))
            return result
            
        except ProtectedError as e:
            # معالجة خطأ الحماية - المستخدم مرتبط بسجلات أخرى
            protected_objects = e.args[1] if len(e.args) > 1 else set()
            
            # تحليل نوع السجلات المحمية
            protected_types = {}
            for obj in protected_objects:
                model_name = obj.__class__.__name__
                if model_name not in protected_types:
                    protected_types[model_name] = 0
                protected_types[model_name] += 1
            
            # بناء رسالة خطأ مفهومة
            error_parts = []
            for model_name, count in protected_types.items():
                if model_name == 'JournalEntry':
                    error_parts.append(f"{count} Journal Entry(ies)")
                elif model_name == 'AuditLog':
                    error_parts.append(f"{count} Audit Log(s)")
                elif model_name == 'Invoice':
                    error_parts.append(f"{count} Invoice(s)")
                else:
                    error_parts.append(f"{count} {model_name}")
            
            error_message = _('Cannot delete user "{}" because it is linked to: {}').format(
                username, 
                "، ".join(error_parts)
            )
            
            messages.error(request, error_message)
            messages.info(request, _('You can deactivate the user instead of deleting it to preserve historical records'))
            
            return self.get(request, *args, **kwargs)
        
        except Exception as e:
            # معالجة أي أخطاء أخرى
            messages.error(request, _('An error occurred while deleting the user: {}').format(str(e)))
            return self.get(request, *args, **kwargs)

class UserGroupListView(LoginRequiredMixin, ListView):
    """عرض قائمة مجموعات المستخدمين"""
    model = Group
    template_name = 'users/group_list.html'
    context_object_name = 'groups'
    
    def test_func(self):
        user = self.request.user
        return user.is_staff or user.is_superuser or getattr(user, 'user_type', None) in ['admin', 'superadmin']
    
    def get_queryset(self):
        """تصفية المجموعات لإخفاء مجموعات السوبر أدمين عن المستخدمين غير السوبر أدمين"""
        queryset = super().get_queryset()
        
        # إذا لم يكن المستخدم superadmin، نخفي المجموعات التي تحتوي على صلاحيات superadmin
        if not (self.request.user.user_type == 'superadmin' or self.request.user.is_superuser):
            from django.contrib.auth.models import Permission
            
            # الصلاحيات الخاصة بـ superadmin
            superadmin_permissions = Permission.objects.filter(
                codename__in=[
                    'can_access_system_management',
                    'can_manage_users', 
                    'can_view_audit_logs',
                    'can_backup_system'
                ]
            )
            
            # استبعاد المجموعات التي تحتوي على أي من صلاحيات superadmin
            for permission in superadmin_permissions:
                queryset = queryset.exclude(permissions=permission)
                
        return queryset
    
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
        label=_('Permissions')
    )
    
    class Meta:
        model = Group
        fields = ['name', 'permissions', 'dashboard_sections']
        labels = {
            'name': _('Group Name'),
        }
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter the group name')
            })
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # إضافة حقل is_system_group فقط للسوبر أدمين
        if self.user and (getattr(self.user, 'user_type', None) == 'superadmin' or self.user.is_superuser):
            self.fields['is_system_group'] = forms.BooleanField(
                required=False,
                label=_('Protected system group'),
                help_text=_('If enabled, this group is protected from deletion except for superadmin users'),
                widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
            )
        
        # جلب جميع الصلاحيات المرتبطة بقسم Purchases (بما فيها المخصصة)
        purchases_content_types = ContentType.objects.filter(app_label='purchases')
        purchases_permissions = Permission.objects.filter(content_type__in=purchases_content_types)
        queryset = Permission.objects.select_related('content_type').order_by('content_type__app_label', 'name')
        if self.user and not (self.user.user_type == 'superadmin' or self.user.is_superuser):
            queryset = queryset.exclude(
                codename__in=[
                    'can_access_system_management',
                    'can_manage_users', 
                    'can_view_audit_logs',
                    'can_backup_system'
                ]
            )
        # دمج جميع صلاحيات purchases مع باقي الصلاحيات
        all_perms = list({perm.id: perm for perm in list(queryset) + list(purchases_permissions)}.values())
        self.fields['permissions'].queryset = Permission.objects.filter(id__in=[perm.id for perm in all_perms]).order_by('content_type__app_label', 'name')
        
        # إضافة حقل dashboard_sections
        self.fields['dashboard_sections'] = forms.MultipleChoiceField(
            choices=[
                ('sales_stats', _('Sales statistics')),
                ('purchases_stats', _('Purchases statistics')),
                ('banks_balances', _('Bank and cashbox balances')),
                ('quick_links', _('Quick links')),
                ('sales_purchases_distribution', _('Sales/Purchases distribution (current month)')),
                ('monthly_performance', _('Monthly performance')),
            ],
            widget=forms.CheckboxSelectMultiple,
            required=False,
            label=_('Dashboard Sections')
        )
        
        # تعيين أقسام لوحة التحكم تلقائياً للمستخدمين المميزين
        if self.user and (self.user.user_type in ['superadmin', 'admin'] or self.user.is_superuser or self.user.is_staff):
            self.fields['dashboard_sections'].initial = ['sales_stats', 'purchases_stats', 'banks_balances', 'quick_links', 'sales_purchases_distribution', 'monthly_performance']
    
    def save(self, commit=True):
        group = super().save(commit=False)
        if commit:
            group.save()
            # حفظ dashboard_sections
            group.dashboard_sections = ','.join(self.cleaned_data.get('dashboard_sections', []))
            group.save()
        return group


class UserGroupCreateForm(forms.ModelForm):
    """نموذج إنشاء مجموعة مستخدمين مخصصة جديدة"""
    
    dashboard_sections = forms.MultipleChoiceField(
        choices=[
            ('sales_stats', _('Sales statistics')),
            ('purchases_stats', _('Purchases statistics')),
            ('banks_balances', _('Bank and cashbox balances')),
            ('quick_links', _('Quick links')),
            ('sales_purchases_distribution', _('Sales/Purchases distribution (current month)')),
            ('monthly_performance', _('Monthly performance')),
        ],
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label=_('Dashboard Sections')
    )
    
    class Meta:
        model = UserGroup
        fields = ['name', 'description', 'permissions', 'dashboard_sections']
        labels = {
            'name': _('Group Name'),
            'description': _('Description'),
        }
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter the group name')
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Enter the group description')
            }),
            'permissions': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': _('Enter permissions as JSON')
            }),
        }


class UserGroupEditForm(forms.ModelForm):
    """نموذج تعديل مجموعة مستخدمين مخصصة"""
    
    dashboard_sections = forms.MultipleChoiceField(
        choices=[
            ('sales_stats', _('Sales statistics')),
                ('purchases_stats', _('Purchases statistics')),
                ('banks_balances', _('Bank and cashbox balances')),
                ('quick_links', _('Quick links')),
                ('sales_purchases_distribution', _('Sales/Purchases distribution (current month)')),
                ('monthly_performance', _('Monthly performance')),
        ],
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label=_('Dashboard Sections')
    )
    
    class Meta:
        model = UserGroup
        fields = ['name', 'description', 'permissions', 'dashboard_sections']
        labels = {
            'name': _('Group Name'),
            'description': _('Description'),
        }
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter the group name')
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Enter the group description')
            }),
            'permissions': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': _('Enter permissions as JSON')
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['dashboard_sections'].initial = self.instance.dashboard_sections or []


class UserGroupCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """عرض إنشاء مجموعة جديدة"""
    model = Group
    form_class = GroupCreateForm
    template_name = 'users/group_add.html'
    success_url = reverse_lazy('users:group_list')
    
    def test_func(self):
        user = self.request.user
        return user.is_staff or user.is_superuser or getattr(user, 'user_type', None) in ['admin', 'superadmin']
    
    def get_form_kwargs(self):
        """تمرير المستخدم للنموذج لتصفية الصلاحيات"""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        try:
            # حفظ المجموعة أولاً
            group = form.save(commit=False)
            group.save()
            
            # حفظ الصلاحيات (signals ستتولى تنظيف cache)
            group.permissions.clear()
            for permission in form.cleaned_data['permissions']:
                group.permissions.add(permission)
            
            # حفظ dashboard_sections
            group.dashboard_sections = ','.join(form.cleaned_data.get('dashboard_sections', []))
            
            # حفظ is_system_group إذا كان متوفراً ومسموح للمستخدم الحالي
            if 'is_system_group' in form.cleaned_data and (getattr(self.request.user, 'user_type', None) == 'superadmin' or self.request.user.is_superuser):
                group.is_system_group = form.cleaned_data['is_system_group']
            else:
                # التأكد من أن is_system_group = False للمستخدمين غير المعتمدين
                group.is_system_group = False
            
            group.save()
            
            # تسجيل النشاط في سجل الأنشطة
            log_user_activity(
                self.request,
                'create',
                group,
                _('Created new user group: {} with {} permissions and dashboard sections: {}').format(
                    group.name,
                    len(form.cleaned_data["permissions"]),
                    ", ".join(form.cleaned_data.get("dashboard_sections", []))
                )
            )
            
            messages.success(self.request, _('Group created successfully'))
            return redirect(self.success_url)
        except Exception as e:
            messages.error(self.request, _('An error occurred while creating the group: {}').format(str(e)))
            return self.form_invalid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            # الحصول على جميع الصلاحيات
            queryset = Permission.objects.select_related('content_type').order_by('content_type__app_label', 'name')
            
            # تصفية صلاحيات superadmin إذا لم يكن المستخدم superadmin أو admin
            if not (getattr(self.request.user, 'user_type', None) in ['superadmin', 'admin'] or self.request.user.is_superuser):
                queryset = queryset.exclude(
                    codename__in=[
                        'can_access_system_management',
                        'can_manage_users',
                        'can_view_audit_logs'
                    ]
                )
            
            # تنظيم الصلاحيات حسب التطبيق
            permissions_by_app = {}
            for permission in queryset:
                app_label = permission.content_type.app_label
                if app_label not in permissions_by_app:
                    permissions_by_app[app_label] = []
                
                # إضافة ترجمة للصلاحية
                permission.translated_name = self._get_permission_translation(permission)
                permissions_by_app[app_label].append(permission)
            
            context['permissions_by_app'] = permissions_by_app
            
            # إضافة أسماء التطبيقات المترجمة
            context['app_names'] = self._get_app_names()
            
            # إضافة wrapper للصلاحيات
            from django.contrib.auth.context_processors import PermWrapper
            context['perms'] = PermWrapper(self.request.user)
            
        except Exception as e:
            # في حالة وجود خطأ، إضافة سياق فارغ
            context['permissions_by_app'] = {}
            context['app_names'] = {}
        
        return context
    
    def _get_permission_translation(self, permission):
        """ترجمة اسم الصلاحية"""
        translations = {
            # صلاحيات القيود اليومية
            'add_journalentry': _('Add Journal Entry'),
            'change_journalentry': _('Change Journal Entry'),
            'delete_journalentry': _('Delete Journal Entry'),
            'view_journalentry': _('View Journal Entry'),
            'change_journalentry_entry_number': _('Change Journal Entry Number'),
            'add_account': _('Add Account'),
            'change_account': _('Change Account'),
            'delete_account': _('Delete Account'),
            'view_account': _('View Account'),
            
            # صلاحيات الإيرادات والمصروفات
            'can_add_sectors': _('Add Sectors'),
            'can_edit_sectors': _('Edit Sectors'),
            'can_delete_sectors': _('Delete Sectors'),
            'can_view_sectors': _('View Sectors'),
            'can_add_categories': _('Add Revenue/Expense Categories'),
            'can_edit_categories': _('Edit Revenue/Expense Categories'),
            'can_delete_categories': _('Delete Revenue/Expense Categories'),
            'can_view_categories': _('View Revenue/Expense Categories'),
            'can_add_entries': _('Add Revenue/Expense Entries'),
            'can_edit_entries': _('Edit Revenue/Expense Entries'),
            'can_delete_entries': _('Delete Revenue/Expense Entries'),
            'can_view_entries': _('View Revenue/Expense Entries'),
            'can_add_recurring': _('Add Recurring Revenue/Expense'),
            'can_edit_recurring': _('Edit Recurring Revenue/Expense'),
            'can_delete_recurring': _('Delete Recurring Revenue/Expense'),
            'can_view_recurring': _('View Recurring Revenue/Expense'),
            
            # صلاحيات المبيعات
            'add_salesinvoice': _('Add Sales Invoice'),
            'change_salesinvoice': _('Change Sales Invoice'),
            'delete_salesinvoice': _('Delete Sales Invoice'),
            'view_salesinvoice': _('View Sales Invoice'),
            'add_salesinvoiceitem': _('Add Sales Invoice Item'),
            'change_salesinvoiceitem': _('Change Sales Invoice Item'),
            'delete_salesinvoiceitem': _('Delete Sales Invoice Item'),
            'view_salesinvoiceitem': _('View Sales Invoice Item'),
            
            # صلاحيات المشتريات
            'add_purchaseinvoice': _('Add Purchase Invoice'),
            'change_purchaseinvoice': _('Change Purchase Invoice'),
            'delete_purchaseinvoice': _('Delete Purchase Invoice'),
            'view_purchaseinvoice': _('View Purchase Invoice'),
            'add_purchaseinvoiceitem': _('Add Purchase Invoice Item'),
            'change_purchaseinvoiceitem': _('Change Purchase Invoice Item'),
            'delete_purchaseinvoiceitem': _('Delete Purchase Invoice Item'),
            'view_purchaseinvoiceitem': _('View Purchase Invoice Item'),
            
            # صلاحيات العملاء والموردين
            'add_customersupplier': _('Add Customer/Supplier'),
            'change_customersupplier': _('Change Customer/Supplier'),
            'delete_customersupplier': _('Delete Customer/Supplier'),
            'view_customersupplier': _('View Customer/Supplier'),
            
            # صلاحيات المنتجات
            'add_product': _('Add Product'),
            'change_product': _('Change Product'),
            'delete_product': _('Delete Product'),
            'view_product': _('View Product'),
            'add_category': _('Add Category'),
            'change_category': _('Change Category'),
            'delete_category': _('Delete Category'),
            'view_category': _('View Category'),
            
            # صلاحيات الإيرادات والمصروفات
            'can_add_sectors': _('Add Sectors'),
            'can_edit_sectors': _('Edit Sectors'),
            'can_delete_sectors': _('Delete Sectors'),
            'can_view_sectors': _('View Sectors'),
            'can_add_categories': _('Add Revenue/Expense Categories'),
            'can_edit_categories': _('Edit Revenue/Expense Categories'),
            'can_delete_categories': _('Delete Revenue/Expense Categories'),
            'can_view_categories': _('View Revenue/Expense Categories'),
            'can_add_entries': _('Add Revenue/Expense Entries'),
            'can_edit_entries': _('Edit Revenue/Expense Entries'),
            'can_delete_entries': _('Delete Revenue/Expense Entries'),
            'can_view_entries': _('View Revenue/Expense Entries'),
            'can_add_recurring': _('Add Recurring Revenue/Expense'),
            'can_edit_recurring': _('Edit Recurring Revenue/Expense'),
            'can_delete_recurring': _('Delete Recurring Revenue/Expense'),
            'can_view_recurring': _('View Recurring Revenue/Expense'),
            
            # صلاحيات المبيعات
            'add_salesinvoice': _('Add Sales Invoice'),
            'change_salesinvoice': _('Change Sales Invoice'),
            'delete_salesinvoice': _('Delete Sales Invoice'),
            'view_salesinvoice': _('View Sales Invoice'),
            'add_salesinvoiceitem': _('Add Sales Invoice Item'),
            'change_salesinvoiceitem': _('Change Sales Invoice Item'),
            'delete_salesinvoiceitem': _('Delete Sales Invoice Item'),
            'view_salesinvoiceitem': _('View Sales Invoice Item'),
            
            # صلاحيات المشتريات
            'add_purchaseinvoice': _('Add Purchase Invoice'),
            'change_purchaseinvoice': _('Change Purchase Invoice'),
            'delete_purchaseinvoice': _('Delete Purchase Invoice'),
            'view_purchaseinvoice': _('View Purchase Invoice'),
            'add_purchaseinvoiceitem': _('Add Purchase Invoice Item'),
            'change_purchaseinvoiceitem': _('Change Purchase Invoice Item'),
            'delete_purchaseinvoiceitem': _('Delete Purchase Invoice Item'),
            'view_purchaseinvoiceitem': _('View Purchase Invoice Item'),
            
            # صلاحيات العملاء والموردين
            'add_customersupplier': _('Add Customer/Supplier'),
            'change_customersupplier': _('Change Customer/Supplier'),
            'delete_customersupplier': _('Delete Customer/Supplier'),
            'view_customersupplier': _('View Customer/Supplier'),
            
            # صلاحيات المنتجات
            'add_product': _('Add Product'),
            'change_product': _('Change Product'),
            'delete_product': _('Delete Product'),
            'view_product': _('View Product'),
            'add_category': _('Add Category'),
            'change_category': _('Change Category'),
            'delete_category': _('Delete Category'),
            'view_category': _('View Category'),
            
            # صلاحيات المخزون
            'add_warehouse': _('Add Warehouse'),
            'change_warehouse': _('Change Warehouse'),
            'delete_warehouse': _('Delete Warehouse'),
            'view_warehouse': _('View Warehouse'),
            'add_inventorymovement': _('Add Inventory Movement'),
            'change_inventorymovement': _('Change Inventory Movement'),
            'delete_inventorymovement': _('Delete Inventory Movement'),
            'view_inventorymovement': _('View Inventory Movement'),
            
            # صلاحيات الأصول والخصوم
            'can_view_asset_categories': _('View Asset Categories'),
            'can_add_asset_categories': _('Add Asset Categories'),
            'can_edit_asset_categories': _('Edit Asset Categories'),
            'can_delete_asset_categories': _('Delete Asset Categories'),
            'can_view_assets': _('View Assets'),
            'can_add_assets': _('Add Assets'),
            'can_edit_assets': _('Edit Assets'),
            'can_delete_assets': _('Delete Assets'),
            'can_view_liability_categories': _('View Liability Categories'),
            'can_add_liability_categories': _('Add Liability Categories'),
            'can_edit_liability_categories': _('Edit Liability Categories'),
            'can_delete_liability_categories': _('Delete Liability Categories'),
            'can_view_liabilities': _('View Liabilities'),
            'can_add_liabilities': _('Add Liabilities'),
            'can_edit_liabilities': _('Edit Liabilities'),
            'can_delete_liabilities': _('Delete Liabilities'),
            'can_view_depreciation_entries': _('View Depreciation Entries'),
            'can_add_depreciation_entries': _('Add Depreciation Entries'),
            'can_edit_depreciation_entries': _('Edit Depreciation Entries'),
            'can_delete_depreciation_entries': _('Delete Depreciation Entries'),
            
            # صلاحيات البنوك
            'add_bank': _('Add Bank'),
            'change_bank': _('Change Bank'),
            'delete_bank': _('Delete Bank'),
            'view_bank': _('View Bank'),
            'add_bankaccount': _('Add Bank Account'),
            'change_bankaccount': _('Change Bank Account'),
            'delete_bankaccount': _('Delete Bank Account'),
            'view_bankaccount': _('View Bank Account'),
            'can_view_bank_accounts': _('Can View Bank Accounts'),
            'can_add_bank_accounts': _('Can Add Bank Accounts'),
            'can_edit_bank_accounts': _('Can Edit Bank Accounts'),
            'can_delete_bank_accounts': _('Can Delete Bank Accounts'),
            
            # صلاحيات الصناديق
            'add_cashbox': _('Add Cashbox'),
            'change_cashbox': _('Change Cashbox'),
            'delete_cashbox': _('Delete Cashbox'),
            'view_cashbox': _('View Cashbox'),
            
            # صلاحيات المدفوعات والمقبوضات
            'add_payment': _('Add Payment'),
            'change_payment': _('Change Payment'),
            'delete_payment': _('Delete Payment'),
            'view_payment': _('View Payment'),
            'add_receipt': _('Add Receipt'),
            'change_receipt': _('Change Receipt'),
            'delete_receipt': _('Delete Receipt'),
            'view_receipt': _('View Receipt'),
            
            # صلاحيات المستخدمين
            'add_user': _('Add User'),
            'change_user': _('Change User'),
            'delete_user': _('Delete User'),
            'view_user': _('View User'),
            'add_group': _('Add Group'),
            'change_group': _('Change Group'),
            'delete_group': _('Delete Group'),
            'view_group': _('View Group'),
            
            # صلاحيات النظام الأساسي
            'add_companysettings': _('Add Company Settings'),
            'change_companysettings': _('Change Company Settings'),
            'delete_companysettings': _('Delete Company Settings'),
            'view_companysettings': _('View Company Settings'),
            'add_auditlog': _('Add Audit Log'),
            'change_auditlog': _('Change Audit Log'),
            'delete_auditlog': _('Delete Audit Log'),
            'view_auditlog': _('View Audit Log'),
            
            # صلاحيات النسخ الاحتياطية
            'can_restore_backup': _('Restore Backups'),
            'delete_backup': _('Delete Backup Files'),
            'can_delete_advanced_data': _('Delete Advanced Data'),
            'can_backup_system': _('Create System Backups'),
        }
        
        return translations.get(permission.codename, permission.name)
    
    def _get_app_names(self):
        """أسماء التطبيقات المترجمة"""
        return {
            'journal': _('Journal Entries'),
            'sales': _('Sales'),
            'purchases': _('Purchases'),
            'customers': _('Customers and Suppliers'),
            'products': _('Categories and Products'),
            'inventory': _('Inventory Management'),
            'assets_liabilities': _('Assets & Liabilities'),
            'revenues_expenses': _('Revenues & Expenses'),
            'banks': _('Banks'),
            'cashboxes': _('Cashboxes'),
            'payments': _('Payments'),
            'receipts': _('Receipts'),
            'users': _('System Management'),
            'core': _('Core'),
            'backup': _('Backups'),
            'hr': _('Human Resources'),
            'reports': _('Reports'),
            'settings': _('Advanced System Settings'),
        }


class GroupEditForm(forms.ModelForm):
    """نموذج تعديل مجموعة"""
    
    permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label=_('Permissions')
    )
    
    class Meta:
        model = Group
        fields = ['name', 'permissions', 'dashboard_sections']
        labels = {
            'name': _('Group Name'),
        }
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter the group name')
            })
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # إضافة حقل is_system_group فقط للسوبر أدمين
        if self.user and (getattr(self.user, 'user_type', None) == 'superadmin' or self.user.is_superuser):
            self.fields['is_system_group'] = forms.BooleanField(
                required=False,
                label=_('Protected system group'),
                help_text=_('If enabled, this group is protected from deletion except for superadmin users'),
                widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
            )
            # تعيين القيمة الأولية من المجموعة الحالية
            if self.instance and self.instance.pk:
                self.fields['is_system_group'].initial = self.instance.is_system_group
        
        # جلب جميع الصلاحيات المرتبطة بقسم Purchases (بما فيها المخصصة)
        purchases_content_types = ContentType.objects.filter(app_label='purchases')
        purchases_permissions = Permission.objects.filter(content_type__in=purchases_content_types)
        queryset = Permission.objects.select_related('content_type').order_by('content_type__app_label', 'name')
        if self.user and not (self.user.user_type in ['superadmin', 'admin'] or self.user.is_superuser):
            queryset = queryset.exclude(
                codename__in=[
                    'can_access_system_management',
                    'can_manage_users', 
                    'can_view_audit_logs',
                    'can_backup_system'
                ]
            )
        # دمج جميع صلاحيات purchases مع باقي الصلاحيات
        all_perms = list({perm.id: perm for perm in list(queryset) + list(purchases_permissions)}.values())
        self.fields['permissions'].queryset = Permission.objects.filter(id__in=[perm.id for perm in all_perms]).order_by('content_type__app_label', 'name')
        # تعيين الصلاحيات الحالية للمجموعة إذا كانت موجودة
        if self.instance and self.instance.pk:
            current_permissions = self.instance.permissions.all()
            if self.user and not (self.user.user_type in ['superadmin', 'admin'] or self.user.is_superuser):
                current_permissions = current_permissions.exclude(
                    codename__in=[
                        'can_access_system_management',
                        'can_manage_users', 
                        'can_view_audit_logs',
                        'can_backup_system'
                    ]
                )
            self.fields['permissions'].initial = list(current_permissions.values_list('pk', flat=True))
        
        # إضافة حقل dashboard_sections
        self.fields['dashboard_sections'] = forms.MultipleChoiceField(
            choices=[
                ('sales_stats', _('Sales statistics')),
                    ('purchases_stats', _('Purchases statistics')),
                    ('banks_balances', _('Bank and cashbox balances')),
                    ('quick_links', _('Quick links')),
                    ('sales_purchases_distribution', _('Sales/Purchases distribution (current month)')),
                    ('monthly_performance', _('Monthly performance')),
            ],
            widget=forms.CheckboxSelectMultiple,
            required=False,
            label=_('Dashboard Sections')
        )
        
        # تعيين أقسام لوحة التحكم من البيانات المحفوظة أو الافتراضية
        if self.instance and self.instance.pk:
            self.fields['dashboard_sections'].initial = self.instance.dashboard_sections.split(',') if self.instance.dashboard_sections else []
        else:
            # تعيين أقسام لوحة التحكم تلقائياً للمستخدمين المميزين
            self.fields['dashboard_sections'].initial = ['sales_stats', 'purchases_stats', 'banks_balances', 'quick_links', 'sales_purchases_distribution', 'monthly_performance']
    
    def save(self, commit=True):
        group = super().save(commit=False)
        if commit:
            # حفظ is_system_group إذا كان الحقل موجوداً
            if 'is_system_group' in self.cleaned_data:
                group.is_system_group = self.cleaned_data['is_system_group']
            group.save()
            
            # حفظ dashboard_sections
            group.dashboard_sections = ','.join(self.cleaned_data.get('dashboard_sections', []))
            group.save()
        return group


class UserGroupUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """عرض تعديل مجموعة"""
    model = Group
    form_class = GroupEditForm
    template_name = 'users/group_edit.html'
    success_url = reverse_lazy('users:group_list')
    
    def test_func(self):
        user = self.request.user
        return user.is_staff or user.is_superuser or getattr(user, 'user_type', None) in ['admin', 'superadmin']
    
    def get_form_kwargs(self):
        """تمرير المستخدم للنموذج لتصفية الصلاحيات"""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # الحصول على جميع الصلاحيات
        queryset = Permission.objects.select_related('content_type').order_by('content_type__app_label', 'name')

        # تصفية صلاحيات superadmin إذا لم يكن المستخدم superadmin أو admin
        if not (getattr(self.request.user, 'user_type', None) in ['superadmin', 'admin'] or self.request.user.is_superuser):
            queryset = queryset.exclude(
                codename__in=[
                    'can_access_system_management',
                    'can_manage_users',
                    'can_view_audit_logs'
                ]
            )

        # تنظيم الصلاحيات حسب التطبيق
        permissions_by_app = {}
        for permission in queryset:
            app_label = permission.content_type.app_label
            if app_label not in permissions_by_app:
                permissions_by_app[app_label] = []

            # إضافة ترجمة للصلاحية
            permission.translated_name = self._get_permission_translation(permission)
            permissions_by_app[app_label].append(permission)

        context['permissions_by_app'] = permissions_by_app

        # إضافة أسماء التطبيقات المترجمة
        context['app_names'] = self._get_app_names()

        # إضافة معلومات إضافية مطلوبة للقالب
        context['group_users'] = self.object.user_set.all()
        context['current_permissions'] = list(self.object.permissions.values_list('pk', flat=True))

        # استخدام initial من النموذج لضمان ظهور الأقسام المختارة تلقائياً
        form = self.get_form()
        context['dashboard_sections_list'] = form.fields['dashboard_sections'].initial or []

        # إضافة wrapper للصلاحيات
        from django.contrib.auth.context_processors import PermWrapper
        context['perms'] = PermWrapper(self.request.user)

        return context
    
    def dispatch(self, request, *args, **kwargs):
        """منع تعديل المجموعات التي تحتوي على صلاحيات superadmin للمستخدمين غير superadmin"""
        self.object = self.get_object()
        user = self.request.user
        if not (user.is_authenticated and (getattr(user, 'user_type', None) == 'superadmin' or user.is_superuser)):
            superadmin_permissions_in_group = self.object.permissions.filter(
                codename__in=[
                    'can_access_system_management',
                    'can_manage_users', 
                    'can_view_audit_logs',
                    'can_backup_system'
                ]
            )
            if superadmin_permissions_in_group.exists():
                messages.error(self.request, _('You cannot edit this group - it contains permissions reserved for superadmin only'))
                return redirect('users:group_list')
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        try:
            # التأكد من أننا نحدث المجموعة الموجودة وليس إنشاء جديدة
            group = self.object
            group.name = form.cleaned_data['name']
            group.save()
            
            # تحديث الصلاحيات (signals ستتولى تنظيف cache)
            # إذا لم يكن المستخدم superadmin، نحتفظ بصلاحيات superadmin الموجودة
            if self.request.user and not (getattr(self.request.user, 'user_type', None) == 'superadmin' or self.request.user.is_superuser):
                # الحصول على صلاحيات superadmin الموجودة حالياً في المجموعة
                existing_superadmin_permissions = group.permissions.filter(
                    codename__in=[
                        'can_access_system_management',
                        'can_manage_users', 
                        'can_view_audit_logs',
                        'can_backup_system'
                    ]
                )
                
                # مسح كل الصلاحيات وإضافة الجديدة
                group.permissions.clear()
                for permission in form.cleaned_data['permissions']:
                    group.permissions.add(permission)
                    
                # إعادة إضافة صلاحيات superadmin الموجودة
                for permission in existing_superadmin_permissions:
                    group.permissions.add(permission)
            else:
                # للسوبر أدمين، يمكنه تعديل كل الصلاحيات
                group.permissions.clear()
                for permission in form.cleaned_data['permissions']:
                    group.permissions.add(permission)
            
            # حفظ dashboard_sections
            group.dashboard_sections = ','.join(form.cleaned_data.get('dashboard_sections', []))
            
            # حفظ is_system_group إذا كان متوفراً ومسموح للمستخدم الحالي
            if 'is_system_group' in form.cleaned_data and (getattr(self.request.user, 'user_type', None) == 'superadmin' or self.request.user.is_superuser):
                old_protected = getattr(group, 'is_system_group', False)
                group.is_system_group = form.cleaned_data['is_system_group']
                if old_protected != group.is_system_group:
                    protection_status = _('Protected') if group.is_system_group else _('Unprotected')
                    log_user_activity(
                        self.request,
                        'update',
                        group,
                        _('Changed group protection status to: {}').format(protection_status)
                    )
            
            group.save()
            
            # تسجيل النشاط في سجل الأنشطة
            log_user_activity(
                self.request, 
                'update', 
                group, 
                _('Updated user group: {} with {} permissions and dashboard sections: {}').format(
                    group.name,
                    len(form.cleaned_data["permissions"]),
                    ", ".join(form.cleaned_data.get("dashboard_sections", []))
                )
            )
            
            messages.success(self.request, _('The group has been updated successfully.'))
            return redirect(self.success_url)
        except Exception as e:
            messages.error(self.request, _('An error occurred while updating the group: {}').format(str(e)))
            return self.form_invalid(form)
    
    def _get_permission_translation(self, permission):
        """ترجمة اسم الصلاحية"""
        translations = {
            # صلاحيات القيود اليومية
            'add_journalentry': _('Add Journal Entry'),
            'change_journalentry': _('Change Journal Entry'),
            'delete_journalentry': _('Delete Journal Entry'),
            'view_journalentry': _('View Journal Entry'),
            'change_journalentry_entry_number': _('Change Journal Entry Number'),
            'add_account': _('Add Account'),
            'change_account': _('Change Account'),
            'delete_account': _('Delete Account'),
            'view_account': _('View Account'),
            
            # صلاحيات الإيرادات والمصروفات
            'can_add_sectors': _('Add Sectors'),
            'can_edit_sectors': _('Edit Sectors'),
            'can_delete_sectors': _('Delete Sectors'),
            'can_view_sectors': _('View Sectors'),
            'can_add_categories': _('Add Revenue/Expense Categories'),
            'can_edit_categories': _('Edit Revenue/Expense Categories'),
            'can_delete_categories': _('Delete Revenue/Expense Categories'),
            'can_view_categories': _('View Revenue/Expense Categories'),
            'can_add_entries': _('Add Revenue/Expense Entries'),
            'can_edit_entries': _('Edit Revenue/Expense Entries'),
            'can_delete_entries': _('Delete Revenue/Expense Entries'),
            'can_view_entries': _('View Revenue/Expense Entries'),
            'can_add_recurring': _('Add Recurring Revenue/Expense'),
            'can_edit_recurring': _('Edit Recurring Revenue/Expense'),
            'can_delete_recurring': _('Delete Recurring Revenue/Expense'),
            'can_view_recurring': _('View Recurring Revenue/Expense'),
            
            # صلاحيات المبيعات
            'add_salesinvoice': _('Add Sales Invoice'),
            'change_salesinvoice': _('Change Sales Invoice'),
            'delete_salesinvoice': _('Delete Sales Invoice'),
            'view_salesinvoice': _('View Sales Invoice'),
            'add_salesinvoiceitem': _('Add Sales Invoice Item'),
            'change_salesinvoiceitem': _('Change Sales Invoice Item'),
            'delete_salesinvoiceitem': _('Delete Sales Invoice Item'),
            'view_salesinvoiceitem': _('View Sales Invoice Item'),
            
            # صلاحيات المشتريات
            'add_purchaseinvoice': _('Add Purchase Invoice'),
            'change_purchaseinvoice': _('Change Purchase Invoice'),
            'delete_purchaseinvoice': _('Delete Purchase Invoice'),
            'view_purchaseinvoice': _('View Purchase Invoice'),
            'add_purchaseinvoiceitem': _('Add Purchase Invoice Item'),
            'change_purchaseinvoiceitem': _('Change Purchase Invoice Item'),
            'delete_purchaseinvoiceitem': _('Delete Purchase Invoice Item'),
            'view_purchaseinvoiceitem': _('View Purchase Invoice Item'),
            
            # صلاحيات العملاء والموردين
            'add_customersupplier': _('Add Customer/Supplier'),
            'change_customersupplier': _('Change Customer/Supplier'),
            'delete_customersupplier': _('Delete Customer/Supplier'),
            'view_customersupplier': _('View Customer/Supplier'),
            
            # صلاحيات المنتجات
            'add_product': _('Add Product'),
            'change_product': _('Change Product'),
            'delete_product': _('Delete Product'),
            'view_product': _('View Product'),
            'add_category': _('Add Category'),
            'change_category': _('Change Category'),
            'delete_category': _('Delete Category'),
            'view_category': _('View Category'),
            'view_account': _('View Account'),
            
            # صلاحيات الإيرادات والمصروفات
            'can_add_sectors': _('Add Sectors'),
            'can_edit_sectors': _('Edit Sectors'),
            'can_delete_sectors': _('Delete Sectors'),
            'can_view_sectors': _('View Sectors'),
            'can_add_categories': _('Add Revenue/Expense Categories'),
            'can_edit_categories': _('Edit Revenue/Expense Categories'),
            'can_delete_categories': _('Delete Revenue/Expense Categories'),
            'can_view_categories': _('View Revenue/Expense Categories'),
            'can_add_entries': _('Add Revenue/Expense Entries'),
            'can_edit_entries': _('Edit Revenue/Expense Entries'),
            'can_delete_entries': _('Delete Revenue/Expense Entries'),
            'can_view_entries': _('View Revenue/Expense Entries'),
            'can_add_recurring': _('Add Recurring Revenue/Expense'),
            'can_edit_recurring': _('Edit Recurring Revenue/Expense'),
            'can_delete_recurring': _('Delete Recurring Revenue/Expense'),
            'can_view_recurring': _('View Recurring Revenue/Expense'),
            
            # صلاحيات المبيعات
            'add_salesinvoice': _('Add Sales Invoice'),
            'change_salesinvoice': _('Change Sales Invoice'),
            'delete_salesinvoice': _('Delete Sales Invoice'),
            'view_salesinvoice': _('View Sales Invoice'),
            'add_salesinvoiceitem': _('Add Sales Invoice Item'),
            'change_salesinvoiceitem': _('Change Sales Invoice Item'),
            'delete_salesinvoiceitem': _('Delete Sales Invoice Item'),
            'view_salesinvoiceitem': _('View Sales Invoice Item'),
            
            # صلاحيات المشتريات
            'add_purchaseinvoice': _('Add Purchase Invoice'),
            'change_purchaseinvoice': _('Change Purchase Invoice'),
            'delete_purchaseinvoice': _('Delete Purchase Invoice'),
            'view_purchaseinvoice': _('View Purchase Invoice'),
            'add_purchaseinvoiceitem': _('Add Purchase Invoice Item'),
            'change_purchaseinvoiceitem': _('Change Purchase Invoice Item'),
            'delete_purchaseinvoiceitem': _('Delete Purchase Invoice Item'),
            'view_purchaseinvoiceitem': _('View Purchase Invoice Item'),
            
            # صلاحيات العملاء والموردين
            'add_customersupplier': _('Add Customer/Supplier'),
            'change_customersupplier': _('Change Customer/Supplier'),
            'delete_customersupplier': _('Delete Customer/Supplier'),
            'view_customersupplier': _('View Customer/Supplier'),
            
            # صلاحيات المنتجات
            'add_product': _('Add Product'),
            'change_product': _('Change Product'),
            'delete_product': _('Delete Product'),
            'view_product': _('View Product'),
            'add_category': _('Add Category'),
            'change_category': _('Change Category'),
            'delete_category': _('Delete Category'),
            'view_category': _('View Category'),
            
            # صلاحيات المخزون
            'add_warehouse': _('Add Warehouse'),
            'change_warehouse': _('Change Warehouse'),
            'delete_warehouse': _('Delete Warehouse'),
            'view_warehouse': _('View Warehouse'),
            'add_inventorymovement': _('Add Inventory Movement'),
            'change_inventorymovement': _('Change Inventory Movement'),
            'delete_inventorymovement': _('Delete Inventory Movement'),
            'view_inventorymovement': _('View Inventory Movement'),
            
            # صلاحيات الأصول والخصوم
            'can_view_asset_categories': _('View Asset Categories'),
            'can_add_asset_categories': _('Add Asset Categories'),
            'can_edit_asset_categories': _('Edit Asset Categories'),
            'can_delete_asset_categories': _('Delete Asset Categories'),
            'can_view_assets': _('View Assets'),
            'can_add_assets': _('Add Assets'),
            'can_edit_assets': _('Edit Assets'),
            'can_delete_assets': _('Delete Assets'),
            'can_view_liability_categories': _('View Liability Categories'),
            'can_add_liability_categories': _('Add Liability Categories'),
            'can_edit_liability_categories': _('Edit Liability Categories'),
            'can_delete_liability_categories': _('Delete Liability Categories'),
            'can_view_liabilities': _('View Liabilities'),
            'can_add_liabilities': _('Add Liabilities'),
            'can_edit_liabilities': _('Edit Liabilities'),
            'can_delete_liabilities': _('Delete Liabilities'),
            'can_view_depreciation_entries': _('View Depreciation Entries'),
            'can_add_depreciation_entries': _('Add Depreciation Entries'),
            'can_edit_depreciation_entries': _('Edit Depreciation Entries'),
            'can_delete_depreciation_entries': _('Delete Depreciation Entries'),
            
            # صلاحيات البنوك
            'add_bank': _('Add Bank'),
            'change_bank': _('Change Bank'),
            'delete_bank': _('Delete Bank'),
            'view_bank': _('View Bank'),
            'add_bankaccount': _('Add Bank Account'),
            'change_bankaccount': _('Change Bank Account'),
            'delete_bankaccount': _('Delete Bank Account'),
            'view_bankaccount': _('View Bank Account'),
            'can_view_bank_accounts': _('Can View Bank Accounts'),
            'can_add_bank_accounts': _('Can Add Bank Accounts'),
            'can_edit_bank_accounts': _('Can Edit Bank Accounts'),
            'can_delete_bank_accounts': _('Can Delete Bank Accounts'),
            
            # صلاحيات الصناديق
            'add_cashbox': _('Add Cashbox'),
            'change_cashbox': _('Change Cashbox'),
            'delete_cashbox': _('Delete Cashbox'),
            'view_cashbox': _('View Cashbox'),
            
            # صلاحيات المدفوعات والمقبوضات
            'add_payment': _('Add Payment'),
            'change_payment': _('Change Payment'),
            'delete_payment': _('Delete Payment'),
            'view_payment': _('View Payment'),
            'add_receipt': _('Add Receipt'),
            'change_receipt': _('Change Receipt'),
            'delete_receipt': _('Delete Receipt'),
            'view_receipt': _('View Receipt'),
            
            # صلاحيات المستخدمين
            'add_user': _('Add User'),
            'change_user': _('Change User'),
            'delete_user': _('Delete User'),
            'view_user': _('View User'),
            'add_group': _('Add Group'),
            'change_group': _('Change Group'),
            'delete_group': _('Delete Group'),
            'view_group': _('View Group'),
            
            # صلاحيات النظام الأساسي
            'add_companysettings': _('Add Company Settings'),
            'change_companysettings': _('Change Company Settings'),
            'delete_companysettings': _('Delete Company Settings'),
            'view_companysettings': _('View Company Settings'),
            'add_auditlog': _('Add Audit Log'),
            'change_auditlog': _('Change Audit Log'),
            'delete_auditlog': _('Delete Audit Log'),
            'view_auditlog': _('View Audit Log'),
            
            # صلاحيات النسخ الاحتياطية
            'can_restore_backup': _('Restore Backups'),
            'delete_backup': _('Delete Backup Files'),
            'can_delete_advanced_data': _('Delete Advanced Data'),
            'can_backup_system': _('Create System Backups'),
            
            # ??????? ????????
            'can_view_sales_reports': _('Can View Sales Reports'),
            'can_view_sales_by_representative_report': _('Can View Sales By Representative Report'),
            'can_view_purchase_reports': _('Can View Purchase Reports'),
            'can_view_profit_loss_report': _('Can View Profit and Loss Report'),
            'can_view_balance_sheet': _('Can View Balance Sheet'),
            'can_view_trial_balance': _('Can View Trial Balance'),
            'can_view_income_statement': _('Can View Income Statement'),
            'can_view_cash_flow_statement': _('Can View Cash Flow Statement'),
            'can_view_financial_ratios': _('Can View Financial Ratios'),
            'can_view_aging_report': _('Can View Aging Report'),
            'can_view_tax_report': _('Can View Tax Report'),
            'can_view_stock_balance_report': _('Can View Stock Balance Report'),
            'can_view_customer_statement': _('Can View Customer Statement'),
            'can_view_documents_report': _('Can View Documents Report'),
        }
        
        return translations.get(permission.codename, permission.name)
    
    def _get_app_names(self):
        """أسماء التطبيقات المترجمة"""
        return {
            'journal': _('Journal Entries'),
            'sales': _('Sales'),
            'purchases': _('Purchases'),
            'customers': _('Customers and Suppliers'),
            'products': _('Categories and Products'),
            'inventory': _('Inventory Management'),
            'assets_liabilities': _('Assets & Liabilities'),
            'revenues_expenses': _('Revenues & Expenses'),
            'banks': _('Banks'),
            'cashboxes': _('Cashboxes'),
            'payments': _('Payments'),
            'receipts': _('Receipts'),
            'users': _('System Management'),
            'core': _('Core'),
            'backup': _('Backups'),
            'hr': _('Human Resources'),
            'reports': _('Reports'),
            'settings': _('Advanced System Settings'),
        }


class UserGroupDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """عرض حذف مجموعة"""
    model = Group
    template_name = 'users/group_delete.html'
    success_url = reverse_lazy('users:group_list')
    
    def test_func(self):
        user = self.request.user
        return user.is_staff or user.is_superuser or getattr(user, 'user_type', None) in ['admin', 'superadmin']
    
    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        
        # منع حذف مجموعات النظام المحمية إلا للسوبر أدمين
        if getattr(self.object, 'is_system_group', False) and not (getattr(request.user, 'user_type', None) == 'superadmin' or request.user.is_superuser):
            messages.error(request, _('This group is protected from deletion. Only superadmin can delete it.'))
            return redirect('users:group_list')
        
        # منع المستخدمين غير superadmin من حذف المجموعات التي تحتوي على صلاحيات superadmin
        if not (request.user.user_type == 'superadmin' or request.user.is_superuser):
            superadmin_permissions_in_group = self.object.permissions.filter(
                codename__in=[
                    'can_access_system_management',
                    'can_manage_users', 
                    'can_view_audit_logs',
                    'can_backup_system'
                ]
            )
            
            if superadmin_permissions_in_group.exists():
                messages.error(request, _('You cannot delete this group - it contains permissions reserved for superadmin only.'))
                return redirect('users:group_list')
        
        return super().dispatch(request, *args, **kwargs)
    
    def delete(self, request, *args, **kwargs):
        try:
            group_name = self.object.name
            user_count = self.object.user_set.count()
            
            if user_count > 0:
                messages.warning(request, _('Warning: This group contains {} users who will lose group permissions').format(user_count))
            
            # تسجيل النشاط قبل الحذف
            log_user_activity(
                request, 
                'delete', 
                self.object, 
                _('Deleted user group: {}').format(group_name)
            )
            
            response = super().delete(request, *args, **kwargs)
            messages.success(request, _('Group "{}" deleted successfully').format(group_name))
            return response
        except Exception as e:
            messages.error(request, _('An error occurred while deleting the group: {}').format(str(e)))
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
        return JsonResponse({'success': False, 'error': _('Not allowed')}, status=403)
    
    # الحصول على الحالة الحالية من الجلسة
    current_state = request.session.get('hide_superusers', False)
    new_state = not current_state
    
    # حفظ الحالة الجديدة في الجلسة
    request.session['hide_superusers'] = new_state
    
    return JsonResponse({
        'success': True, 
        'hide_superusers': new_state,
        'message': _('High privileged users are hidden') if new_state else _('High privileged users are shown.')
    })