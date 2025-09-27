from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.http import JsonResponse, HttpResponse, Http404
from django.contrib import messages
from django.core import serializers
from django.apps import apps
from django.conf import settings
from django.utils.translation import gettext as _
from django.utils import timezone
from django.db import transaction
from django.db import models
from django.db.models.deletion import ProtectedError
from django.core.cache import cache
from django.template.defaultfilters import filesizeformat
from django.urls import reverse
import json
import os
import threading
import time
import logging
from datetime import datetime as dt_module
from openpyxl import Workbook
from decimal import Decimal

# إضافة AuditLog import
try:
    from core.models import AuditLog
    AUDIT_AVAILABLE = True
except ImportError:
    AUDIT_AVAILABLE = False

logger = logging.getLogger(__name__)


def log_audit(user, action, description, obj_id=None):
    """دالة مساعدة لتسجيل الأحداث في سجل المراجعة"""
    if not AUDIT_AVAILABLE or not user:
        return
    
    try:
        AuditLog.objects.create(
            user=user,
            action_type=action,
            content_type='backup_system',
            object_id=obj_id,
            description=description
        )
    except Exception as e:
        logger.warning(f"فشل في تسجيل الحدث في سجل المراجعة: {str(e)}")


def get_backup_progress_data():
    """الحصول على بيانات تقدم النسخ الاحتياطي من cache"""
    return cache.get('backup_progress', {
        'is_running': False,
        'current_table': '',
        'processed_tables': 0,
        'total_tables': 0,
        'processed_records': 0,
        'total_records': 0,
        'percentage': 0,
        'status': 'idle',
        'error': None,
        'tables_status': [],
        'estimated_time': ''
    })

def set_backup_progress_data(data):
    """تحديث بيانات تقدم النسخ الاحتياطي في cache"""
    import time
    current_time = time.time()
    cache.set('backup_progress', data, timeout=3600)
    cache.set('backup_last_update', current_time, timeout=3600)
    
    # تحديث آخر نسبة مئوية للمراقبة
    if 'percentage' in data:
        cache.set('backup_last_percentage', data['percentage'], timeout=3600)


def get_restore_progress_data():
    """الحصول على بيانات تقدم الاستعادة من cache"""
    return cache.get('restore_progress', {
        'is_running': False,
        'current_table': '',
        'processed_tables': 0,
        'total_tables': 0,
        'processed_records': 0,
        'total_records': 0,
        'percentage': 0,
        'status': 'idle',
        'error': None,
        'tables_status': [],
        'estimated_time': ''
    })


@login_required
def get_deletable_tables(request):
    """API تعرض الجداول التي يمكن حذفها مع فحص التبعيات بين النماذج.
    سترجع قائمة من العناصر: { app_name, model_name, display_name, record_count, dependents: [labels], safe_to_delete }
    safe_to_delete True يعني أنه لا يوجد نموذج آخر يعتمد على هذا النموذج (FK) بخلاف التطبيقات المستبعدة.
    """
    
    # فحص الصلاحية
    if not request.user.has_perm('backup.can_delete_advanced_data'):
        # تسجيل محاولة الوصول غير المسموح
        log_audit(request.user, 'denied', _('محاولة وصول مرفوضة لعرض قائمة الجداول القابلة للحذف - صلاحية غير متوفرة'))
        return JsonResponse({'success': False, 'error': _('ليس لديك صلاحية للوصول لهذه الميزة')})
    
    try:
        result = []
        
        # قائمة التطبيقات المحمية من Django (يجب استبعادها من قائمة الحذف)
        protected_apps = [
            'admin',
            'auth',
            'contenttypes',
            'sessions',
            'messages',
            'staticfiles',
            'corsheaders',
            'rest_framework',
            'django_bootstrap5',
            'crispy_forms',
            'crispy_bootstrap5',
        ]
        
        # بناء خريطة العلاقات العكسية: model_label -> set(of dependent model labels)
        dep_map = {}
        all_models = []
        for app_config in apps.get_app_configs():
            # استبعاد التطبيقات المحمية من قائمة الحذف
            if app_config.name in protected_apps:
                continue
                
            for model in app_config.get_models():
                label = f"{app_config.name}.{model._meta.model_name}"
                dep_map[label] = set()
                all_models.append((app_config, model))

        # ملء الخريطة
        for app_config, model in all_models:
            for field in model._meta.get_fields():
                try:
                    if field.is_relation and (field.many_to_one or field.one_to_one) and field.related_model is not None:
                        rel = field.related_model
                        rel_label = f"{rel._meta.app_label}.{rel._meta.model_name}"
                        src_label = f"{app_config.name}.{model._meta.model_name}"
                        dep_map[rel_label].add(src_label)
                except Exception:
                    continue

        # جمع المعلومات لكل نموذج
        for app_config, model in all_models:
            try:
                # تخطي النماذج التي لا تدير جداول في قاعدة البيانات (managed = False)
                if not model._meta.managed:
                    continue
                    
                label = f"{app_config.name}.{model._meta.model_name}"
                display = model._meta.verbose_name or label
                count = model.objects.count()
                dependents = sorted(list(dep_map.get(label, [])))
                # امن للحذف إذا لا يوجد تابعون (dependents) أو التوابع كلها ضمن التطبيقات المستبعدة
                safe = len(dependents) == 0
                result.append({
                    'app_name': app_config.name,
                    'model_name': model._meta.model_name,
                    'label': label,
                    'display_name': str(display),
                    'record_count': count,
                    'dependents': dependents,
                    'safe_to_delete': safe
                })
            except Exception as e:
                logger.warning(f"فشل جلب معلومات النموذج {app_config.name}.{model}: {str(e)}")
                continue

        # رتب بحسب عدد السجلات تنازلياً
        result.sort(key=lambda x: (-x['record_count'], x['label']))
        
        # تسجيل العملية في سجل الأنشطة
        log_audit(request.user, 'view', _('عرض قائمة الجداول القابلة للحذف - تم العثور على {} جدول').format(len(result)))
        
        return JsonResponse({'success': True, 'tables': result})
    except Exception as e:
        logger.error(f"خطأ في get_deletable_tables: {str(e)}")
        # تسجيل الخطأ في سجل الأنشطة
        log_audit(request.user, 'error', _('خطأ في عرض قائمة الجداول القابلة للحذف: {}').format(str(e)))
        return JsonResponse({'success': False, 'error': _('حدث خطأ في تحميل قائمة الجداول')})


