# Generated by Django 4.2.7 on 2025-07-06 10:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0003_product_cost_price'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='serial_number',
            field=models.CharField(blank=True, help_text='للمنتجات التي تُباع بالقطعة وتحتاج كفالة', max_length=100, verbose_name='الرقم التسلسلي'),
        ),
    ]
