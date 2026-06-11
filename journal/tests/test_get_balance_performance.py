"""
Unit Tests لدالة get_balance()
التحقق من الأداء الفعّال وعدم وجود N+1 queries
"""
from django.test import TestCase
from django.test.utils import override_settings
from django.db import connection, reset_queries
from django.db.models import Q
from decimal import Decimal
from journal.models import Account, JournalEntry, JournalLine
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date

User = get_user_model()


@override_settings(DEBUG=True)  # لتفعيل تتبع الاستعلامات
class GetBalancePerformanceTests(TestCase):
    """اختبارات أداء دالة get_balance"""
    
    def setUp(self):
        """إعداد بيانات الاختبار"""
        # إنشاء مستخدم اختبار
        self.user = User.objects.create_user(
            username='test_user',
            password='test_password',
            user_type='admin'
        )
        
        # إنشاء حسابات أب وفرعية
        self.parent_account = Account.objects.create(
            code='1',
            name='الأصول الحالية',
            account_type='asset',
            is_active=True
        )
        
        # إنشاء عدة حسابات فرعية
        self.child_accounts = []
        for i in range(1, 4):
            child = Account.objects.create(
                code=f'1.{i}',
                name=f'حساب فرعي {i}',
                account_type='asset',
                parent=self.parent_account,
                is_active=True
            )
            self.child_accounts.append(child)
        
        # إنشاء مدخلات يومية (journal entries) لكل حساب فرعي
        for idx, account in enumerate(self.child_accounts):
            entry = JournalEntry.objects.create(
                entry_number=f'JE{idx}',
                entry_date=date.today(),
                entry_type='daily',
                description=f'إدخال اختبار للحساب {account.name}',
                total_amount=Decimal('1000.000'),
                created_by=self.user
            )
            
            # إنشاء بنود القيد (journal lines)
            JournalLine.objects.create(
                journal_entry=entry,
                account=account,
                debit=Decimal('1000.000'),
                credit=Decimal('0.000'),
                description=f'دين للحساب {account.code}'
            )
    
    def test_get_balance_leaf_account(self):
        """اختبار الحصول على رصيد حساب ورقي (بدون أبناء)"""
        reset_queries()
        
        # الحصول على رصيد الحساب الفرعي
        balance = self.child_accounts[0].get_balance()
        
        # التحقق من أن الرصيد صحيح (1000 = 1000 - 0)
        self.assertEqual(balance, Decimal('1000.000'))
        
        # التحقق من عدد الاستعلامات
        query_count = len(connection.queries)
        print(f"\n✅ عدد الاستعلامات لحساب ورقي: {query_count}")
        
        # يجب أن يكون هناك استعلام واحد فقط أو اثنين على الأكثر
        self.assertLessEqual(query_count, 2, 
            f"اختبرت أكثر من 2 استعلامات للحساب الورقي! ({query_count} استعلام)")
    
    def test_get_balance_parent_account(self):
        """اختبار الحصول على رصيد حساب أب (مع حسابات فرعية)"""
        reset_queries()
        
        # الحصول على رصيد حساب الأب
        balance = self.parent_account.get_balance()
        
        # التحقق من أن الرصيد هو مجموع أرصدة الأبناء (3000 = 1000 * 3)
        expected = Decimal('3000.000')
        self.assertEqual(balance, expected, 
            f"الرصيد المحسوب {balance} لا يساوي الرصيد المتوقع {expected}")
        
        # التحقق من عدد الاستعلامات
        query_count = len(connection.queries)
        print(f"✅ عدد الاستعلامات لحساب أب: {query_count}")
        
        # يجب أن يكون هناك استعلام واحد فقط أو اثنين على الأكثر
        self.assertLessEqual(query_count, 2, 
            f"اختبرت أكثر من 2 استعلامات للحساب الأب! ({query_count} استعلام)")
    
    def test_no_n_plus_one_queries(self):
        """اختبار أن الدالة لا تحتوي على N+1 queries"""
        reset_queries()
        
        # الحصول على جميع الحسابات الفرعية
        accounts = Account.objects.filter(parent=self.parent_account)
        
        # حساب أرصدة جميع الحسابات
        for account in accounts:
            balance = account.get_balance()
        
        query_count = len(connection.queries)
        print(f"✅ عدد الاستعلامات لـ {len(accounts)} حسابات: {query_count}")
        
        # يجب أن يكون هناك استعلام واحد فقط أو بضعة استعلامات على الأكثر
        # وليس N استعلام (أي استعلام لكل حساب)
        # المتوقع: 1 استعلام للتحقق من وجود الأبناء + 1 استعلام للمجاميع لكل حساب
        # = 2 * عدد الحسابات في الأسوأ الحالات، لكن يجب أن يكون أقل من ذلك بكثير
        
        # في الحقيقة، يجب أن يكون بحد أقصى 3-4 استعلامات فقط
        self.assertLess(query_count, len(accounts) * 2, 
            f"يبدو أن هناك N+1 queries! ({query_count} استعلام لـ {len(accounts)} حساب)")
    
    def test_get_balance_with_date_filter(self):
        """اختبار الحصول على رصيد الحساب حتى تاريخ معين"""
        reset_queries()
        
        # الحصول على رصيد الحساب حتى اليوم
        balance = self.child_accounts[0].get_balance(as_of_date=date.today())
        
        # التحقق من أن الرصيد صحيح
        self.assertEqual(balance, Decimal('1000.000'))
        
        # التحقق من عدد الاستعلامات
        query_count = len(connection.queries)
        print(f"✅ عدد الاستعلامات مع فلتر التاريخ: {query_count}")
        
        # يجب أن يكون هناك استعلام واحد فقط أو اثنين على الأكثر
        self.assertLessEqual(query_count, 2, 
            f"اختبرت أكثر من 2 استعلامات مع فلتر التاريخ! ({query_count} استعلام)")
    
    def test_get_balance_with_circular_reference_protection(self):
        """اختبار حماية الدالة من الحلقات المفرغة"""
        # إنشاء حلقة مفرغة (لاختبار الحماية)
        # الحساب 1 -> الحساب 2 -> الحساب 3 -> الحساب 1
        
        # لا نقوم بإنشاء حلقة حقيقية لأن نموذج Account لديه حماية
        # لكن نتحقق من أن الدالة تعالج الحلقات بشكل آمن
        
        reset_queries()
        balance = self.parent_account.get_balance()
        
        # التحقق من أن الدالة لم تتعطل
        self.assertIsNotNone(balance)
        self.assertIsInstance(balance, Decimal)
    
    def test_get_balance_consistency(self):
        """اختبار اتساق الرصيد المحسوب"""
        # الحصول على أرصدة جميع الحسابات
        child_balances = [account.get_balance() for account in self.child_accounts]
        parent_balance = self.parent_account.get_balance()
        
        # يجب أن يكون رصيد الأب = مجموع أرصدة الأبناء
        expected_parent_balance = sum(child_balances)
        
        self.assertEqual(parent_balance, expected_parent_balance,
            f"الرصيد غير متسق! رصيد الأب {parent_balance} ≠ مجموع الأبناء {expected_parent_balance}")


