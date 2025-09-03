# Customer Deletion Fix Migration
# This ensures proper cascade deletion for CustomerSupplier foreign keys

from django.db import migrations

class Migration(migrations.Migration):
    
    dependencies = [
        ('customers', '0004_alter_customersupplier_options_and_more'),
        ('sales', '0003_alter_salesinvoice_customer'),
        ('purchases', '0003_purchasereturn_purchasereturnitem'),
    ]

    operations = [
        # No actual database changes needed
        # The deletion logic is handled in views.py
        # This migration is for backup/restore compatibility
    ]
