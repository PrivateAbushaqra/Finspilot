#!/usr/bin/env python
"""
سكريبت لإنشاء بيانات تجريبية لاختبار الرصيد الافتتاحي
"""
import os
import sys
import django

# إعداد Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from banks.models import BankAccount
from users.models import User

def create_test_bank_account():
    """إنشاء حساب بنكي تجريبي برصيد افتتاحي"""
    try:
        # الحصول على مستخدم super
        super_user = User.objects.filter(username='super').first()
        if not super_user:
            print("لم يتم العثور على مستخدم super")
            return

        # إنشاء حساب بنكي برصيد افتتاحي
        bank_account = BankAccount.objects.create(
            name='حساب تجريبي للاختبار',
            bank_name='بنك تجريبي',
            account_number='123456789',
            initial_balance=1000.00,
            balance=1000.00,
            currency='JOD',
            created_by=super_user
        )

        print(f"تم إنشاء حساب بنكي: {bank_account.name} برصيد افتتاحي: {bank_account.initial_balance}")
        return bank_account

    except Exception as e:
        print(f"خطأ في إنشاء الحساب: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    create_test_bank_account()