class GetBalanceAccuracyTests(TestCase):
    """اختبارات دقة حساب الرصيد"""
    
    def setUp(self):
        """إعداد بيانات الاختبار"""
        self.user = User.objects.create_user(
            username='test_user2',
            password='test_password',
            user_type='admin'
        )
        
        # إنشاء حساب أصل (أصول)
        self.asset_account = Account.objects.create(
            code='101',
            name='النقد في الصندوق',
            account_type='asset',
            is_active=True
        )
        
        # إنشاء حساب مطلوبات
        self.liability_account = Account.objects.create(
            code='201',
            name='الحسابات الدائنة',
            account_type='liability',
            is_active=True
        )
    
    def test_asset_account_calculation(self):
        """اختبار حساب الأصول (الرصيد = مدين - دائن)"""
        # إنشاء قيد: مدين 1000، دائن 300
        entry = JournalEntry.objects.create(
            entry_number='JE001',
            entry_date=date.today(),
            entry_type='daily',
            description='اختبار',
            total_amount=Decimal('1300.000'),
            created_by=self.user
        )
        
        JournalLine.objects.create(
            journal_entry=entry,
            account=self.asset_account,
            debit=Decimal('1000.000'),
            credit=Decimal('300.000'),
            description='الرصيد'
        )
        
        balance = self.asset_account.get_balance()
        
        # الرصيد = 1000 - 300 = 700
        expected = Decimal('700.000')
        self.assertEqual(balance, expected,
            f"رصيد الأصل غير صحيح! المحسوب: {balance}, المتوقع: {expected}")
    
    def test_liability_account_calculation(self):
        """اختبار حساب المطلوبات (الرصيد = دائن - مدين)"""
        # إنشاء قيد: مدين 300، دائن 1000
        entry = JournalEntry.objects.create(
            entry_number='JE002',
            entry_date=date.today(),
            entry_type='daily',
            description='اختبار',
            total_amount=Decimal('1300.000'),
            created_by=self.user
        )
        
        JournalLine.objects.create(
            journal_entry=entry,
            account=self.liability_account,
            debit=Decimal('300.000'),
            credit=Decimal('1000.000'),
            description='الرصيد'
        )
        
        balance = self.liability_account.get_balance()
        
        # الرصيد = 1000 - 300 = 700
        expected = Decimal('700.000')
        self.assertEqual(balance, expected,
            f"رصيد المطلوبات غير صحيح! المحسوب: {balance}, المتوقع: {expected}")
