from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from .models import Provision, ProvisionEntry
from journal.models import JournalEntry, JournalLine


@receiver(post_save, sender=Provision)
def create_provision_journal_entry(sender, instance, created, **kwargs):
    """إنشاء قيد محاسبي عند إنشاء أو تحديث مخصص"""
    if created:
        # إنشاء قيد محاسبي للمخصص
        entry = JournalEntry(
            entry_date=instance.start_date,
            reference_type='provision',
            reference_id=instance.id,
            description=f'{_("Provision")}: {instance.name}'
        )
        entry.entry_number = entry.generate_entry_number()
        entry.save()

        # إدخال في حساب المخصص (مدين)
        JournalLine.objects.create(
            journal_entry=entry,
            account=instance.provision_account,
            debit=instance.amount,
            credit=0,
            description=f'{_("Provision")}: {instance.name}'
        )

        # إدخال في الحساب المرتبط (دائن)
        JournalLine.objects.create(
            journal_entry=entry,
            account=instance.related_account,
            debit=0,
            credit=instance.amount,
            description=f'{_("Provision")}: {instance.name}'
        )


@receiver(post_save, sender=ProvisionEntry)
def create_provision_entry_journal_entry(sender, instance, created, **kwargs):
    """إنشاء قيد محاسبي عند إضافة إدخال مخصص"""
    if created:
        # إنشاء قيد محاسبي لإدخال المخصص
        entry = JournalEntry(
            entry_date=instance.date,
            reference_type='provision_entry',
            reference_id=instance.id,
            description=f'{_("Provision Entry")}: {instance.provision.name}'
        )
        entry.entry_number = entry.generate_entry_number()
        entry.save()

        # تحديد نوع الحركة حسب نوع المخصص
        if instance.provision.provision_type.name in [_('Bad Debt'), _('Depreciation'), _('Inventory Provision')]:
            # للمخصصات التي تقلل من الأصول أو تزيد من المصاريف
            debit_account = instance.provision.provision_account  # حساب المخصص
            credit_account = instance.provision.related_account  # الحساب المرتبط
        else:
            # للمخصصات الأخرى
            debit_account = instance.provision.related_account
            credit_account = instance.provision.provision_account

        # إدخال في حساب المدين
        JournalLine.objects.create(
            journal_entry=entry,
            account=debit_account,
            debit=instance.amount,
            credit=0,
            description=f'{_("Provision Entry")}: {instance.description}'
        )

        # إدخال في حساب الدائن
        JournalLine.objects.create(
            journal_entry=entry,
            account=credit_account,
            debit=0,
            credit=instance.amount,
            description=f'{_("Provision Entry")}: {instance.description}'
        )


@receiver(post_delete, sender=Provision)
def delete_provision_journal_entries(sender, instance, **kwargs):
    """حذف القيود المحاسبية عند حذف مخصص"""
    # حذف جميع القيود المتعلقة بالمخصص
    JournalEntry.objects.filter(
        reference_type='provision',
        reference_id=instance.id
    ).delete()

    # حذف قيود الإدخالات
    for entry in instance.provisionentry_set.all():
        JournalEntry.objects.filter(
            reference_type='provision_entry',
            reference_id=entry.id
        ).delete()


@receiver(post_delete, sender=ProvisionEntry)
def delete_provision_entry_journal_entry(sender, instance, **kwargs):
    """حذف القيد المحاسبي عند حذف إدخال مخصص"""
    JournalEntry.objects.filter(
        reference_type='provision_entry',
        reference_id=instance.id
    ).delete()