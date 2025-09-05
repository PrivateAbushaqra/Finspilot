"""
تجهيز سريع لاختبار نظام الإيرادات والمصروفات المتكررة
"""

from django.core.management.base import BaseCommand
from datetime import date
from decimal import Decimal
from revenues_expenses.models import RevenueExpenseCategory, RecurringRevenueExpense

class Command(BaseCommand):
    help = 'إعداد بيانات اختبار للإيرادات والمصروفات المتكررة'
    
    def handle(self, *args, **options):
        self.stdout.write("🔧 بدء إعداد البيانات...")
        
        # إنشاء فئات الاختبار
        revenue_category, created = RevenueExpenseCategory.objects.get_or_create(
            name="إيرادات الاشتراكات",
            defaults={
                'type': 'revenue',
                'is_default': False,
                'description': 'إيرادات من الاشتراكات الشهرية'
            }
        )
        
        expense_category, created = RevenueExpenseCategory.objects.get_or_create(
            name="إيجار المكتب",
            defaults={
                'type': 'expense',
                'is_default': False,
                'description': 'مصروف إيجار المكتب الشهري'
            }
        )
        
        # إنشاء إيرادات متكررة
        monthly_revenue, created = RecurringRevenueExpense.objects.get_or_create(
            name="اشتراك شهري - شركة ABC",
            defaults={
                'category': revenue_category,
                'amount': Decimal('5000.00'),
                'frequency': 'monthly',
                'start_date': date(2024, 1, 1),
                'is_active': True,
                'description': 'اشتراك شهري من شركة ABC'
            }
        )
        
        # إنشاء مصروفات متكررة
        monthly_expense, created = RecurringRevenueExpense.objects.get_or_create(
            name="إيجار المكتب الرئيسي",
            defaults={
                'category': expense_category,
                'amount': Decimal('3000.00'),
                'frequency': 'monthly',
                'start_date': date(2024, 1, 1),
                'is_active': True,
                'description': 'إيجار المكتب الشهري'
            }
        )
        
        # إنشاء إيراد ربع سنوي
        quarterly_revenue, created = RecurringRevenueExpense.objects.get_or_create(
            name="مكافأة أداء فصلية",
            defaults={
                'category': revenue_category,
                'amount': Decimal('15000.00'),
                'frequency': 'quarterly',
                'start_date': date(2024, 1, 1),
                'is_active': True,
                'description': 'مكافأة أداء كل ثلاثة أشهر'
            }
        )
        
        self.stdout.write(
            self.style.SUCCESS('✅ تم إنشاء البيانات التجريبية بنجاح!')
        )
        
        self.stdout.write(f"📊 الإحصائيات:")
        self.stdout.write(f"   - فئات الإيرادات: {RevenueExpenseCategory.objects.filter(type='revenue').count()}")
        self.stdout.write(f"   - فئات المصروفات: {RevenueExpenseCategory.objects.filter(type='expense').count()}")
        self.stdout.write(f"   - العناصر المتكررة النشطة: {RecurringRevenueExpense.objects.filter(is_active=True).count()}")
        
        self.stdout.write(
            self.style.SUCCESS('🎉 يمكنك الآن زيارة: http://127.0.0.1:8000/ar/revenues-expenses/recurring/')
        )
