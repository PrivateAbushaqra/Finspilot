from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('sales', '0007_alter_salesinvoice_created_at_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='salesinvoice',
            name='inclusive_tax',
            field=models.BooleanField(default=True, verbose_name='شامل ضريبة'),
        ),
        migrations.AlterModelOptions(
            name='salesinvoice',
            options={'ordering': ['-date', '-invoice_number'], 'verbose_name': 'فاتورة مبيعات', 'verbose_name_plural': 'فواتير المبيعات', 'permissions': (('can_toggle_invoice_tax', 'Can toggle invoice tax inclusion'),)},
        ),
    ]
