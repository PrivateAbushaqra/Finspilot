# Generated by Django 4.2.7 on 2025-07-10 15:30

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('customers', '0001_initial'),
        ('cashboxes', '0001_initial'),
        ('banks', '0005_banktransaction'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PaymentVoucher',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('voucher_number', models.CharField(max_length=50, unique=True, verbose_name='رقم السند')),
                ('date', models.DateField(verbose_name='تاريخ السند')),
                ('voucher_type', models.CharField(choices=[('supplier', 'دفع لمورد'), ('expense', 'مصروفات'), ('salary', 'راتب'), ('other', 'أخرى')], max_length=20, verbose_name='نوع السند')),
                ('payment_type', models.CharField(choices=[('cash', 'نقدي'), ('check', 'شيك'), ('bank_transfer', 'تحويل بنكي')], max_length=15, verbose_name='نوع الدفع')),
                ('amount', models.DecimalField(decimal_places=3, max_digits=15, verbose_name='المبلغ')),
                ('beneficiary_name', models.CharField(blank=True, help_text='في حالة عدم كون المستفيد مورد مسجل', max_length=200, verbose_name='اسم المستفيد')),
                ('bank_reference', models.CharField(blank=True, max_length=100, verbose_name='مرجع التحويل')),
                ('check_number', models.CharField(blank=True, max_length=50, verbose_name='رقم الشيك')),
                ('check_date', models.DateField(blank=True, null=True, verbose_name='تاريخ الشيك')),
                ('check_due_date', models.DateField(blank=True, null=True, verbose_name='تاريخ استحقاق الشيك')),
                ('check_bank_name', models.CharField(blank=True, max_length=200, verbose_name='اسم البنك')),
                ('check_status', models.CharField(blank=True, choices=[('pending', 'في الانتظار'), ('cleared', 'تم الصرف'), ('cancelled', 'ملغي')], default='pending', max_length=20, verbose_name='حالة الشيك')),
                ('description', models.TextField(verbose_name='الوصف')),
                ('notes', models.TextField(blank=True, verbose_name='ملاحظات')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='تاريخ التحديث')),
                ('is_active', models.BooleanField(default=True, verbose_name='نشط')),
                ('is_reversed', models.BooleanField(default=False, verbose_name='مُعكوس')),
                ('reversed_at', models.DateTimeField(blank=True, null=True, verbose_name='تاريخ العكس')),
                ('reversal_reason', models.TextField(blank=True, verbose_name='سبب العكس')),
                ('bank', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='payment_vouchers', to='banks.bankaccount', verbose_name='البنك')),
                ('cashbox', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='payment_vouchers', to='cashboxes.cashbox', verbose_name='الصندوق النقدي')),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL, verbose_name='أنشئ بواسطة')),
                ('reversed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reversed_payments', to=settings.AUTH_USER_MODEL, verbose_name='عُكس بواسطة')),
                ('supplier', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='payment_vouchers', to='customers.customersupplier', verbose_name='المورد')),
            ],
            options={
                'verbose_name': 'سند صرف',
                'verbose_name_plural': 'سندات الصرف',
                'ordering': ['-date', '-voucher_number'],
            },
        ),
    ]