@login_required
def delete_selected_tables(request):
    """مسح الجداول المحددة (data-only) بعد فحص التبعيات.
    يتوقع POST body 'tables' كقائمة من labels ['app.model', ...] و 'confirm' boolean.
    سيقوم بحذف جميع السجلات في تلك الجداول داخل معاملة واحدة، ويُسجل كل عملية في AuditLog.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'طريقة طلب غير صحيحة'})

    # فحص الصلاحية
    if not request.user.has_perm('backup.can_delete_advanced_data'):
        # تسجيل محاولة الوصول غير المسموح
        log_audit(request.user, 'denied', _('محاولة وصول مرفوضة لحذف بيانات الجداول - صلاحية غير متوفرة'))
        return JsonResponse({'success': False, 'error': _('ليس لديك صلاحية لحذف البيانات')})

    try:
        payload = json.loads(request.body.decode('utf-8')) if request.body else {}
    except Exception:
        payload = request.POST.dict() if request.POST else {}

    tables = payload.get('tables') or payload.get('labels') or []
    confirm = payload.get('confirm') in [True, 'true', '1', 1, 'on']

    if not tables or not isinstance(tables, list):
        return JsonResponse({'success': False, 'error': 'يرجى تحديد جداول للحذف'})

    if not confirm:
        return JsonResponse({'success': False, 'error': 'يرجى تأكيد الحذف (confirm=true)'})

    try:
        # بناء خريطة التبعية كما في get_deletable_tables
        dep_map = {}
        model_map = {}
        for app_config in apps.get_app_configs():
            for model in app_config.get_models():
                label = f"{app_config.name}.{model._meta.model_name}"
                dep_map[label] = set()
                model_map[label] = model

        for label, model in list(model_map.items()):
            for field in model._meta.get_fields():
                try:
                    if field.is_relation and (field.many_to_one or field.one_to_one) and field.related_model is not None:
                        rel = field.related_model
                        rel_label = f"{rel._meta.app_label}.{rel._meta.model_name}"
                        src_label = label
                        if rel_label in dep_map:
                            dep_map[rel_label].add(src_label)
                except Exception:
                    continue

        # وسّع مجموعة الجداول لتشمل جميع التبعيات المتسلسلة (closure)
        selected_set = set([str(x) for x in tables])
        def add_deps(label):
            for dep in dep_map.get(label, set()):
                if dep not in selected_set:
                    selected_set.add(dep)
                    add_deps(dep)

        for t in list(selected_set):
            add_deps(t)

        # بعد التوسيع، تأكد من عدم وجود تبعيات خارج المجموعه النهائية
        cannot_delete = []
        for t in list(selected_set):
            dependents = dep_map.get(t, set())
            external = [d for d in dependents if d not in selected_set]
            if external:
                cannot_delete.append({'table': t, 'blocked_by': external})

        if cannot_delete:
            return JsonResponse({'success': False, 'error': 'بعض الجداول لا يمكن حذفها بسبب تبعيات خارجية', 'details': cannot_delete})

        # احسب ترتيب الحذف بحيث تُحذف التبعيات أولاً (post-order)
        visited = set()
        delete_order = []
        def dfs(label):
            if label in visited:
                return
            visited.add(label)
            for dep in dep_map.get(label, set()):
                if dep in selected_set:
                    dfs(dep)
            delete_order.append(label)

        for label in list(selected_set):
            dfs(label)

    except Exception as e:
        logger.error(f"خطأ في بناء خريطة التبعية أو حساب ترتيب الحذف: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})

    # تنفيذ الحذف داخل معاملة وبترتيب آمن
    deleted_stats = []
    audit_reassign_notifications = []
    try:
        with transaction.atomic():
            for t in delete_order:
                model = model_map.get(t)
                if model is None:
                    continue
                try:
                    # Special handling for User model: create or keep a fallback '__deleted_user__' user
                    UserModel = None
                    try:
                        from django.contrib.auth import get_user_model
                        UserModel = get_user_model()
                    except Exception:
                        UserModel = None

                    if UserModel is not None and getattr(model, '__name__', '').lower() == getattr(UserModel, '__name__', '').lower():
                        # ensure fallback exists
                        fallback_username = '__deleted_user__'
                        fallback = UserModel.objects.filter(username=fallback_username).first()
                        if not fallback:
                            # create minimal fallback user
                            fallback = UserModel.objects.create(username=fallback_username, is_active=False)

                        # reassign AuditLog.user entries that reference users we will delete to fallback
                        try:
                            user_ids = list(model.objects.exclude(pk=fallback.pk).values_list('pk', flat=True))
                            from core.models import AuditLog as _AuditLog
                            if user_ids:
                                _AuditLog.objects.filter(user_id__in=user_ids).update(user_id=fallback.pk)
                        except Exception as reassign_err:
                            logger.warning(f"Failed to reassign AuditLog.user before deleting users: {reassign_err}")

                        # notify front-end that we reassigned audit logs for this table
                        audit_reassign_notifications.append({'table': t, 'fallback': fallback.username, 'reassigned_count': len(user_ids)})

                        # delete all users except fallback
                        qs = model.objects.exclude(pk=fallback.pk)
                        count = qs.count()
                        qs.delete()
                        deleted_stats.append({'table': t, 'deleted': count})
                        from django.utils.translation import gettext as _
                        log_audit(request.user, 'delete', _('Deleted all records from table %(table)s - count: %(count)s') % {'table': t, 'count': count})
                        continue

                    # Default deletion path for other models
                    count = model.objects.all().count()
                    # حاول حذف السجلات؛ إذا كان هناك FK محمي فسيُثار ProtectedError أو قد يحدث IntegrityError
                    try:
                        model.objects.all().delete()
                    except Exception as del_exc:
                        from django.db import IntegrityError
                        if isinstance(del_exc, IntegrityError):
                            # Special retry logic for User model: try to reassign AuditLog.user references then retry
                            try:
                                from django.contrib.auth import get_user_model
                                UserModelLocal = get_user_model()
                            except Exception:
                                UserModelLocal = None

                            if UserModelLocal is not None and getattr(model, '__name__', '').lower() == getattr(UserModelLocal, '__name__', '').lower():
                                # perform reassignment of AuditLog entries to fallback
                                try:
                                    fallback_username = '__deleted_user__'
                                    fallback = UserModelLocal.objects.filter(username=fallback_username).first()
                                    if not fallback:
                                        fallback = UserModelLocal.objects.create(username=fallback_username, is_active=False)
                                    user_ids = list(model.objects.exclude(pk=fallback.pk).values_list('pk', flat=True))
                                    from core.models import AuditLog as _AuditLog
                                    if user_ids:
                                        _AuditLog.objects.filter(user_id__in=user_ids).update(user_id=fallback.pk)
                                    # retry delete
                                    model.objects.exclude(pk=fallback.pk).delete()
                                except Exception as reassign_err:
                                    logger.error(f"Failed to reassign AuditLog on IntegrityError: {reassign_err}")
                                    raise del_exc
                            else:
                                raise del_exc

                    deleted_stats.append({'table': t, 'deleted': count})
                    from django.utils.translation import gettext as _
                    log_audit(request.user, 'delete', _('Deleted all records from table %(table)s - count: %(count)s') % {'table': t, 'count': count})
                except ProtectedError as p_err:
                    # جمع تفاصيل يمنع الحذف بسبب ProtectedError
                    blockers = []
                    try:
                        # ProtectedError.args may include a list/queryset of blocking objects
                        for item in getattr(p_err, 'protected_objects', []) or []:
                            try:
                                blockers.append(str(item))
                            except Exception:
                                blockers.append(repr(item))
                    except Exception:
                        blockers = [str(p_err)]
                    logger.warning(f"ProtectedError deleting {t}: {blockers}")
                    return JsonResponse({'success': False, 'error': 'ProtectedError', 'details': {'table': t, 'blocked_by_instances': blockers}})

        return JsonResponse({'success': True, 'deleted': deleted_stats, 'audit_reassign_notifications': audit_reassign_notifications})
    except Exception as e:
        logger.error(f"خطأ في delete_selected_tables: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})


def set_restore_progress_data(data):
    """تحديث بيانات تقدم الاستعادة في cache"""
    import time
    current_time = time.time()
    cache.set('restore_progress', data, timeout=3600)
    cache.set('restore_last_update', current_time, timeout=3600)
    if 'percentage' in data:
        cache.set('restore_last_percentage', data['percentage'], timeout=3600)


class BackupRestoreView(LoginRequiredMixin, TemplateView):
    """صفحة إدارة النسخ الاحتياطية والاستعادة"""
    template_name = 'backup/backup_restore.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # إنشاء مجلد النسخ الاحتياطية إذا لم يكن موجوداً
        backup_dir = os.path.join(settings.MEDIA_ROOT, 'backups')
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        # جلب قائمة النسخ الاحتياطية
        backups = []
        for filename in os.listdir(backup_dir):
            if filename.endswith('.json') or filename.endswith('.xlsx'):
                filepath = os.path.join(backup_dir, filename)
                try:
                    stat = os.stat(filepath)
                    file_type = 'XLSX' if filename.endswith('.xlsx') else 'JSON'
                    backups.append({
                        'filename': filename,
                        'size': filesizeformat(stat.st_size),
                        'created_at': dt_module.fromtimestamp(stat.st_mtime),
                        'path': filepath,
                        'type': file_type
                    })
                except (OSError, IOError):
                    continue

        # ترتيب النسخ حسب تاريخ الإنشاء (الأحدث أولاً)
        backups.sort(key=lambda x: x['created_at'], reverse=True)

        context['backups'] = backups
        context['is_superuser'] = self.request.user.is_superuser
        return context


@login_required
def get_backup_progress(request):
    """الحصول على حالة تقدم النسخ الاحتياطي"""
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'error': 'يجب تسجيل الدخول أولاً',
            'progress': None
        }, status=401)
    
    progress_data = get_backup_progress_data()
    
    # التحقق من العمليات المعلقة وحذفها إذا مر وقت طويل
    if progress_data.get('is_running', False):
        # إذا كانت العملية تعمل لأكثر من 30 دقيقة، قم بإلغائها
        import time
        current_time = time.time()
        
        # إذا لم يتم تحديث الحالة لمدة 10 دقائق، اعتبر العملية معلقة
        last_update_key = 'backup_last_update'
        last_update = cache.get(last_update_key, current_time)
        
        if current_time - last_update > 600:  # 10 دقائق
            # العملية معلقة، قم بإلغائها
            cache.delete('backup_progress')
            cache.delete(last_update_key)
            
            log_audit(request.user, 'delete', 'تم إلغاء عملية النسخ الاحتياطي المعلقة تلقائياً')
    
    return JsonResponse({
        'success': True,
        'progress': progress_data
    })


@login_required
def clear_backup_cache(request):
    """مسح كاش النسخ الاحتياطي"""
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'error': 'طريقة طلب غير صحيحة'
        })
    
    try:
        cache.delete('backup_progress')
        cache.delete('backup_last_update')
        
        log_audit(request.user, 'delete', 'تم مسح كاش النسخ الاحتياطية يدوياً')
        
        return JsonResponse({
            'success': True,
            'message': 'تم مسح الكاش بنجاح'
        })
        
    except Exception as e:
        logger.error(f"خطأ في مسح الكاش: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


def get_backup_tables_info():
    """الحصول على معلومات مفصلة عن جميع الجداول في قاعدة البيانات"""
    tables_info = []
    
    # قائمة التطبيقات المستثناة من النسخ الاحتياطي (تطبيقات Django الأساسية فقط)
    excluded_apps = [
        'django.contrib.admin',
        'django.contrib.contenttypes', 
        'django.contrib.sessions',
        'django.contrib.messages',
        'django.contrib.staticfiles',
        'corsheaders',
        'rest_framework',
        'django_bootstrap5',
        'crispy_forms',
        'crispy_bootstrap5',
    ]
    
    try:
        for app_config in apps.get_app_configs():
            if app_config.name in excluded_apps:
                continue
                
            for model in app_config.get_models():
                # تجاهل النماذج التي لا تنشئ جداول (managed = False)
                if getattr(model._meta, 'managed', True) is False:
                    continue
                    
                try:
                    record_count = model.objects.count()
                    tables_info.append({
                        'app_name': app_config.name,
                        'model_name': model._meta.model_name,
                        'display_name': model._meta.verbose_name or f"{app_config.verbose_name} - {model._meta.model_name}",
                        'record_count': record_count,
                        'status': 'pending',
                        'progress': 0,
                        'actual_records': 0,
                        'error': None
                    })
                except Exception as e:
                    # تجاهل النماذج التي تسبب أخطاء (مثل الجداول غير الموجودة)
                    logger.warning(f"تجاهل النموذج {model._meta.model_name} بسبب خطأ: {str(e)}")
                    continue
        
        return tables_info
        
    except Exception as e:
        logger.error(f"خطأ في جلب معلومات الجداول: {str(e)}")
        return []


@login_required
def get_backup_tables(request):
    """API للحصول على معلومات الجداول"""
    try:
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'error': 'يجب تسجيل الدخول أولاً'
            }, status=401)
        
        tables_info = get_backup_tables_info()
        return JsonResponse({
            'success': True,
            'tables': tables_info,
            'total_tables': len(tables_info),
            'total_records': sum(table['record_count'] for table in tables_info)
        })
        
    except Exception as e:
        logger.error(f"خطأ في جلب معلومات الجداول: {str(e)}")
        
        log_audit(request.user, 'error', f'خطأ في جلب معلومات الجداول: {str(e)}')
        
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


def perform_backup_task(user, timestamp, filename, filepath, format_type='json'):
    """تنفيذ مهمة النسخ الاحتياطي في خيط منفصل مع تتبع مفصل"""
    
    logger.info(f"🎯 دخول perform_backup_task: user={user.username}, filename={filename}, format={format_type}")
    
    try:
        log_audit(user, 'create', f'بدء إنشاء النسخة الاحتياطية: {filename} - النوع: {format_type.upper()}')
        
        # تحديث حالة البداية
        progress_data = {
            'is_running': True,
            'status': 'starting',
            'error': None,
            'percentage': 0,
            'current_table': 'بدء النسخ الاحتياطي...',
            'processed_tables': 0,
            'total_tables': 0,
            'processed_records': 0,
            'total_records': 0,
            'estimated_time': 'جاري الحساب...',
            'tables_status': []
        }
        set_backup_progress_data(progress_data)
        
        # الحصول على معلومات الجداول
        progress_data['current_table'] = 'تحليل قاعدة البيانات...'
        progress_data['status'] = 'analyzing'
        set_backup_progress_data(progress_data)
        
        tables_info = get_backup_tables_info()
        total_tables = len(tables_info)
        total_records = sum(table['record_count'] for table in tables_info)
        
        # تحديث معلومات الجداول
        for table in tables_info:
            table['status'] = 'pending'
            table['progress'] = 0
            table['actual_records'] = 0
            table['error'] = None
        
        progress_data.update({
            'status': 'preparing',
            'current_table': f'تم العثور على {total_tables} جدول بإجمالي {total_records} سجل',
            'total_tables': total_tables,
            'total_records': total_records,
            'tables_status': tables_info,
            'percentage': 5
        })
        set_backup_progress_data(progress_data)
        
        time.sleep(2)
        
        # إنشاء هيكل النسخة الاحتياطية
        backup_content = {
            'metadata': {
                'backup_name': f'نسخة احتياطية {timestamp}',
                'created_at': timezone.now().isoformat(),
                'created_by': user.username,
                'system_version': '1.0',
                'total_tables': total_tables,
                'total_records': total_records,
                'format': format_type.upper(),
                'description': 'نسخة احتياطية كاملة مع معلومات تفصيلية'
            },
            'data': {}
        }

        # تضمين قائمة بملفات الوسائط المهمة (شعارات النظام وصور الخلفية) ضمن المحتوى
        try:
            media_files = []
            system_media_dir = os.path.join(settings.MEDIA_ROOT, 'system')
            if os.path.exists(system_media_dir):
                for root, dirs, files in os.walk(system_media_dir):
                    for fname in files:
                        fpath = os.path.join(root, fname)
                        rel = os.path.relpath(fpath, settings.MEDIA_ROOT)
                        media_files.append(rel.replace('\\', '/'))
            backup_content['media_files'] = media_files
        except Exception as e:
            logger.warning(f"فشل في حصر ملفات الوسائط للنسخ الاحتياطي: {str(e)}")
        
        # تضمين ملفات الترجمة
        try:
            locale_files = []
            locale_dir = os.path.join(settings.BASE_DIR, 'locale')
            if os.path.exists(locale_dir):
                for root, dirs, files in os.walk(locale_dir):
                    for fname in files:
                        if fname.endswith('.po') or fname.endswith('.mo'):
                            fpath = os.path.join(root, fname)
                            rel = os.path.relpath(fpath, settings.BASE_DIR)
                            locale_files.append(rel.replace('\\', '/'))
            backup_content['locale_files'] = locale_files
        except Exception as e:
            logger.warning(f"فشل في حصر ملفات الترجمة للنسخ الاحتياطي: {str(e)}")
        
        # متغيرات التتبع
        processed_tables = 0
        processed_records = 0
        start_time = time.time()
        
        progress_data = get_backup_progress_data()
        progress_data.update({
            'status': 'processing',
            'current_table': 'بدء معالجة الجداول...',
            'percentage': 10
        })
        set_backup_progress_data(progress_data)
        
        # نسخ البيانات من كل جدول
        for table_index, table_info in enumerate(tables_info):
            app_name = table_info['app_name']
            model_name = table_info['model_name']
            display_name = table_info['display_name']
            expected_records = table_info['record_count']
            
            try:
                progress_data = get_backup_progress_data()
                tables_status = progress_data.get('tables_status', [])
                
                if table_index < len(tables_status):
                    tables_status[table_index]['status'] = 'processing'
                    tables_status[table_index]['progress'] = 0
                
                progress_data.update({
                    'current_table': f'معالجة {display_name}...',
                    'tables_status': tables_status
                })
                set_backup_progress_data(progress_data)
                
                # تسجيل بداية معالجة الجدول
                log_audit(user, 'create', f'بدء نسخ الجدول: {display_name} ({expected_records} سجل متوقع)')
                
                # الحصول على النموذج
                app = apps.get_app_config(app_name)
                model = app.get_model(model_name)
                
                if app_name not in backup_content['data']:
                    backup_content['data'][app_name] = {}
                
                # نسخ البيانات مع معالجة خاصة للحقول الإشكالية
                queryset = model.objects.all()
                
                # تحسين الاستعلامات للنماذج ذات العلاقات
                if hasattr(model, '_meta'):
                    # إضافة select_related للعلاقات الأجنبية المباشرة
                    foreign_keys = [f.name for f in model._meta.fields if hasattr(f, 'related_model') and f.related_model]
                    if foreign_keys:
                        queryset = queryset.select_related(*foreign_keys)
                    
                    # إضافة prefetch_related للعلاقات العكسية المهمة
                    reverse_relations = []
                    for related in model._meta.related_objects:
                        if related.one_to_many or related.many_to_many:
                            reverse_relations.append(related.get_accessor_name())
                    if reverse_relations:
                        queryset = queryset.prefetch_related(*reverse_relations)
                
                actual_records = queryset.count()
                
                if actual_records > 0:
                    # زيادة عدد الأجزاء لتسريع المعالجة (من 10 إلى 50 جزء)
                    chunk_size = max(100, actual_records // 50)  # حد أدنى 100 سجل لكل جزء
                    processed_in_table = 0
                    
                    all_data = []
                    for chunk_start in range(0, actual_records, chunk_size):
                        chunk_end = min(chunk_start + chunk_size, actual_records)
                        chunk_queryset = queryset[chunk_start:chunk_end]
                        
                        try:
                            # محاولة التسلسل العادي أولاً مع التحقق من الحقول المتاحة
                            chunk_data = serializers.serialize('json', chunk_queryset)
                            serialized_data = json.loads(chunk_data)
                            
                            # تنظيف البيانات من الحقول المحذوفة
                            cleaned_data = []
                            for item in serialized_data:
                                if 'fields' in item:
                                    # إزالة الحقول المحذوفة أو غير الموجودة - تم إزالة فلترة is_service
                                    pass
                                cleaned_data.append(item)
                            
                            all_data.extend(cleaned_data)
                            
                        except Exception as serialization_error:
                            # في حالة فشل التسلسل، نعالج السجلات فردياً
                            logger.warning(f"فشل تسلسل chunk في {display_name}: {str(serialization_error)}")
                            
                            for record in chunk_queryset:
                                try:
                                    # محاولة تسلسل سجل واحد
                                    single_data = serializers.serialize('json', [record])
                                    serialized_record = json.loads(single_data)
                                    
                                    # تنظيف البيانات من الحقول المحذوفة
                                    for item in serialized_record:
                                        # تم إزالة فلترة is_service - الحقل لم يعد موجود
                                        pass
                                    
                                    all_data.extend(serialized_record)
                                    
                                except Exception as single_error:
                                    # معالجة خاصة للسجلات التالفة
                                    logger.warning(f"فشل في تسلسل سجل {record.pk} في {display_name}: {str(single_error)}")
                                    
                                    # إنشاء سجل آمن يدوياً
                                    safe_record = {
                                        'model': f"{app_name}.{model_name}",
                                        'pk': record.pk,
                                        'fields': {}
                                    }
                                    
                                    # نسخ الحقول مع تجنب المشاكل
                                    for field in model._meta.fields:
                                        field_name = field.name
                                        
                                        # تم إزالة فلترة is_service - الحقل لم يعد موجود
                                            
                                        try:
                                            value = getattr(record, field_name)
                                            
                                            # معالجة خاصة للحقول الإشكالية
                                            if hasattr(field, 'upload_to'):  # حقول الملفات والصور
                                                if value and hasattr(value, 'name'):
                                                    safe_record['fields'][field_name] = value.name
                                                else:
                                                    safe_record['fields'][field_name] = None
                                            elif hasattr(value, 'isoformat'):  # حقول التاريخ
                                                safe_record['fields'][field_name] = value.isoformat()
                                            elif value is None:
                                                safe_record['fields'][field_name] = None
                                            else:
                                                # التأكد من أن القيمة قابلة للتسلسل
                                                try:
                                                    json.dumps(value)
                                                    safe_record['fields'][field_name] = value
                                                except (TypeError, ValueError):
                                                    safe_record['fields'][field_name] = str(value)
                                                    
                                        except Exception as field_error:
                                            logger.warning(f"فشل في حقل {field_name} للسجل {record.pk}: {str(field_error)}")
                                            safe_record['fields'][field_name] = None
                                    
                                    all_data.append(safe_record)
                                    log_audit(user, 'warning', f'تم إصلاح سجل تالف: {display_name} - المعرف: {record.pk}')
                        
                        processed_in_table = chunk_end
                        table_progress = int((processed_in_table / actual_records) * 100)
                        
                        progress_data = get_backup_progress_data()
                        tables_status = progress_data.get('tables_status', [])
                        if table_index < len(tables_status):
                            tables_status[table_index]['progress'] = table_progress
                        
                        progress_data.update({
                            'current_table': f'{display_name}: {processed_in_table}/{actual_records} ({table_progress}%)',
                            'tables_status': tables_status
                        })
                        set_backup_progress_data(progress_data)
                        
                        time.sleep(0.3)
                    
                    backup_content['data'][app_name][model_name] = all_data
                else:
                    backup_content['data'][app_name][model_name] = []
                
                processed_records += actual_records
                processed_tables += 1
                
                progress_data = get_backup_progress_data()
                tables_status = progress_data.get('tables_status', [])
                if table_index < len(tables_status):
                    tables_status[table_index]['status'] = 'completed'
                    tables_status[table_index]['progress'] = 100
                    tables_status[table_index]['actual_records'] = actual_records
                
                # حساب الوقت المتبقي
                elapsed_time = time.time() - start_time
                if processed_tables > 0:
                    avg_time_per_table = elapsed_time / processed_tables
                    remaining_tables = total_tables - processed_tables
                    estimated_remaining = avg_time_per_table * remaining_tables
                    estimated_time = f"{int(estimated_remaining)} ثانية متبقية تقريباً"
                else:
                    estimated_time = "حساب الوقت المتبقي..."
                
                overall_progress = 10 + int(((processed_tables / total_tables) * 80))
                progress_data.update({
                    'processed_tables': processed_tables,
                    'processed_records': processed_records,
                    'percentage': overall_progress,
                    'tables_status': tables_status,
                    'estimated_time': estimated_time,
                    'current_table': f'اكتمل {display_name} ✅ ({actual_records} سجل)'
                })
                set_backup_progress_data(progress_data)
                
                log_audit(user, 'update', f'اكتمل نسخ الجدول: {display_name} - تم نسخ {actual_records} سجل')
                
                time.sleep(0.5)
                
            except Exception as e:
                error_msg = f"تعذر نسخ جدول {display_name}: {str(e)}"
                logger.error(error_msg)
                
                # تسجيل الخطأ
                log_audit(user, 'error', error_msg)
                
                progress_data = get_backup_progress_data()
                tables_status = progress_data.get('tables_status', [])
                if table_index < len(tables_status):
                    tables_status[table_index]['status'] = 'error'
                    tables_status[table_index]['error'] = str(e)
                    tables_status[table_index]['progress'] = 0
                
                # تحديث الحالة للمتابعة رغم الخطأ
                processed_tables += 1
                overall_progress = 10 + int(((processed_tables / total_tables) * 80))
                
                progress_data.update({
                    'processed_tables': processed_tables,
                    'percentage': overall_progress,
                    'tables_status': tables_status,
                    'current_table': f'⚠️ فشل في {display_name}: {str(e)[:50]}...',
                    'errors': progress_data.get('errors', []) + [error_msg]
                })
                set_backup_progress_data(progress_data)
                
                # متابعة المعالجة للجدول التالي
                time.sleep(1)
                continue
                if table_index < len(tables_status):
                    tables_status[table_index]['status'] = 'error'
                    tables_status[table_index]['error'] = str(e)
                
                progress_data.update({
                    'tables_status': tables_status,
                    'current_table': f'خطأ في {display_name}: {str(e)}'
                })
                set_backup_progress_data(progress_data)
                
                if AUDIT_AVAILABLE:
                    try:
                        AuditLog.objects.create(
                            user=user,
                            action='backup_table_error',
                            details=f'خطأ في نسخ الجدول: {display_name} - {str(e)}'
                        )
                    except Exception:
                        pass
                
                processed_tables += 1
                time.sleep(1)
                continue
        
        # حفظ النسخة الاحتياطية
        progress_data = get_backup_progress_data()
        progress_data.update({
            'current_table': 'حفظ الملف النهائي...',
            'status': 'saving',
            'percentage': 95,
            'estimated_time': 'جاري الحفظ...'
        })
        set_backup_progress_data(progress_data)
        
        try:
            # حفظ حسب النوع المطلوب
            if format_type.lower() == 'xlsx':
                if AUDIT_AVAILABLE:
                    try:
                        AuditLog.objects.create(
                            user=user,
                            action='backup_saving_xlsx',
                            details=f'بدء حفظ النسخة الاحتياطية بصيغة XLSX: {filename}'
                        )
                    except Exception:
                        pass
                save_backup_as_xlsx(backup_content, filepath)
            else:
                if AUDIT_AVAILABLE:
                    try:
                        AuditLog.objects.create(
                            user=user,
                            action='backup_saving_json',
                            details=f'بدء حفظ النسخة الاحتياطية بصيغة JSON: {filename}'
                        )
                    except Exception:
                        pass
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(backup_content, f, ensure_ascii=False, indent=2)
            
            # التأكد من حفظ الملف
            if not os.path.exists(filepath):
                raise Exception(f"فشل في إنشاء الملف: {filepath}")
            
            file_size = os.path.getsize(filepath)
            if file_size == 0:
                raise Exception(f"تم إنشاء ملف فارغ: {filepath}")
                
            logger.info(f"تم حفظ الملف بنجاح: {filepath} - الحجم: {file_size} بايت")
            
        except Exception as save_error:
            logger.error(f"خطأ في حفظ الملف: {str(save_error)}")
            
            if AUDIT_AVAILABLE:
                try:
                    AuditLog.objects.create(
                        user=user,
                        action='backup_save_error',
                        details=f'خطأ في حفظ النسخة الاحتياطية: {filename} - خطأ: {str(save_error)}'
                    )
                except Exception:
                    pass
            
            raise save_error
        
        # تحديث النهاية الناجحة
        progress_data.update({
            'status': 'completed',
            'current_table': 'تم الانتهاء بنجاح! ✅',
            'percentage': 100,
            'is_running': False,
            'estimated_time': 'اكتمل'
        })
        set_backup_progress_data(progress_data)
        
        # حساب إحصائيات الجداول
        empty_tables = 0
        non_empty_tables = 0
        for table_info in tables_info:
            if table_info['record_count'] == 0:
                empty_tables += 1
            else:
                non_empty_tables += 1
        
        # تسجيل النشاط النهائي مع تفاصيل الجداول
        details = f'تم إنشاء النسخة الاحتياطية بنجاح: {filename} - النوع: {format_type.upper()} - إجمالي الجداول: {total_tables} (فارغة: {empty_tables}, تحتوي بيانات: {non_empty_tables}) - السجلات: {processed_records}'
        log_audit(user, 'create', details)
        
        logger.info(f"تم إنشاء النسخة الاحتياطية بنجاح: {filename}")
        
        # تنظيف الكاش بعد فترة قصيرة للسماح للواجهة بقراءة الحالة النهائية
        def cleanup_cache():
            time.sleep(10)  # انتظار 10 ثواني
            cache.delete('backup_progress')
            cache.delete('backup_last_update')
        
        threading.Thread(target=cleanup_cache, daemon=True).start()
        
    except Exception as e:
        logger.error(f"خطأ في إنشاء النسخة الاحتياطية: {str(e)}")
        
        progress_data = get_backup_progress_data()
        progress_data.update({
            'status': 'error',
            'error': str(e),
            'is_running': False,
            'current_table': f'خطأ: {str(e)}'
        })
        set_backup_progress_data(progress_data)
        
        log_audit(user, 'error', f'فشل في إنشاء النسخة الاحتياطية: {filename} - خطأ: {str(e)}')
        
        # تنظيف الكاش بعد فترة قصيرة عند الخطأ أيضاً
        def cleanup_cache_error():
            time.sleep(30)  # انتظار 30 ثانية عند الخطأ
            cache.delete('backup_progress')
            cache.delete('backup_last_update')
        
        threading.Thread(target=cleanup_cache_error, daemon=True).start()
        threading.Thread(target=cleanup_cache_error, daemon=True).start()
        
        raise e


def clean_sheet_name(name):
    """تنظيف اسم ورقة العمل لضمان التوافق مع Excel"""
    # إزالة الأحرف غير المسموحة في Excel
    invalid_chars = ['\\', '/', '?', '*', '[', ']', ':', '\'']
    cleaned_name = str(name) if name else ''
    for char in invalid_chars:
        cleaned_name = cleaned_name.replace(char, '_')
    
    # إزالة النقاط (قد تتسبب في مشاكل)
    cleaned_name = cleaned_name.replace('.', '_')
    
    # إزالة أي أحرف خاصة أخرى قد تسبب مشاكل
    cleaned_name = ''.join(c if c.isalnum() or c in '_- ' else '_' for c in cleaned_name)
    
    # إزالة المسافات المتعددة والاستبدال بـ underscore واحد
    cleaned_name = '_'.join(cleaned_name.split())
    
    # تحديد الطول الأقصى (31 حرف هو الحد الأقصى لـ Excel)
    if len(cleaned_name) > 31:
        cleaned_name = cleaned_name[:31]
    
    # التأكد من أن الاسم ليس فارغاً أو يبدأ برقم
    if not cleaned_name or cleaned_name.isspace() or cleaned_name[0].isdigit():
        cleaned_name = "Sheet_" + cleaned_name[:25] if cleaned_name else "Sheet1"
    
    # التأكد مرة أخيرة من الطول
    if len(cleaned_name) > 31:
        cleaned_name = cleaned_name[:31]
    
    return cleaned_name


def save_backup_as_xlsx(backup_content, filepath):
    """حفظ النسخة الاحتياطية كملف Excel"""
    try:
        logger.info(f"بدء حفظ النسخة الاحتياطية كـ XLSX: {filepath}")
        
        workbook = Workbook()
        
        # حذف الورقة الافتراضية
        workbook.remove(workbook.active)
        
        # إنشاء ورقة للمعلومات العامة
        info_sheet = workbook.create_sheet(title="Backup Info")
        metadata = backup_content.get('metadata', {})
        
        info_sheet['A1'] = 'Backup Name'
        info_sheet['B1'] = metadata.get('backup_name', '')
        info_sheet['A2'] = 'Created At'
        info_sheet['B2'] = metadata.get('created_at', '')
        info_sheet['A3'] = 'Created By'
        info_sheet['B3'] = metadata.get('created_by', '')
        info_sheet['A4'] = 'Total Tables'
        info_sheet['B4'] = metadata.get('total_tables', 0)
        info_sheet['A5'] = 'Total Records'
        info_sheet['B5'] = metadata.get('total_records', 0)
        
        # إنشاء ورقة لكل تطبيق
        data = backup_content.get('data', {})
        sheet_count = 0
        used_sheet_names = set()  # تتبع الأسماء المستخدمة
        
        for app_name, app_data in data.items():
            for model_name, model_data in app_data.items():
                if isinstance(model_data, list):  # إزالة شرط التحقق من أن القائمة غير فارغة
                    try:
                        # تنظيف اسم ورقة العمل لضمان التوافق مع Excel
                        raw_sheet_name = f"{app_name}_{model_name}"
                        sheet_name = clean_sheet_name(raw_sheet_name)
                        
                        # التأكد من عدم تكرار الاسم
                        original_name = sheet_name
                        counter = 1
                        while sheet_name in used_sheet_names:
                            counter_suffix = f"_{counter}"
                            max_length = 31 - len(counter_suffix)
                            if len(original_name) > max_length:
                                sheet_name = f"{original_name[:max_length]}{counter_suffix}"
                            else:
                                sheet_name = f"{original_name}{counter_suffix}"
                            counter += 1
                        
                        used_sheet_names.add(sheet_name)
                        sheet = workbook.create_sheet(title=sheet_name)
                        sheet_count += 1
                        
                        if len(model_data) > 0:
                            # كتابة الرؤوس
                            first_record = model_data[0]
                            if isinstance(first_record, dict) and 'fields' in first_record:
                                fields = first_record.get('fields', {})
                                
                                # فلترة الحقول المحذوفة
                                filtered_fields = {}
                                for field_name, field_value in fields.items():
                                    # تم إزالة فلترة is_service - الحقل لم يعد موجود
                                    filtered_fields[field_name] = field_value
                                
                                headers = ['ID'] + list(filtered_fields.keys())
                                for col, header in enumerate(headers, 1):
                                    # تنظيف اسم العمود
                                    clean_header = str(header) if header else f'Column_{col}'
                                    # إزالة الأحرف الخاصة من أسماء الأعمدة
                                    clean_header = ''.join(c if c.isalnum() or c in ' _-' else '_' for c in clean_header)
                                    if len(clean_header) > 255:  # حد Excel للأعمدة
                                        clean_header = clean_header[:252] + "..."
                                    sheet.cell(row=1, column=col, value=clean_header)
                                
                                # كتابة البيانات
                                for row_idx, record in enumerate(model_data, 2):
                                    if isinstance(record, dict):
                                        sheet.cell(row=row_idx, column=1, value=record.get('pk', ''))
                                        record_fields = record.get('fields', {})
                                        
                                        # فلترة الحقول المحذوفة قبل الكتابة
                                        filtered_record_fields = {}
                                        for field_name, field_value in record_fields.items():
                                            # تم إزالة فلترة is_service - الحقل لم يعد موجود
                                            filtered_record_fields[field_name] = field_value
                                        
                                        for col_idx, (field_name, field_value) in enumerate(filtered_record_fields.items(), 2):
                                            try:
                                                if field_value is None:
                                                    cell_value = ''
                                                elif isinstance(field_value, (str, int, float, bool)):
                                                    cell_value = str(field_value)
                                                else:
                                                    cell_value = str(field_value)
                                                
                                                # تحديد طول النص لتجنب مشاكل Excel
                                                if len(cell_value) > 32767:
                                                    cell_value = cell_value[:32760] + "..."
                                                    
                                                # تجنب الأحرف الخاصة التي قد تؤثر على Excel
                                                if cell_value and any(ord(char) < 32 for char in cell_value if char != '\t' and char != '\n' and char != '\r'):
                                                    cell_value = ''.join(char if ord(char) >= 32 or char in '\t\n\r' else '?' for char in cell_value)
                                                    
                                                sheet.cell(row=row_idx, column=col_idx, value=cell_value)
                                            except Exception as cell_error:
                                                logger.warning(f"خطأ في كتابة خلية {field_name}: {str(cell_error)}")
                                                sheet.cell(row=row_idx, column=col_idx, value='Error')
                        else:
                            # إضافة رأس أساسي للجداول الفارغة
                            sheet.cell(row=1, column=1, value='ID')
                            sheet.cell(row=1, column=2, value='Empty Table')
                            
                        logger.debug(f"تم إنشاء ورقة العمل: {sheet_name} مع {len(model_data)} سجل")
                    
                    except Exception as e:
                        logger.warning(f"خطأ في إنشاء ورقة العمل {app_name}_{model_name}: {str(e)}")
                        # تسجيل الخطأ في audit log إذا كان متاحاً
                        try:
                            from core.models import AuditLog
                            AuditLog.objects.create(
                                user=None,  # سيتم تعيينه لاحقاً بواسطة المستخدم الذي أنشأ النسخة
                                action='backup_xlsx_sheet_error',
                                details=f'خطأ في إنشاء ورقة عمل {app_name}_{model_name}: {str(e)}'
                            )
                        except Exception:
                            pass
                        continue
        
        # حفظ الملف
        workbook.save(filepath)
        logger.info(f"تم حفظ النسخة الاحتياطية XLSX بنجاح: {filepath} - تم إنشاء {sheet_count} ورقة عمل")
        
    except Exception as e:
        logger.error(f"خطأ في حفظ النسخة الاحتياطية كـ XLSX: {str(e)}")
        # تسجيل الخطأ الرئيسي في audit log
        try:
            from core.models import AuditLog
            AuditLog.objects.create(
                user=None,  # سيتم تعيينه لاحقاً بواسطة المستخدم الذي أنشأ النسخة
                action='backup_xlsx_save_error',
                details=f'خطأ كبير في حفظ ملف XLSX: {str(e)}'
            )
        except Exception:
            pass
        raise e


def load_backup_from_xlsx(file_obj, user=None):
    """تحويل ملف Excel إلى تنسيق JSON للاستعادة مع مزيد من التحمّل"""
    try:
        from openpyxl import load_workbook
        from django.apps import apps as django_apps
        
        logger.info("بدء قراءة ملف Excel للاستعادة")
        workbook = load_workbook(file_obj)
        
        # قراءة معلومات النسخة الاحتياطية من ورقة "Backup Info"
        backup_data = {
            'metadata': {},
            'data': {}
        }
        
        info_sheet = None
        if "Backup Info" in workbook.sheetnames:
            info_sheet = workbook["Backup Info"]
            
            # قراءة المعلومات الأساسية
            for row in info_sheet.iter_rows(min_row=1, max_row=5, values_only=True):
                if len(row) >= 2 and row[0] and row[1]:
                    if row[0] == 'Backup Name':
                        backup_data['metadata']['backup_name'] = str(row[1])
                    elif row[0] == 'Created At':
                        backup_data['metadata']['created_at'] = str(row[1])
                    elif row[0] == 'Created By':
                        backup_data['metadata']['created_by'] = str(row[1])
                    elif row[0] == 'Total Tables':
                        backup_data['metadata']['total_tables'] = int(row[1]) if row[1] else 0
                    elif row[0] == 'Total Records':
                        backup_data['metadata']['total_records'] = int(row[1]) if row[1] else 0
        
        # تجهيز قائمة أسماء التطبيقات المتاحة للمطابقة الذكية
        available_apps = {cfg.name for cfg in django_apps.get_app_configs()}
        
        # قراءة البيانات من باقي أوراق العمل
        for sheet_name in workbook.sheetnames:
            if sheet_name == "Backup Info":
                continue
                
            sheet = workbook[sheet_name]
            
            # تحليل اسم ورقة العمل للحصول على app_name و model_name بطريقة متحمّلة
            resolved_app = None
            resolved_model = None
            raw = str(sheet_name)
            parts = raw.split('_')
            # جرّب جميع نقاط التقسيم المحتملة حتى تجد نموذجاً معروفاً
            for i in range(1, len(parts)):
                cand_app = '_'.join(parts[:i])
                cand_model = '_'.join(parts[i:])
                # إزالة اللاحقة الرقمية المحتملة التي تمت إضافتها لتفادي التكرار
                cand_model = cand_model.rstrip('_0123456789')
                # تحقّق من توافق اسم التطبيق
                if cand_app in available_apps:
                    try:
                        # apps.get_model يتوقع app_label.model_name (model_name يمكن أن يكون lower)
                        mdl = django_apps.get_model(f"{cand_app}.{cand_model.lower()}")
                        if mdl is not None:
                            resolved_app = cand_app
                            resolved_model = cand_model
                            break
                    except Exception:
                        continue
            if not resolved_app or not resolved_model:
                # fallback: استخدم أول جزء كتطبيق والباقي كنموذج بعد إزالة اللاحقة الرقمية
                resolved_app = parts[0]
                resolved_model = '_'.join(parts[1:]).rstrip('_0123456789') or 'default'
            app_name = resolved_app
            model_name = resolved_model
            
            # سجّل محاولة التصحيح إذا كان اسم الورقة غامضاً
            if AUDIT_AVAILABLE and user and raw != f"{app_name}_{model_name}":
                try:
                    AuditLog.objects.create(
                        user=user,
                        action='backup_restore_xlsx_sheet_resolved',
                        details=f'تم تحليل اسم الورقة "{raw}" إلى التطبيق "{app_name}" والنموذج "{model_name}"'
                    )
                except Exception:
                    pass
            
            # التأكد من وجود التطبيق في البيانات
            if app_name not in backup_data['data']:
                backup_data['data'][app_name] = {}
            
            # قراءة البيانات من الورقة
            rows = list(sheet.iter_rows(values_only=True))
            if len(rows) < 1:
                backup_data['data'][app_name][model_name] = []
                continue
            
            # الصف الأول يحتوي على أسماء الأعمدة
            headers = [str(h) if h else f'col_{i}' for i, h in enumerate(rows[0])]
            
            # تحويل البيانات إلى تنسيق Django
            model_data = []
            for row_data in rows[1:]:  # تجاهل صف الرؤوس
                if not any(cell for cell in row_data):  # تجاهل الصفوف الفارغة
                    continue
                
                try:
                    # أول عمود هو ID
                    record_id = row_data[0] if len(row_data) > 0 and row_data[0] is not None else None
                    # Excel قد يحوّل الأرقام إلى float
                    if isinstance(record_id, float):
                        record_id = int(record_id) if float(record_id).is_integer() else record_id
                    
                    # باقي الأعمدة هي الحقول
                    fields = {}
                    for i, (header, value) in enumerate(zip(headers[1:], row_data[1:]), 1):
                        if value is not None:
                            # تحويل القيم حسب النوع
                            if isinstance(value, (int, float, bool)):
                                fields[header] = value
                            elif isinstance(value, str):
                                # محاولة تحويل النص إلى رقم أو boolean إذا أمكن
                                try:
                                    v = value.strip()
                                    # حاول قراءة JSON للقوائم/القواميس (مثل قيم ManyToMany المحفوظة كسلسلة)
                                    if (v.startswith('[') and v.endswith(']')) or (v.startswith('{') and v.endswith('}')):
                                        try:
                                            parsed = json.loads(v)
                                            fields[header] = parsed
                                            continue
                                        except Exception:
                                            pass
                                    # قائمة مفصولة بفواصل للأرقام: 1,2,3
                                    if ',' in v:
                                        parts_vals = [p.strip() for p in v.split(',') if p.strip()]
                                        if parts_vals and all(p.replace('.', '', 1).isdigit() for p in parts_vals):
                                            # حوّل إلى أعداد صحيحة عندما ممكن
                                            as_numbers = [int(p) if p.isdigit() else float(p) for p in parts_vals]
                                            fields[header] = as_numbers
                                            continue
                                    if v.lower() in ['true', 'false']:
                                        fields[header] = v.lower() == 'true'
                                    elif v.isdigit():
                                        fields[header] = int(v)
                                    elif v.replace('.', '', 1).isdigit():
                                        fields[header] = float(v)
                                    else:
                                        fields[header] = value
                                except:
                                    fields[header] = value
                            else:
                                fields[header] = str(value) if value is not None else None
                        else:
                            fields[header] = None
                    
                    # إنشاء سجل بتنسيق Django
                    record = {
                        'pk': record_id,
                        'model': f"{app_name}.{model_name.lower()}",
                        'fields': fields
                    }
                    model_data.append(record)
                    
                except Exception as row_error:
                    logger.warning(f"خطأ في قراءة صف في ورقة {sheet_name}: {str(row_error)}")
                    continue
            
            backup_data['data'][app_name][model_name] = model_data
            logger.debug(f"تم قراءة {len(model_data)} سجل من ورقة {sheet_name}")
        
        logger.info(f"تم تحويل ملف Excel بنجاح - {len(backup_data['data'])} تطبيق")
        return backup_data
        
    except Exception as e:
        logger.error(f"خطأ في قراءة ملف Excel: {str(e)}")
        raise Exception(f"خطأ في قراءة ملف Excel: {str(e)}")


def convert_field_value(field, value):
    """تحويل قيمة الحقل إلى النوع الصحيح"""
    if value is None or value == '':
        return value
    
    try:
        field_type = field.get_internal_type()
        
        if field_type in ['DecimalField']:
            if isinstance(value, str):
                return Decimal(value)
            return Decimal(str(value))
        elif field_type in ['IntegerField', 'BigIntegerField', 'SmallIntegerField', 'PositiveIntegerField']:
            if isinstance(value, str):
                return int(float(value)) if '.' in value else int(value)
            return int(value)
        elif field_type in ['FloatField']:
            if isinstance(value, str):
                return float(value)
            return float(value)
        elif field_type in ['BooleanField']:
            if isinstance(value, str):
                return value.lower() in ('true', '1', 'yes', 'on')
            return bool(value)
        elif field_type in ['DateTimeField']:
            if isinstance(value, str):
                from django.utils.dateparse import parse_datetime
                return parse_datetime(value)
            return value
        elif field_type in ['DateField']:
            if isinstance(value, str):
                from django.utils.dateparse import parse_date
                return parse_date(value)
            return value
        elif field_type in ['TimeField']:
            if isinstance(value, str):
                from django.utils.dateparse import parse_time
                return parse_time(value)
            return value
        else:
            return value
    except Exception:
        # في حالة فشل التحويل، أعد القيمة الأصلية
        return value


def perform_backup_restore(backup_data, clear_data=False, user=None):
    """تنفيذ عملية الاستعادة الفعلية"""
    try:
        logger.info("بدء تنفيذ عملية الاستعادة")
        
        # تسجيل بداية العملية في سجل الأنشطة
        log_audit(user, 'create', _('بدء عملية استعادة النسخة الاحتياطية'))

        # تهيئة تتبع التقدم
        flat_tables = []
        total_records_expected = 0
        if isinstance(backup_data, dict) and 'data' in backup_data:
            for app_name, app_data in backup_data['data'].items():
                for model_name, model_records in app_data.items():
                    if isinstance(model_records, list):
                        rec_count = len(model_records)
                        total_records_expected += rec_count
                        flat_tables.append({
                            'app_name': app_name,
                            'model_name': model_name,
                            'display_name': f"{app_name}.{model_name}",
                            'record_count': rec_count,
                            'status': 'pending',
                            'progress': 0,
                            'actual_records': 0,
                            'error': None
                        })

        # تسجيل إحصائيات العملية
        log_audit(user, 'view', _('تحليل النسخة الاحتياطية - {} جدول بإجمالي {} سجل').format(len(flat_tables), total_records_expected))

        progress_data = get_restore_progress_data()
        progress_data.update({
            'is_running': True,
            'status': 'starting',
            'error': None,
            'percentage': 0,
            'current_table': 'بدء عملية الاستعادة...',
            'processed_tables': 0,
            'total_tables': len(flat_tables),
            'processed_records': 0,
            'total_records': total_records_expected,
            'estimated_time': 'جاري الحساب...',
            'tables_status': flat_tables
        })
        set_restore_progress_data(progress_data)
        
        # مسح البيانات الموجودة إذا طُلب ذلك
        if clear_data:
            logger.info("مسح البيانات الموجودة...")
            
            # تجاهل التطبيقات الأساسية للنظام (contenttypes, auth, admin, sessions)
            skip_apps = {'contenttypes', 'auth', 'admin', 'sessions'}
            
            # بناء خريطة التبعية بين النماذج
            dep_map = {}
            model_map = {}
            for app_config in apps.get_app_configs():
                if app_config.name in skip_apps:
                    continue
                    
                for model in app_config.get_models():
                    # تجاهل النماذج التي لا تنشئ جداول
                    if not model._meta.managed:
                        continue
                        
                    label = f"{app_config.name}.{model._meta.model_name}"
                    dep_map[label] = set()
                    model_map[label] = model

            logger.info(f"تم العثور على {len(model_map)} نموذج قابل للمسح")
            
            # ملء خريطة التبعيات
            for label, model in list(model_map.items()):
                for field in model._meta.get_fields():
                    try:
                        if field.is_relation and (field.many_to_one or field.one_to_one) and field.related_model is not None:
                            rel = field.related_model
                            rel_label = f"{rel._meta.app_label}.{rel._meta.model_name}"
                            if rel_label in dep_map:
                                dep_map[rel_label].add(label)
                    except Exception:
                        continue

            # حساب ترتيب الحذف بحيث تُحذف التبعيات أولاً (post-order traversal)
            visited = set()
            delete_order = []
            def dfs(label):
                if label in visited:
                    return
                visited.add(label)
                for dep in dep_map.get(label, set()):
                    dfs(dep)
                delete_order.append(label)

            for label in list(model_map.keys()):
                dfs(label)
            
            logger.info(f"تم حساب ترتيب الحذف: {len(delete_order)} نموذج")
            
            # تنفيذ الحذف داخل معاملة وبترتيب آمن
            deleted_stats = []
            failed_deletions = []
            total_deleted_records = 0
            
            try:
                with transaction.atomic():
                    for i, label in enumerate(delete_order):
                        model = model_map.get(label)
                        if model is None:
                            continue
                            
                        try:
                            # معالجة خاصة لنموذج User
                            UserModel = None
                            try:
                                from django.contrib.auth import get_user_model
                                UserModel = get_user_model()
                            except Exception:
                                UserModel = None

                            if UserModel is not None and getattr(model, '__name__', '').lower() == getattr(UserModel, '__name__', '').lower():
                                # إنشاء مستخدم احتياطي إذا لم يكن موجوداً
                                fallback_username = '__deleted_user__'
                                fallback = UserModel.objects.filter(username=fallback_username).first()
                                if not fallback:
                                    fallback = UserModel.objects.create(username=fallback_username, is_active=False)

                                # إعادة توجيه مراجعات المستخدمين المراد حذفها
                                try:
                                    user_ids = list(model.objects.exclude(pk=fallback.pk).values_list('pk', flat=True))
                                    from core.models import AuditLog as _AuditLog
                                    if user_ids:
                                        _AuditLog.objects.filter(user_id__in=user_ids).update(user_id=fallback.pk)
                                except Exception as reassign_err:
                                    logger.warning(f"فشل في إعادة توجيه مراجعات المستخدمين: {reassign_err}")

                                # حذف جميع المستخدمين عدا المستخدم الاحتياطي
                                qs = model.objects.exclude(pk=fallback.pk)
                                count = qs.count()
                                qs.delete()
                                deleted_stats.append({'table': label, 'deleted': count})
                                total_deleted_records += count
                                logger.debug(f"تم مسح {count} مستخدم من {label} ({i+1}/{len(delete_order)})")
                                continue

                            # الحذف العادي للنماذج الأخرى
                            count = model.objects.all().count()
                            if count > 0:  # فقط إذا كان هناك بيانات
                                model.objects.all().delete()
                                deleted_stats.append({'table': label, 'deleted': count})
                                total_deleted_records += count
                                logger.debug(f"تم مسح {count} سجل من {label} ({i+1}/{len(delete_order)})")
                            
                        except ProtectedError as p_err:
                            # تسجيل النماذج التي فشل حذفها بسبب علاقات محمية
                            failed_deletions.append({
                                'table': label,
                                'error': 'ProtectedError',
                                'details': str(p_err)
                            })
                            logger.warning(f"تعذر مسح {label} بسبب علاقات محمية: {str(p_err)}")
                            continue
                            
                        except Exception as del_exc:
                            # تسجيل النماذج التي فشل حذفها لأسباب أخرى
                            failed_deletions.append({
                                'table': label,
                                'error': str(type(del_exc).__name__),
                                'details': str(del_exc)
                            })
                            logger.warning(f"تعذر مسح {label}: {str(del_exc)}")
                            continue
                    
                # تسجيل نتائج مسح البيانات
                logger.info(f"تم مسح البيانات بنجاح - إجمالي السجلات الممسوحة: {total_deleted_records}")
                log_audit(user, 'delete', f'تم مسح البيانات الموجودة قبل الاستعادة - تم مسح {total_deleted_records} سجل من {len(deleted_stats)} جدول')
                
                if failed_deletions:
                    failed_count = len(failed_deletions)
                    log_audit(user, 'warning', f'فشل مسح {failed_count} جدول بسبب علاقات محمية أو أخطاء أخرى')
                    logger.warning(f"فشل مسح {failed_count} جدول: {[f['table'] for f in failed_deletions]}")
                    
            except Exception as tx_error:
                logger.error(f"فشل في مسح البيانات داخل المعاملة: {str(tx_error)}")
                log_audit(user, 'error', f'فشل في مسح البيانات قبل الاستعادة: {str(tx_error)}')
                # لا نرمي استثناء هنا للسماح بمتابعة الاستعادة
        # استعادة البيانات
        if 'data' in backup_data:
            total_records = 0
            restored_count = 0
            processed_tables = 0
            processed_records = 0
            table_index = -1
            start_time = time.time()
            errors = []
            for app_name, app_data in backup_data['data'].items():
                for model_name, model_records in app_data.items():
                    if isinstance(model_records, list):
                        table_index += 1
                        expected_in_table = len(model_records)
                        # تحديث حالة الجدول الجاري
                        pd = get_restore_progress_data()
                        ts = pd.get('tables_status', [])
                        if table_index < len(ts):
                            ts[table_index]['status'] = 'processing'
                            ts[table_index]['progress'] = 0
                        pd.update({
                            'status': 'processing',
                            'current_table': f'استعادة {app_name}.{model_name}...',
                            'tables_status': ts
                        })
                        set_restore_progress_data(pd)

                        processed_in_table = 0
                        for record in model_records:
                            try:
                                # تصحيح أسماء التطبيقات والنماذج القديمة
                                original_app_name = app_name
                                original_model_name = model_name
                                
                                if app_name == 'revenues':
                                    app_name = 'revenues_expenses'
                                elif app_name == 'assets':
                                    app_name = 'assets_liabilities'
                                elif app_name == 'expenses':
                                    app_name = 'revenues_expenses'
                                elif app_name == 'liabilities':
                                    app_name = 'assets_liabilities'
                                
                                model_label = f"{app_name}.{model_name.lower()}"
                                
                                # معالجة خاصة لـ AuditLog - تصحيح الحقول القديمة
                                if model_label == 'core.auditlog':
                                    fields = record.get('fields', {})
                                    if 'action' in fields and 'action_type' not in fields:
                                        fields['action_type'] = fields.pop('action')
                                    if 'details' in fields and 'description' not in fields:
                                        fields['description'] = fields.pop('details')
                                
                                model = apps.get_model(model_label)
                                fields = record.get('fields', {})
                                # تحويلات توافقية لحقول قديمة قبل إنشاء الكائن
                                try:
                                    # المنتجات: تحويل is_service القديم إلى product_type الجديد
                                    if model_label == 'products.product' and 'is_service' in fields and 'product_type' not in fields:
                                        is_service_val = fields.get('is_service')
                                        fields['product_type'] = 'service' if bool(is_service_val) else 'physical'
                                        if AUDIT_AVAILABLE and user:
                                            try:
                                                log_audit(user, 'import', 'تم تحويل الحقل القديم "is_service" إلى "product_type" أثناء الاستعادة')
                                            except Exception:
                                                pass
                                    # حركات المخزون: تحويل total_amount القديم إلى total_cost
                                    if model_label == 'inventory.inventorymovement' and 'total_amount' in fields and 'total_cost' not in fields:
                                        fields['total_cost'] = fields.get('total_amount')
                                        if AUDIT_AVAILABLE and user:
                                            try:
                                                log_audit(user, 'import', 'تم تحويل الحقل القديم "total_amount" إلى "total_cost" في حركة المخزون أثناء الاستعادة')
                                            except Exception:
                                                pass
                                except Exception:
                                    # تجاهل أي خطأ غير متوقع في التحويلات التوافقية
                                    pass
                                pk = record.get('pk', None)
                                obj = model()
                                # معالجة الحقول الإلزامية الفارغة وحقول العلاقات
                                m2m_fields = {}
                                model_field_names = [f.name for f in model._meta.get_fields()]
                                for field in model._meta.get_fields():
                                    fname = field.name
                                    # اعتبر الحقل إلزامياً إذا كان null=False فقط (blank خاص بالنماذج وليس قاعدة البيانات)
                                    is_required = (getattr(field, 'null', True) is False) and not getattr(field, 'auto_created', False) and fname != 'id'
                                    # معالجة الحقول الخارجية ForeignKey و OneToOne
                                    if field.is_relation and (field.many_to_one or field.one_to_one):
                                        rel_model = field.related_model
                                        rel_value = fields.get(fname)
                                        if rel_value not in [None, '']:
                                            try:
                                                rel_obj = rel_model.objects.filter(pk=rel_value).first()
                                                setattr(obj, fname, rel_obj)
                                                if rel_obj is None:
                                                    # إذا كان الحقل FK لمستخدم ومطلوب وقيمة المعرف غير موجودة، عيّن المستخدم الحالي
                                                    try:
                                                        from django.contrib.auth import get_user_model
                                                        UserModel = get_user_model()
                                                    except Exception:
                                                        UserModel = None
                                                    if is_required and UserModel and user and isinstance(user, UserModel) and (rel_model == UserModel or issubclass(rel_model, UserModel)):
                                                        setattr(obj, fname, user)
                                                        if AUDIT_AVAILABLE and user:
                                                            log_audit(user, 'import', f'تم تعيين المستخدم الحالي كقيمة افتراضية للحقل "{fname}" (مرجع غير موجود) في النموذج {model_label}')
                                                    elif AUDIT_AVAILABLE and user:
                                                        AuditLog.objects.create(
                                                            user=user,
                                                            action='backup_restore_fk_missing',
                                                            details=f'لم يتم العثور على الكائن المرتبط للحقل "{fname}" في النموذج {model_label} أثناء الاستعادة. تم تعيين None.'
                                                        )
                                            except Exception as fk_error:
                                                setattr(obj, fname, None)
                                                if AUDIT_AVAILABLE and user:
                                                    AuditLog.objects.create(
                                                        user=user,
                                                        action='backup_restore_fk_error',
                                                        details=f'خطأ في جلب الكائن المرتبط للحقل "{fname}" في النموذج {model_label}: {str(fk_error)}'
                                                    )
                                        else:
                                            # إذا كان الحقل FK لمستخدم ومطلوب وقيمته مفقودة، عيّن المستخدم الحالي كمقدار افتراضي
                                            try:
                                                from django.contrib.auth import get_user_model
                                                UserModel = get_user_model()
                                            except Exception:
                                                UserModel = None
                                            if is_required and UserModel and user and isinstance(user, UserModel) and (rel_model == UserModel or issubclass(rel_model, UserModel)):
                                                try:
                                                    setattr(obj, fname, user)
                                                    if AUDIT_AVAILABLE and user:
                                                        log_audit(user, 'import', f'تم تعيين المستخدم الحالي كقيمة افتراضية للحقل "{fname}" المطلوب في النموذج {model_label}')
                                                except Exception:
                                                    setattr(obj, fname, None)
                                            else:
                                                setattr(obj, fname, None)
                                    # معالجة الحقول ManyToMany
                                    elif field.many_to_many:
                                        rel_model = field.related_model
                                        rel_values = fields.get(fname)
                                        if rel_values:
                                            m2m_fields[fname] = rel_values
                                    # الحقول الإلزامية الفارغة
                                    elif is_required and (fname not in fields or fields[fname] in [None, '']):
                                        if getattr(field, 'default', models.NOT_PROVIDED) is not models.NOT_PROVIDED:
                                            try:
                                                setattr(obj, fname, field.get_default())
                                            except Exception:
                                                setattr(obj, fname, getattr(field, 'default', None))
                                        elif getattr(field, 'get_internal_type', lambda: None)() in ['CharField', 'TextField']:
                                            setattr(obj, fname, '')
                                        elif getattr(field, 'get_internal_type', lambda: None)() == 'BooleanField':
                                            setattr(obj, fname, False)
                                        elif getattr(field, 'get_internal_type', lambda: None)() in ['IntegerField', 'BigIntegerField', 'SmallIntegerField', 'PositiveIntegerField']:
                                            setattr(obj, fname, 0)
                                        elif getattr(field, 'get_internal_type', lambda: None)() in ['FloatField']:
                                            setattr(obj, fname, 0.0)
                                        elif getattr(field, 'get_internal_type', lambda: None)() in ['DecimalField']:
                                            setattr(obj, fname, Decimal('0'))
                                        elif getattr(field, 'get_internal_type', lambda: None)() == 'DateTimeField':
                                            from django.utils import timezone
                                            setattr(obj, fname, timezone.now())
                                        elif getattr(field, 'get_internal_type', lambda: None)() == 'DateField':
                                            from django.utils import timezone
                                            setattr(obj, fname, timezone.now().date())
                                        else:
                                            setattr(obj, fname, None)
                                        if AUDIT_AVAILABLE and user:
                                            try:
                                                AuditLog.objects.create(
                                                    user=user,
                                                    action='backup_restore_field_fix',
                                                    details=f'تم تعيين قيمة افتراضية للحقل الإلزامي "{fname}" في النموذج {model_label} أثناء الاستعادة.'
                                                )
                                            except Exception:
                                                pass
                                    # الحقول العادية
                                    elif fname in fields:
                                        # إذا كانت القيمة None وحقل غير قابل لـ null فقم بضبط قيمة افتراضية آمنة
                                        val = fields[fname]
                                        if (val is None) and (getattr(field, 'null', True) is False) and not field.is_relation and not field.many_to_many:
                                            internal = getattr(field, 'get_internal_type', lambda: None)()
                                            if getattr(field, 'default', models.NOT_PROVIDED) is not models.NOT_PROVIDED:
                                                try:
                                                    safe_val = field.get_default()
                                                except Exception:
                                                    safe_val = getattr(field, 'default', None)
                                            elif internal in ['CharField', 'TextField']:
                                                safe_val = ''
                                            elif internal == 'BooleanField':
                                                safe_val = False
                                            elif internal in ['IntegerField', 'BigIntegerField', 'SmallIntegerField', 'PositiveIntegerField']:
                                                safe_val = 0
                                            elif internal == 'FloatField':
                                                safe_val = 0.0
                                            elif internal == 'DecimalField':
                                                safe_val = Decimal('0')
                                            elif internal == 'DateTimeField':
                                                from django.utils import timezone
                                                safe_val = timezone.now()
                                            elif internal == 'DateField':
                                                from django.utils import timezone
                                                safe_val = timezone.now().date()
                                            else:
                                                safe_val = ''
                                            setattr(obj, fname, safe_val)
                                            if AUDIT_AVAILABLE and user:
                                                try:
                                                    log_audit(user, 'update', f'تم استبدال قيمة None بقيمة افتراضية للحقل الإلزامي "{fname}" في النموذج {model_label}.')
                                                except Exception:
                                                    pass
                                        else:
                                            # تحويل القيمة إلى النوع الصحيح قبل التعيين
                                            converted_val = convert_field_value(field, val)
                                            setattr(obj, fname, converted_val)
                                # تجاهل الحقول غير الموجودة في النموذج
                                for field_name in fields.keys():
                                    if field_name not in model_field_names:
                                        if AUDIT_AVAILABLE and user:
                                            try:
                                                log_audit(user, 'view', f'تم تجاهل الحقل غير الموجود "{field_name}" في النموذج {model_label} أثناء الاستعادة.')
                                            except Exception:
                                                pass
                                if pk:
                                    obj.pk = pk
                                try:
                                    obj.save()
                                except Exception as save_error:
                                    # معالجة أخطاء التكرار والقيود
                                    error_msg = str(save_error).lower()
                                    if 'duplicate key' in error_msg or 'unique constraint' in error_msg:
                                        # في حالة التكرار، حاول التحديث بدلاً من الإدراج
                                        try:
                                            if pk:
                                                existing_obj = model.objects.filter(pk=pk).first()
                                                if existing_obj:
                                                    # تحديث الكائن الموجود
                                                    for fname, val in fields.items():
                                                        if hasattr(existing_obj, fname) and fname != 'id':
                                                            setattr(existing_obj, fname, val)
                                                    existing_obj.save()
                                                    if AUDIT_AVAILABLE and user:
                                                        log_audit(user, 'update', f'تم تحديث سجل موجود في {model_label} بدلاً من إنشاء مكرر')
                                                else:
                                                    # إذا لم يوجد بالـ PK، جرب بدون PK
                                                    obj.pk = None
                                                    obj.save()
                                            else:
                                                # جرب حفظ بدون PK
                                                obj.pk = None
                                                obj.save()
                                        except Exception as retry_error:
                                            # إذا فشل كل شيء، تجاهل هذا السجل
                                            logger.warning(f"تعذر استعادة سجل {model_label} بسبب تكرار: {str(retry_error)}")
                                            if AUDIT_AVAILABLE and user:
                                                log_audit(user, 'error', f'تم تجاهل سجل مكرر في {model_label}: {str(retry_error)}')
                                            total_records += 1
                                            continue
                                    else:
                                        # خطأ آخر غير التكرار
                                        raise save_error
                                # تعيين الحقول ManyToMany بعد الحفظ
                                for m2m_name, m2m_values in m2m_fields.items():
                                    try:
                                        # إذا كانت القيمة نصية، حاول تحويلها لقائمة أرقام
                                        if isinstance(m2m_values, str):
                                            v = m2m_values.strip()
                                            try:
                                                if (v.startswith('[') and v.endswith(']')):
                                                    m2m_values = json.loads(v)
                                                else:
                                                    tokens = [p.strip() for p in v.split(',') if p.strip()]
                                                    if tokens and all(t.replace('.', '', 1).isdigit() for t in tokens):
                                                        m2m_values = [int(t) if t.isdigit() else float(t) for t in tokens]
                                            except Exception:
                                                pass
                                        # تأكد أن العناصر أعداد صحيحة قدر الإمكان
                                        if isinstance(m2m_values, list):
                                            norm_values = []
                                            for vv in m2m_values:
                                                if isinstance(vv, float) and float(vv).is_integer():
                                                    norm_values.append(int(vv))
                                                elif isinstance(vv, (int,)):
                                                    norm_values.append(vv)
                                                elif isinstance(vv, str) and vv.isdigit():
                                                    norm_values.append(int(vv))
                                                else:
                                                    # اترك القيمة كما هي إذا لم يمكن تحويلها
                                                    norm_values.append(vv)
                                            m2m_values = norm_values
                                        m2m_manager = getattr(obj, m2m_name)
                                        m2m_manager.set(m2m_values)
                                    except Exception as m2m_error:
                                        if AUDIT_AVAILABLE and user:
                                            log_audit(user, 'error', f'خطأ في تعيين الحقل ManyToMany "{m2m_name}" في النموذج {model_label}: {str(m2m_error)}')
                                restored_count += 1
                                processed_in_table += 1
                                processed_records += 1
                                # تحديث تقدم الجدول والتقدم العام
                                pd = get_restore_progress_data()
                                ts = pd.get('tables_status', [])
                                if table_index < len(ts) and expected_in_table > 0:
                                    table_progress = int((processed_in_table / expected_in_table) * 100)
                                    ts[table_index]['progress'] = table_progress
                                    ts[table_index]['actual_records'] = processed_in_table
                                # تقدير الوقت والكنترول العام
                                elapsed = time.time() - start_time
                                overall_percentage = 0
                                # استخدم total_records_expected المحسوب في البداية بدلاً من total_records المتغير
                                if total_records_expected > 0:
                                    overall_percentage = int((processed_records / total_records_expected) * 100)
                                
                                pd.update({
                                    'processed_tables': processed_tables,
                                    'processed_records': processed_records,
                                    'percentage': overall_percentage,
                                    'tables_status': ts
                                })
                                set_restore_progress_data(pd)
                            except Exception as record_error:
                                logger.warning(f"فشل في استعادة سجل في {app_name}.{model_name}: {str(record_error)}")
                                errors.append(f"فشل في استعادة سجل في {app_name}.{model_name}: {str(record_error)}")
                                continue
            logger.info(f"تم استعادة {restored_count} من {total_records} سجل")
            if AUDIT_AVAILABLE and user:
                try:
                    log_audit(user, 'create', f'تم استعادة {restored_count} سجل من أصل {total_records}. عدد الأخطاء: {len(errors)}')
                    if errors:
                        log_audit(user, 'error', '\n'.join(errors))
                except Exception:
                    pass
            # لا نفشل العملية بالكامل عند وجود أخطاء جزئية؛ تم تسجيلها في سجل الأنشطة بالفعل
            # يمكن لاحقاً عرض تحذير في الواجهة إذا لزم، دون رمي استثناء هنا
            logger.info("تم إتمام عملية الاستعادة بنجاح")
            
            # تسجيل نهاية العملية بنجاح في سجل الأنشطة
            log_audit(user, 'create', _('تم إكمال عملية الاستعادة بنجاح - {} جدول، {} سجل مستعاد').format(processed_tables, restored_count))
            
            # إنهاء حالة التقدم مع ضمان 100%
            pd = get_restore_progress_data()
            # تأكد أن جميع الجداول مكتملة
            ts = pd.get('tables_status', [])
            for table_status in ts:
                table_status['status'] = 'completed'
                table_status['progress'] = 100
            pd.update({
                'status': 'completed',
                'is_running': False,
                'percentage': 100,
                'processed_records': total_records_expected,  # تأكد من المطابقة الكاملة
                'current_table': 'تم إتمام الاستعادة بنجاح! ✅',
                'estimated_time': 'اكتمل',
                'tables_status': ts
            })
            set_restore_progress_data(pd)
            # تنظيف كاش الاستعادة بعد 10 ثواني
            def cleanup_restore_cache():
                time.sleep(10)
                cache.delete('restore_progress')
                cache.delete('restore_last_update')
                cache.delete('restore_last_percentage')
            threading.Thread(target=cleanup_restore_cache, daemon=True).start()
        # إذا كانت النسخة تحتوي على ملفات وسائط، سجّل ذلك في سجل المراجعة لتوعية المسؤول
        try:
            if isinstance(backup_data, dict) and 'media_files' in backup_data and backup_data['media_files']:
                if AUDIT_AVAILABLE and user:
                    try:
                        log_audit(user, 'view', f'تحتوي النسخة على {len(backup_data["media_files"]) } ملف وسائط (system/*). يتطلب نقلها يدوياً إلى MEDIA_ROOT.')
                    except Exception:
                        pass
        except Exception:
            pass
        
        # إذا كانت النسخة تحتوي على ملفات ترجمة، سجّل ذلك في سجل المراجعة لتوعية المسؤول
        try:
            if isinstance(backup_data, dict) and 'locale_files' in backup_data and backup_data['locale_files']:
                if AUDIT_AVAILABLE and user:
                    try:
                        log_audit(user, 'view', f'تحتوي النسخة على {len(backup_data["locale_files"]) } ملف ترجمة. يتطلب نقلها يدوياً إلى مجلد locale.')
                    except Exception:
                        pass
        except Exception:
            pass
        return True
    except Exception as e:
        logger.error(f"خطأ في تنفيذ الاستعادة: {str(e)}")
        # تحديث حالة الخطأ
        pd = get_restore_progress_data()
        pd.update({
            'status': 'error',
            'is_running': False,
            'error': str(e),
            'current_table': f'خطأ: {str(e)}'
        })
        set_restore_progress_data(pd)
        if AUDIT_AVAILABLE and user:
            try:
                log_audit(user, 'error', f'خطأ في الاستعادة: {str(e)}')
            except Exception:
                pass
        raise e


@login_required
def create_backup(request):
    """إنشاء نسخة احتياطية مع تتبع التقدم وتسجيل الأنشطة"""
    
    logger.info(f"🎯 دخول create_backup: {request.method} - User: {request.user.username if request.user.is_authenticated else 'Anonymous'}")
    
    if request.method != 'POST':
        logger.warning(f"❌ طريقة طلب غير صحيحة: {request.method}")
        if AUDIT_AVAILABLE:
            try:
                AuditLog.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    action='backup_access_denied',
                    details='محاولة وصول غير صحيحة لإنشاء نسخة احتياطية'
                )
            except Exception:
                pass
        messages.error(request, _('طريقة طلب غير صحيحة'))
        return redirect('backup:backup_restore')
    
    progress_data = get_backup_progress_data()
    
    # التحقق من العمليات المعلقة
    if progress_data.get('is_running', False):
        import time
        current_time = time.time()
        last_update = cache.get('backup_last_update', current_time)
        
        # إذا مر أكثر من دقيقة واحدة بدون تحديث، قم بمسح العملية المعلقة تلقائياً
        if current_time - last_update > 60:  # دقيقة واحدة
            cache.delete('backup_progress')
            cache.delete('backup_last_update')
            
            log_audit(request.user, 'delete', f'تم مسح عملية النسخ الاحتياطي المعلقة تلقائياً - عمر العملية: {int(current_time - last_update)} ثانية')
            
            progress_data = get_backup_progress_data()  # إعادة جلب البيانات
        else:
            # فحص إضافي: التحقق من أن العملية تتقدم فعلاً
            current_percentage = progress_data.get('percentage', 0)
            last_percentage = cache.get('backup_last_percentage', 0)
            
            # إذا لم تتقدم العملية لمدة 30 ثانية، فهي معلقة
            if current_percentage == last_percentage and current_time - last_update > 30:
                cache.delete('backup_progress')
                cache.delete('backup_last_update')
                cache.delete('backup_last_percentage')
                
                log_audit(request.user, 'delete', f'تم مسح عملية النسخ الاحتياطي المتوقفة تلقائياً - توقفت عند {current_percentage}%')
                
                progress_data = get_backup_progress_data()  # إعادة جلب البيانات
            else:
                # تحديث آخر نسبة مئوية
                cache.set('backup_last_percentage', current_percentage, timeout=3600)
                
                # العملية ما زالت قيد التشغيل - تسجيل المحاولة
                log_audit(request.user, 'error', f'محاولة بدء نسخة احتياطية أثناء وجود عملية قيد التشغيل - نسبة الإنجاز: {current_percentage}%')
                
                messages.error(request, _('عملية نسخ احتياطي قيد التشغيل بالفعل'))
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'error': 'عملية نسخ احتياطي قيد التشغيل بالفعل'
                    })
                return redirect('backup:backup_restore')
    
    try:
        # الحصول على التنسيق المختار
        selected_format = (
            request.POST.get('format') or 
            request.POST.get('backupFormat') or 
            'json'
        ).strip().lower()
        
        # إنشاء اسم الملف حسب التنسيق
        timestamp = dt_module.now().strftime('%Y%m%d_%H%M%S')
        
        if selected_format == 'xlsx':
            filename = f'backup_{timestamp}.xlsx'
            format_name = 'XLSX'
        else:
            filename = f'backup_{timestamp}.json'
            format_name = 'JSON'
            selected_format = 'json'
            
        # تسجيل بداية عملية النسخ الاحتياطي
        log_audit(request.user, 'create', f'طلب إنشاء نسخة احتياطية بصيغة {format_name}: {filename}')
        
        # إنشاء مجلد النسخ الاحتياطية إذا لم يكن موجوداً
        backup_dir = os.path.join(settings.MEDIA_ROOT, 'backups')
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        filepath = os.path.join(backup_dir, filename)
        
        # بدء المهمة في خيط منفصل (مبسط)
        def start_backup():
            try:
                # إضافة تأخير بسيط
                import time
                time.sleep(0.5)
                
                # استدعاء مباشر بدون تعقيدات إضافية
                perform_backup_task(request.user, timestamp, filename, filepath, selected_format)
                
            except Exception as e:
                logger.error(f"❌ خطأ في النسخ الاحتياطي: {str(e)}")
                # تحديث الكاش بالخطأ
                try:
                    from django.core.cache import cache
                    progress_data = {
                        'is_running': False,
                        'status': 'error',
                        'error': str(e),
                        'percentage': 0,
                        'current_table': f'خطأ: {str(e)}'
                    }
                    cache.set('backup_progress', progress_data, timeout=3600)
                except:
                    pass
                
        # إنشاء وتشغيل الخيط
        thread = threading.Thread(target=start_backup)
        thread.daemon = True
        thread.start()
        
        logger.info(f"📝 تم بدء النسخ الاحتياطي: {filename}")
        
        # إرجاع JSON response للطلبات AJAX
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'filename': filename,
                'format': format_name,
                'message': f'تم بدء إنشاء النسخة الاحتياطية {format_name}: {filename}'
            })
        
        messages.success(request, _(f'تم بدء إنشاء النسخة الاحتياطية {format_name}: {filename}'))
        return redirect('backup:backup_restore')
        
    except Exception as e:
        error_msg = f"خطأ في إنشاء النسخة الاحتياطية: {str(e)}"
        logger.error(error_msg)
        
        if AUDIT_AVAILABLE:
            try:
                AuditLog.objects.create(
                    user=request.user,
                    action='backup_error_request',
                    details=error_msg
                )
            except Exception:
                pass
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': error_msg
            })
        
        messages.error(request, error_msg)
        return redirect('backup:backup_restore')


@login_required  
def download_backup(request, filename):
    """تحميل ملف النسخة الاحتياطية"""
    
    if not filename.endswith(('.json', '.xlsx')):
        raise Http404("نوع الملف غير مدعوم")
    
    backup_dir = os.path.join(settings.MEDIA_ROOT, 'backups')
    filepath = os.path.join(backup_dir, filename)
    
    if not os.path.exists(filepath):
        raise Http404("الملف غير موجود")
    
    if AUDIT_AVAILABLE:
        try:
            AuditLog.objects.create(
                user=request.user,
                action='backup_download',
                details=f'تحميل النسخة الاحتياطية: {filename}'
            )
        except Exception:
            pass
    
    content_type = 'application/json' if filename.endswith('.json') else 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    
    try:
        with open(filepath, 'rb') as f:
            response = HttpResponse(f.read(), content_type=content_type)
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
    except Exception as e:
        logger.error(f"خطأ في تحميل الملف {filename}: {str(e)}")
        raise Http404("حدث خطأ في تحميل الملف")


@login_required
def delete_backup(request, filename):
    """حذف ملف النسخة الاحتياطية"""
    
    if request.method != 'POST':
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': 'طريقة طلب غير صحيحة'
            })
        return redirect('backup:backup_restore')
    
    if not filename.endswith(('.json', '.xlsx')):
        error_msg = "نوع الملف غير مدعوم"
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': error_msg
            })
        
        messages.error(request, error_msg)
        return redirect('backup:backup_restore')
    
    backup_dir = os.path.join(settings.MEDIA_ROOT, 'backups')
    filepath = os.path.join(backup_dir, filename)
    
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            
            # تسجيل الحدث في سجل المراجعة
            log_audit(request.user, 'delete', f'حذف النسخة الاحتياطية: {filename}')
            
            success_msg = f"تم حذف النسخة الاحتياطية {filename} بنجاح"
            logger.info(f"✅ {success_msg} - المستخدم: {request.user.username}")
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': success_msg
                })
                
            messages.success(request, success_msg)
        else:
            error_msg = "الملف غير موجود"
            
            # تسجيل محاولة الحذف للملف غير الموجود
            log_audit(request.user, 'warning', f'محاولة حذف ملف غير موجود: {filename}')
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': error_msg
                })
                
            messages.error(request, error_msg)
            
    except Exception as e:
        error_msg = f"حدث خطأ في حذف الملف: {str(e)}"
        logger.error(f"❌ خطأ في حذف الملف {filename}: {str(e)}")
        
        # تسجيل الخطأ في سجل المراجعة
        log_audit(request.user, 'error', f'فشل حذف النسخة الاحتياطية: {filename} - خطأ: {str(e)}')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': error_msg
            })
        
        messages.error(request, error_msg)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': 'تم معالجة الطلب'
        })
    
    return redirect('backup:backup_restore')


@login_required
def restore_backup(request):
    """استعادة النسخة الاحتياطية"""
    
    if request.method != 'POST':
        messages.error(request, _("طريقة طلب غير صحيحة"))
        return redirect('backup:backup_restore')
    
    if not request.user.is_superuser:
        messages.error(request, _("غير مسموح لك بإجراء هذه العملية"))
        return redirect('backup:backup_restore')
    
    if 'backup_file' not in request.FILES and not request.POST.get('filename'):
        messages.error(request, _("يرجى اختيار ملف النسخة الاحتياطية"))
        return redirect('backup:backup_restore')
    
    # قبول عدة صيغ لتمرير قيمة clear_data من النموذج أو ال AJAX (مثال: 'on' من form submission، 'true' من AJAX)
    raw_clear = request.POST.get('clear_data')
    if raw_clear is None:
        clear_data = False
    else:
        try:
            clear_data = str(raw_clear).strip().lower() in ('true', '1', 'on', 'yes')
        except Exception:
            clear_data = False
    filename_from_list = request.POST.get('filename')
    backup_file = request.FILES.get('backup_file')
    
    try:
        if filename_from_list:
            # قراءة من ملف موجود في مجلد النسخ الاحتياطية
            backup_dir = os.path.join(settings.MEDIA_ROOT, 'backups')
            filepath = os.path.join(backup_dir, filename_from_list)
            if not os.path.exists(filepath):
                msg = _("الملف غير موجود")
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': msg})
                messages.error(request, msg)
                return redirect('backup:backup_restore')
            if filepath.endswith('.json'):
                with open(filepath, 'r', encoding='utf-8') as f:
                    backup_data = json.load(f)
            elif filepath.endswith('.xlsx'):
                with open(filepath, 'rb') as f:
                    backup_data = load_backup_from_xlsx(f, user=request.user)
            else:
                msg = _("نوع الملف غير مدعوم")
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': msg})
                messages.error(request, msg)
                return redirect('backup:backup_restore')
            input_name_for_audit = filename_from_list
        elif backup_file and backup_file.name.endswith('.json'):
            file_content = backup_file.read().decode('utf-8')
            backup_data = json.loads(file_content)
            input_name_for_audit = backup_file.name
        elif backup_file and backup_file.name.endswith('.xlsx'):
            # دعم استعادة ملفات Excel
            try:
                backup_data = load_backup_from_xlsx(backup_file, user=request.user)
                if AUDIT_AVAILABLE:
                    try:
                        AuditLog.objects.create(
                            user=request.user,
                            action='backup_restore_xlsx_parsed',
                            details=f'تم تحويل ملف Excel للاستعادة: {backup_file.name}'
                        )
                    except Exception:
                        pass
            except Exception as xlsx_error:
                logger.error(f"خطأ في قراءة ملف Excel: {str(xlsx_error)}")
                messages.error(request, _(f"خطأ في قراءة ملف Excel: {str(xlsx_error)}"))
                if AUDIT_AVAILABLE:
                    try:
                        AuditLog.objects.create(
                            user=request.user,
                            action='backup_restore_xlsx_error',
                            details=f'فشل تحويل ملف Excel: {backup_file.name} - {str(xlsx_error)}'
                        )
                    except Exception:
                        pass
                return redirect('backup:backup_restore')
            input_name_for_audit = backup_file.name
        else:
            messages.error(request, _("نوع الملف غير مدعوم"))
            return redirect('backup:backup_restore')
        
        if AUDIT_AVAILABLE:
            try:
                AuditLog.objects.create(
                    user=request.user,
                    action='backup_restore_start',
                    details=f'بدء استعادة النسخة الاحتياطية: {input_name_for_audit}'
                )
            except Exception:
                pass
        
        # تشغيل عملية الاستعادة في خيط منفصل وتحديث التقدم عبر الكاش
        def start_restore_task():
            try:
                perform_backup_restore(backup_data, clear_data, request.user)
                # عند النجاح، سجّل في السجل (تمت إضافة ذلك داخل perform_backup_restore أيضاً)
                if AUDIT_AVAILABLE:
                    try:
                        AuditLog.objects.create(
                            user=request.user,
                            action='backup_restore_complete',
                            details=f'تم إتمام استعادة النسخة الاحتياطية بنجاح: {input_name_for_audit}'
                        )
                    except Exception:
                        pass
            except Exception as restore_error:
                logger.error(f"خطأ في تنفيذ الاستعادة (خلفية): {str(restore_error)}")
                if AUDIT_AVAILABLE:
                    try:
                        AuditLog.objects.create(
                            user=request.user,
                            action='backup_restore_failed',
                            details=f'فشل في استعادة النسخة الاحتياطية: {input_name_for_audit} - {str(restore_error)}'
                        )
                    except Exception:
                        pass

        thread = threading.Thread(target=start_restore_task, daemon=True)
        thread.start()

        # الاستجابة حسب نوع الطلب
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': _('تم بدء عملية الاستعادة في الخلفية')
            })
        else:
            messages.info(request, _("تم بدء عملية الاستعادة في الخلفية، يمكن متابعة التقدم على هذه الصفحة"))
            return redirect('backup:backup_restore')
        
    except json.JSONDecodeError:
        messages.error(request, _("ملف JSON غير صحيح"))
    except Exception as e:
        logger.error(f"خطأ في استعادة النسخة الاحتياطية: {str(e)}")
        messages.error(request, _(f"حدث خطأ في الاستعادة: {str(e)}"))
    
    return redirect('backup:backup_restore')


@login_required
def get_restore_progress(request):
    """الحصول على حالة تقدم الاستعادة"""
    try:
        progress_data = get_restore_progress_data()
        # التحقق من العمليات المعلقة
        if progress_data.get('is_running', False):
            import time
            current_time = time.time()
            last_update = cache.get('restore_last_update', current_time)
            if current_time - last_update > 600:
                cache.delete('restore_progress')
                cache.delete('restore_last_update')
                log_audit(request.user, 'delete', 'تم إلغاء عملية الاستعادة المعلقة تلقائياً')
        return JsonResponse({
            'success': True,
            'progress': progress_data
        })
    except Exception as e:
        logger.error(f"خطأ في جلب تقدم الاستعادة: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def list_backups(request):
    """API لجلب قائمة النسخ الاحتياطية"""
    
    try:
        backup_dir = os.path.join(settings.MEDIA_ROOT, 'backups')
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        backups = []
        for filename in os.listdir(backup_dir):
            if filename.endswith('.json') or filename.endswith('.xlsx'):
                filepath = os.path.join(backup_dir, filename)
                try:
                    stat = os.stat(filepath)
                    file_type = 'XLSX' if filename.endswith('.xlsx') else 'JSON'
                    backups.append({
                        'filename': filename,
                        'size': stat.st_size,
                        'size_formatted': filesizeformat(stat.st_size),
                        'created_at': dt_module.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                        'type': file_type,
                        'download_url': reverse('backup:download_backup', kwargs={'filename': filename})
                    })
                except (OSError, IOError):
                    continue
        
        # ترتيب النسخ حسب تاريخ الإنشاء (الأحدث أولاً)
        backups.sort(key=lambda x: x['created_at'], reverse=True)
        
        return JsonResponse({
            'success': True,
            'backups': backups,
            'count': len(backups)
        })
        
    except Exception as e:
        logger.error(f"خطأ في جلب قائمة النسخ الاحتياطية: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })