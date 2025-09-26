#!/usr/bin/env python
"""
اختبار تلقائي للتقرير الضريبي
يختبر التقرير الضريبي ويحفظ النتائج في ملف نصي
"""

import os
import sys
import django
from datetime import datetime, timedelta

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
User = get_user_model()
from django.utils import timezone
from core.views import TaxReportView


class TaxReportTest(TestCase):
    """اختبار التقرير الضريبي"""

    def setUp(self):
        """إعداد البيانات للاختبار"""
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            is_staff=True
        )

    def test_tax_report_generation(self):
        """اختبار إنشاء التقرير الضريبي"""
        print("بدء اختبار التقرير الضريبي...")

        # إنشاء طلب GET للتقرير
        request = self.factory.get('/reports/tax/')
        request.user = self.user

        # إنشاء view واستدعاء get_context_data
        view = TaxReportView()
        view.request = request

        try:
            context = view.get_context_data()

            # جمع النتائج
            results = {
                'timestamp': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
                'tax_data_count': len(context.get('tax_data', [])),
                'all_tax_rates': context.get('all_tax_rates', []),
                'total_positive': context.get('total_positive', 0),
                'total_negative': context.get('total_negative', 0),
                'net_tax': context.get('net_tax', 0),
                'grand_total_tax': context.get('grand_total_tax', 0),
                'total_amount_before_tax': context.get('total_amount_before_tax', 0),
                'column_totals': context.get('column_totals', {}),
            }

            # حفظ النتائج في ملف
            output_file = r'C:\Accounting_soft\finspilot\test_result\tax_report_test_result.txt'

            # التأكد من وجود المجلد
            os.makedirs(os.path.dirname(output_file), exist_ok=True)

            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("=== نتائج اختبار التقرير الضريبي ===\n\n")
                f.write(f"تاريخ الاختبار: {results['timestamp']}\n")
                f.write(f"عدد السجلات: {results['tax_data_count']}\n")
                f.write(f"أسعار الضرائب المتاحة: {', '.join(map(str, results['all_tax_rates']))}\n")
                f.write(f"إجمالي الضرائب الموجبة: {results['total_positive']:.2f}\n")
                f.write(f"إجمالي الضرائب السالبة: {results['total_negative']:.2f}\n")
                f.write(f"صافي الضريبة: {results['net_tax']:.2f}\n")
                f.write(f"إجمالي الضريبة الكلي: {results['grand_total_tax']:.2f}\n")
                f.write(f"إجمالي القيم قبل الضريبة: {results['total_amount_before_tax']:.2f}\n\n")

                f.write("إجماليات أعمدة الضرائب:\n")
                for rate, total in results['column_totals'].items():
                    f.write(f"  ضريبة {rate}%: {total:.2f}\n")

                f.write("\n=== تفاصيل البيانات ===\n")
                tax_data = context.get('tax_data', [])
                if tax_data:
                    for i, item in enumerate(tax_data[:10], 1):  # عرض أول 10 سجلات فقط
                        f.write(f"\nسجل {i}:\n")
                        f.write(f"  رقم المستند: {item['document_number']}\n")
                        f.write(f"  نوع المستند: {item['document_type']}\n")
                        f.write(f"  العميل/المورد: {item['customer_supplier']}\n")
                        f.write(f"  التاريخ: {item['date']}\n")
                        f.write(f"  القيمة قبل الضريبة: {item['amount_before_tax']:.2f}\n")
                        f.write(f"  إجمالي الضريبة: {item['total_tax']:.2f}\n")
                        f.write(f"  تفصيل الضرائب: {item['tax_breakdown']}\n")
                else:
                    f.write("لا توجد بيانات ضريبية\n")

                f.write("\n=== نهاية التقرير ===\n")

            print(f"تم حفظ نتائج الاختبار في: {output_file}")
            print("اختبار التقرير الضريبي مكتمل بنجاح!")

            return True

        except Exception as e:
            error_msg = f"خطأ في اختبار التقرير الضريبي: {str(e)}"
            print(error_msg)

            # حفظ رسالة الخطأ في الملف
            output_file = r'C:\Accounting_soft\finspilot\test_result\tax_report_test_result.txt'
            os.makedirs(os.path.dirname(output_file), exist_ok=True)

            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("=== خطأ في اختبار التقرير الضريبي ===\n\n")
                f.write(f"تاريخ الاختبار: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"رسالة الخطأ: {error_msg}\n")

            return False

    def test_tax_report_filters(self):
        """اختبار فلاتر التقرير الضريبي"""
        print("اختبار فلاتر التقرير الضريبي...")

        # اختبار فلتر التاريخ
        start_date = (timezone.now().date() - timedelta(days=30)).strftime('%Y-%m-%d')
        end_date = timezone.now().date().strftime('%Y-%m-%d')

        request = self.factory.get(f'/reports/tax/?start_date={start_date}&end_date={end_date}')
        request.user = self.user

        view = TaxReportView()
        view.request = request

        try:
            context = view.get_context_data()
            print(f"تم تطبيق فلتر التاريخ: من {start_date} إلى {end_date}")
            print(f"عدد السجلات المفلترة: {len(context.get('tax_data', []))}")
            return True
        except Exception as e:
            print(f"خطأ في اختبار الفلاتر: {str(e)}")
            return False


def run_tax_report_test():
    """تشغيل اختبار التقرير الضريبي"""
    print("=== بدء اختبار التقرير الضريبي ===")

    test_instance = TaxReportTest()
    test_instance.setUp()

    # تشغيل الاختبارات
    success1 = test_instance.test_tax_report_generation()
    success2 = test_instance.test_tax_report_filters()

    print("\n=== ملخص النتائج ===")
    print(f"اختبار إنشاء التقرير: {'نجح' if success1 else 'فشل'}")
    print(f"اختبار الفلاتر: {'نجح' if success2 else 'فشل'}")

    if success1 and success2:
        print("جميع اختبارات التقرير الضريبي نجحت!")
        return True
    else:
        print("بعض اختبارات التقرير الضريبي فشلت!")
        return False


if __name__ == '__main__':
    success = run_tax_report_test()
    sys.exit(0 if success else 1)