from django.db.models import Q
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from decimal import Decimal

User = get_user_model()


CASH_CASHBOX_NAME = 'كاش'
CARD_CASHBOX_NAME = 'صندوق البطاقة'
OLD_CARD_CASHBOX_SUFFIX = ' - card'


def _build_pos_cashbox_names(username):
    return CASH_CASHBOX_NAME, CARD_CASHBOX_NAME


def _create_pos_cashbox(instance, name, description, location, currency):
    from cashboxes.models import Cashbox
    cashbox = Cashbox.objects.create(
        name=name,
        description=description,
        balance=Decimal('0.000'),
        currency=currency,
        is_active=True,
        location=location,
        responsible_user=instance,
    )
    return cashbox


@receiver(post_save, sender=User)
def create_pos_cashboxes(sender, instance, created, **kwargs):
    """إنشاء صناديق النقد والصندوق البطاقة تلقائياً عند إنشاء مستخدم POS"""
    try:
        from cashboxes.models import Cashbox
        from core.models import AuditLog
        from core.models import CompanySettings

        if created and instance.user_type == 'pos_user':
            cashbox_name, card_cashbox_name = _build_pos_cashbox_names(instance.username)
            existing_cashbox = Cashbox.objects.filter(
                responsible_user=instance,
                is_active=True
            ).filter(
                Q(name__iexact=cashbox_name) |
                Q(name__iexact=instance.username)
            ).first()
            existing_card_cashbox = Cashbox.objects.filter(
                responsible_user=instance,
                is_active=True
            ).filter(
                Q(name__iexact=card_cashbox_name) |
                Q(name__iexact=f"{instance.username}{OLD_CARD_CASHBOX_SUFFIX}") |
                Q(name__iexact=f"{instance.username} - Card") |
                Q(name__icontains='بطاقة') |
                Q(name__icontains='Card')
            ).first()

            company_settings = CompanySettings.get_settings()
            currency = 'JOD'
            if company_settings and company_settings.currency:
                currency = company_settings.currency

            if not existing_cashbox:
                cashbox = _create_pos_cashbox(
                    instance,
                    cashbox_name,
                    _('صندوق مستخدم نقطة البيع: %(full_name)s') % {
                        'full_name': instance.get_full_name() or instance.username
                    },
                    _('نقطة البيع - %(username)s') % {'username': instance.username},
                    currency
                )
                try:
                    AuditLog.objects.create(
                        user=instance,
                        action='create',
                        model_name='Cashbox',
                        object_id=cashbox.id,
                        object_repr=str(cashbox),
                        description=_('تم إنشاء صندوق نقد تلقائياً لمستخدم نقطة البيع: %(username)s') % {
                            'username': instance.username
                        },
                        ip_address='127.0.0.1'
                    )
                except Exception as log_error:
                    print(f"خطأ في تسجيل النشاط: {log_error}")
                print(f"تم إنشاء صندوق '{cashbox_name}' للمستخدم {instance.username}")
            else:
                if not existing_cashbox.responsible_user:
                    existing_cashbox.responsible_user = instance
                    existing_cashbox.save()
                    print(f"تم ربط الصندوق الموجود '{cashbox_name}' بالمستخدم {instance.username}")

            if not existing_card_cashbox:
                card_cashbox = _create_pos_cashbox(
                    instance,
                    card_cashbox_name,
                    _('صندوق بطاقة مستخدم نقطة البيع: %(full_name)s') % {
                        'full_name': instance.get_full_name() or instance.username
                    },
                    _('نقطة البيع - %(username)s') % {'username': instance.username},
                    currency
                )
                try:
                    AuditLog.objects.create(
                        user=instance,
                        action='create',
                        model_name='Cashbox',
                        object_id=card_cashbox.id,
                        object_repr=str(card_cashbox),
                        description=_('تم إنشاء صندوق بطاقة تلقائياً لمستخدم نقطة البيع: %(username)s') % {
                            'username': instance.username
                        },
                        ip_address='127.0.0.1'
                    )
                except Exception as log_error:
                    print(f"خطأ في تسجيل النشاط: {log_error}")
                print(f"تم إنشاء صندوق البطاقة '{card_cashbox_name}' للمستخدم {instance.username}")
            else:
                if not existing_card_cashbox.responsible_user:
                    existing_card_cashbox.responsible_user = instance
                    existing_card_cashbox.save()
                    print(f"تم ربط صندوق البطاقة الموجود '{card_cashbox_name}' بالمستخدم {instance.username}")
    except Exception as e:
        print(f"خطأ في إنشاء صناديق POS للمستخدم {instance.username}: {e}")
        pass


@receiver(post_save, sender=User)
def update_pos_cashbox_on_user_change(sender, instance, created, **kwargs):
    """تحديث معلومات الصندوق عند تحديث معلومات المستخدم"""
    try:
        from cashboxes.models import Cashbox
        
        # إذا لم يكن المستخدم جديداً ونوعه pos_user
        if not created and instance.user_type == 'pos_user':
            cashbox_name, card_cashbox_name = _build_pos_cashbox_names(instance.username)
            cashboxes = Cashbox.objects.filter(responsible_user=instance)

            for cashbox in cashboxes:
                if cashbox.name.endswith(CARD_CASHBOX_SUFFIX) or 'بطاقة' in cashbox.name or 'Card' in cashbox.name:
                    new_name = card_cashbox_name
                    new_description = _('صندوق بطاقة مستخدم نقطة البيع: %(full_name)s') % {
                        'full_name': instance.get_full_name() or instance.username
                    }
                else:
                    new_name = cashbox_name
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
                    
                    print(f"تم تحديث معلومات صندوق POS للمستخدم {instance.username}")
                    
    except Exception as e:
        print(f"خطأ في تحديث صندوق POS للمستخدم {instance.username}: {e}")
        pass