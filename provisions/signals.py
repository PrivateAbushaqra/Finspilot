from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from .models import Provision, ProvisionEntry
from journal.models import JournalEntry, JournalLine


@receiver(post_save, sender=Provision)
def create_provision_journal_entry(sender, instance, created, **kwargs):
    """Create journal entry when creating or updating a provision"""
    if created:
        # Create journal entry for provision
        entry = JournalEntry(
            entry_date=instance.start_date,
            reference_type='provision',
            reference_id=instance.id,
            description=f'{_("Provision")}: {instance.name}'
        )
        entry.entry_number = entry.generate_entry_number()
        entry.save()

        # Debit entry in provision account
        JournalLine.objects.create(
            journal_entry=entry,
            account=instance.provision_account,
            debit=instance.amount,
            credit=0,
            description=f'{_("Provision")}: {instance.name}'
        )

        # Credit entry in related account
        JournalLine.objects.create(
            journal_entry=entry,
            account=instance.related_account,
            debit=0,
            credit=instance.amount,
            description=f'{_("Provision")}: {instance.name}'
        )


@receiver(post_save, sender=ProvisionEntry)
def create_provision_entry_journal_entry(sender, instance, created, **kwargs):
    """Create journal entry when adding a provision entry"""
    if created:
        # Create journal entry for provision entry
        entry = JournalEntry(
            entry_date=instance.date,
            reference_type='provision_entry',
            reference_id=instance.id,
            description=f'{_("Provision Entry")}: {instance.provision.name}'
        )
        entry.entry_number = entry.generate_entry_number()
        entry.save()

        # Determine transaction type based on provision type
        if instance.provision.provision_type.name in [_('Bad Debt'), _('Depreciation'), _('Inventory Provision')]:
            # For provisions that reduce assets or increase expenses
            debit_account = instance.provision.provision_account  # Provision account
            credit_account = instance.provision.related_account  # Related accountt
        else:
            # For other provisions
            debit_account = instance.provision.related_account
            credit_account = instance.provision.provision_account

        # Debit entry
        JournalLine.objects.create(
            journal_entry=entry,
            account=debit_account,
            debit=instance.amount,
            credit=0,
            description=f'{_("Provision Entry")}: {instance.description}'
        )

        # Credit entry
        JournalLine.objects.create(
            journal_entry=entry,
            account=credit_account,
            debit=0,
            credit=instance.amount,
            description=f'{_("Provision Entry")}: {instance.description}'
        )


@receiver(post_delete, sender=Provision)
def delete_provision_journal_entries(sender, instance, **kwargs):
    """Delete journal entries when deleting a provision"""
    # Delete all journal entries related to the provision
    JournalEntry.objects.filter(
        reference_type='provision',
        reference_id=instance.id
    ).delete()

    # Delete entry entries
    for entry in instance.provisionentry_set.all():
        JournalEntry.objects.filter(
            reference_type='provision_entry',
            reference_id=entry.id
        ).delete()


@receiver(post_delete, sender=ProvisionEntry)
def delete_provision_entry_journal_entry(sender, instance, **kwargs):
    """Delete journal entry when deleting a provision entry"""
    JournalEntry.objects.filter(
        reference_type='provision_entry',
        reference_id=instance.id
    ).delete()