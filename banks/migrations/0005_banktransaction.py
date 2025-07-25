# Generated by Django 4.2.7 on 2025-07-10 15:30

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('banks', '0004_remove_default_currency'),
    ]

    operations = [
        migrations.CreateModel(
            name='BankTransaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('transaction_type', models.CharField(choices=[('deposit', 'إيداع'), ('withdrawal', 'سحب')], max_length=20, verbose_name='نوع الحركة')),
                ('amount', models.DecimalField(decimal_places=3, max_digits=15, verbose_name='المبلغ')),
                ('description', models.TextField(verbose_name='الوصف')),
                ('reference_number', models.CharField(blank=True, max_length=100, verbose_name='الرقم المرجعي')),
                ('date', models.DateField(verbose_name='التاريخ')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')),
                ('bank', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='transactions', to='banks.bankaccount', verbose_name='الحساب البنكي')),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL, verbose_name='أنشئ بواسطة')),
            ],
            options={
                'verbose_name': 'حركة بنكية',
                'verbose_name_plural': 'الحركات البنكية',
                'ordering': ['-date', '-created_at'],
            },
        ),
    ]
