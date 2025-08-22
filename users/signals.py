from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from decimal import Decimal

User = get_user_model()


@receiver(post_save, sender=User)
def create_pos_cashbox(sender, instance, created, **kwargs):
    """إنشاء صندوق تلقائياً عند إنشاء مستخدم POS"""
    try:
        from cashboxes.models import Cashbox
        from core.models import AuditLog
        from core.models import CompanySettings
        
        # التحقق من أن المستخدم نوعه pos_user وأنه تم إنشاؤه حديثاً
        if created and instance.user_type == 'pos_user':
            # اسم الصندوق يكون نفس اسم المستخدم
            cashbox_name = instance.username
            existing_cashbox = Cashbox.objects.filter(name=cashbox_name).first()
            
            if not existing_cashbox:
                # الحصول على العملة الأساسية من إعدادات الشركة
                company_settings = CompanySettings.get_settings()
                currency = 'JOD'  # افتراضي
                if company_settings and company_settings.currency:
                    currency = company_settings.currency
                
                # إنشاء الصندوق الجديد بكامل المواصفات
                cashbox = Cashbox.objects.create(
                    name=cashbox_name,  # اسم الصندوق = اسم المستخدم
                    description=_('صندوق مستخدم نقطة البيع: %(full_name)s') % {
                        'full_name': instance.get_full_name() or instance.username
                    },
                    balance=Decimal('0.000'),  # رصيد ابتدائي صفر
                    currency=currency,  # العملة الأساسية
                    is_active=True,  # نشط
                    location=_('نقطة البيع - %(username)s') % {'username': instance.username},
                    responsible_user=instance,  # المسؤول عن الصندوق
                )
                
                # تسجيل النشاط في سجل الأنشطة
                try:
                    AuditLog.objects.create(
                        user=instance,
                        action='create',
                        model_name='Cashbox',
                        object_id=cashbox.id,
                        object_repr=str(cashbox),
                        description=_('تم إنشاء صندوق تلقائياً لمستخدم نقطة البيع: %(username)s') % {
                            'username': instance.username
                        },
                        ip_address='127.0.0.1'
                    )
                except Exception as log_error:
                    print(f"خطأ في تسجيل النشاط: {log_error}")
                
                print(f"تم إنشاء صندوق '{cashbox_name}' للمستخدم {instance.username}")
            else:
                # ربط الصندوق الموجود بالمستخدم إذا لم يكن مربوطاً
                if not existing_cashbox.responsible_user:
                    existing_cashbox.responsible_user = instance
                    existing_cashbox.save()
                    print(f"تم ربط الصندوق الموجود '{cashbox_name}' بالمستخدم {instance.username}")
                
    except Exception as e:
        print(f"خطأ في إنشاء صندوق POS للمستخدم {instance.username}: {e}")
        # لا نوقف عملية إنشاء المستخدم في حالة فشل إنشاء الصندوق
        pass


@receiver(post_save, sender=User)
def update_pos_cashbox_on_user_change(sender, instance, created, **kwargs):
    """تحديث معلومات الصندوق عند تحديث معلومات المستخدم"""
    try:
        from cashboxes.models import Cashbox
        
        # إذا لم يكن المستخدم جديداً ونوعه pos_user
        if not created and instance.user_type == 'pos_user':
            # البحث عن الصندوق المرتبط بالمستخدم
            cashbox = Cashbox.objects.filter(responsible_user=instance).first()
            
            if cashbox:
                # تحديث اسم الصندوق ووصفه ليطابق اسم المستخدم
                new_name = instance.username
                new_description = _('صندوق مستخدم نقطة البيع: %(full_name)s') % {
                    'full_name': instance.get_full_name() or instance.username
                }
                new_location = _('نقطة البيع - %(username)s') % {'username': instance.username}
                
                if (cashbox.name != new_name or 
                    cashbox.description != new_description or 
                    cashbox.location != new_location):
                    
                    cashbox.name = new_name
                    cashbox.description = new_description
                    cashbox.location = new_location
                    cashbox.save()
                    
                    # تسجيل التحديث في سجل الأنشطة
                    try:
                        from core.models import AuditLog
                        AuditLog.objects.create(
                            user=instance,
                            action='change',
                            model_name='Cashbox',
                            object_id=cashbox.id,
                            object_repr=str(cashbox),
                            description=_('تم تحديث معلومات الصندوق للمستخدم: %(username)s') % {
                                'username': instance.username
                            },
                            ip_address='127.0.0.1'
                        )
                    except Exception as log_error:
                        print(f"خطأ في تسجيل تحديث الصندوق: {log_error}")
                    
                    print(f"تم تحديث معلومات الصندوق للمستخدم {instance.username}")
                    
    except Exception as e:
        print(f"خطأ في تحديث صندوق POS للمستخدم {instance.username}: {e}")
        pass