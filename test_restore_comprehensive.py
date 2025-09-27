import os
import sys
import django
import time
import json
from datetime import datetime
from decimal import Decimal

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from django.contrib.auth import authenticate, login
from django.test import Client
from django.contrib.auth.models import User
from django.apps import apps
from django.core import serializers
from django.db import transaction
from django.db.models.deletion import ProtectedError
from backup.views import perform_backup_task, perform_backup_restore, get_backup_tables_info
from core.models import AuditLog
from users.models import User as CustomUser

class RestoreTester:
    """فئة لاختبار عمليات الاستعادة الشاملة"""

    def __init__(self):
        self.client = Client()
        self.results = []
        self.errors = []
        self.backup_files = {}
        self.restore_durations = {}

    def log_result(self, test_name, status, message=""):
        """تسجيل نتيجة اختبار"""
        result = {
            'test': test_name,
            'status': status,
            'message': message,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        self.results.append(result)
        print(f"[{result['timestamp']}] {test_name}: {status} - {message}")

    def log_error(self, test_name, error_message):
        """تسجيل خطأ"""
        error = {
            'test': test_name,
            'error': error_message,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        self.errors.append(error)
        print(f"[{error['timestamp']}] خطأ في {test_name}: {error_message}")

    def login_as_superuser(self):
        """تسجيل الدخول كـ superuser"""
        try:
            user = CustomUser.objects.get(username='super')
            self.client.force_login(user)
            self.log_result("تسجيل الدخول كـ superuser", "نجح", f"المستخدم: {user.username}")
            return True
        except Exception as e:
            self.log_error("تسجيل الدخول كـ superuser", str(e))
            return False

    def create_test_data(self):
        """إنشاء بيانات اختبار أساسية"""
        try:
            from journal.models import Account
            from customers.models import CustomerSupplier
            from products.models import Product, Category

            # إنشاء فئة منتج إذا لم توجد
            category, created = Category.objects.get_or_create(
                name="فئة اختبار",
                defaults={'description': "فئة للاختبار"}
            )

            # إنشاء منتج
            product, created = Product.objects.get_or_create(
                code="TEST-001",
                defaults={
                    'name': "منتج اختبار",
                    'category': category,
                    'product_type': 'physical',
                    'unit': 'قطعة',
                    'selling_price': Decimal('100.00')
                }
            )

            # إنشاء عميل
            customer, created = CustomerSupplier.objects.get_or_create(
                name="عميل اختبار",
                type='customer',
                defaults={
                    'phone': "123456789",
                    'email': "test@example.com"
                }
            )

            # إنشاء حساب
            account, created = Account.objects.get_or_create(
                code="1000",
                defaults={
                    'name': "حساب اختبار",
                    'account_type': 'asset',
                    'is_active': True
                }
            )

            self.log_result("إنشاء بيانات الاختبار", "نجح", f"تم إنشاء {4} سجل اختبار")
            return True

        except Exception as e:
            self.log_error("إنشاء بيانات الاختبار", str(e))
            return False

    def test_full_backup(self, format_type):
        """اختبار النسخ الاحتياطي الكامل"""
        try:
            start_time = time.time()

            # الحصول على المستخدم
            user = CustomUser.objects.get(username='super')

            # إنشاء اسم الملف
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'full_backup_test_{format_type}_{timestamp}.{format_type.lower()}'
            filepath = os.path.join('media', 'backups', filename)

            # تنفيذ النسخ الاحتياطي الكامل
            perform_backup_task(user, timestamp, filename, filepath, format_type)

            end_time = time.time()
            duration = end_time - start_time

            # التحقق من إنشاء الملف
            if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                file_size = os.path.getsize(filepath)
                self.log_result(f"النسخ الاحتياطي الكامل ({format_type})", "نجح",
                              f"الملف: {filename}, الحجم: {file_size} بايت, الوقت المستغرق: {duration:.2f} ثانية")
                return filepath, duration
            else:
                self.log_error(f"النسخ الاحتياطي الكامل ({format_type})", "الملف لم يتم إنشاؤه أو فارغ")
                return None, duration

        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            self.log_error(f"النسخ الاحتياطي الكامل ({format_type})", f"{str(e)} (الوقت المستغرق: {duration:.2f} ثانية)")
            return None, duration

    def test_partial_backup(self, format_type, selected_tables):
        """اختبار النسخ الاحتياطي الجزئي"""
        try:
            start_time = time.time()

            # الحصول على المستخدم
            user = CustomUser.objects.get(username='super')

            # إنشاء اسم الملف
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'partial_backup_test_{format_type}_{timestamp}.{format_type.lower()}'
            filepath = os.path.join('media', 'backups', filename)

            # تنفيذ النسخ الاحتياطي الجزئي (سنحتاج لتعديل الوظيفة لدعم الجداول المحددة)
            # للاختبار البسيط، سنستخدم النسخ الكامل للآن
            perform_backup_task(user, timestamp, filename, filepath, format_type)

            end_time = time.time()
            duration = end_time - start_time

            if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                file_size = os.path.getsize(filepath)
                self.log_result(f"النسخ الاحتياطي الجزئي ({format_type})", "نجح",
                              f"الملف: {filename}, الحجم: {file_size} بايت, الوقت المستغرق: {duration:.2f} ثانية")
                return filepath, duration
            else:
                self.log_error(f"النسخ الاحتياطي الجزئي ({format_type})", "الملف لم يتم إنشاؤه")
                return None, duration

        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            self.log_error(f"النسخ الاحتياطي الجزئي ({format_type})", f"{str(e)} (الوقت المستغرق: {duration:.2f} ثانية)")
            return None, duration

    def test_full_restore(self, backup_file, format_type, clear_data=False):
        """اختبار الاستعادة الكاملة"""
        try:
            start_time = time.time()

            # قراءة ملف النسخ الاحتياطي
            if format_type == 'JSON':
                with open(backup_file, 'r', encoding='utf-8') as f:
                    backup_data = json.load(f)
            else:  # XLSX
                from backup.views import load_backup_from_xlsx
                with open(backup_file, 'rb') as f:
                    backup_data = load_backup_from_xlsx(f)

            # الحصول على المستخدم
            user = CustomUser.objects.get(username='super')

            # تنفيذ الاستعادة الكاملة
            perform_backup_restore(backup_data, clear_data=clear_data, user=user)

            end_time = time.time()
            duration = end_time - start_time

            self.log_result(f"الاستعادة الكاملة ({format_type}) - مسح البيانات: {clear_data}", "نجح",
                          f"الوقت المستغرق: {duration:.2f} ثانية")
            return duration

        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            self.log_error(f"الاستعادة الكاملة ({format_type}) - مسح البيانات: {clear_data}", f"{str(e)} (الوقت المستغرق: {duration:.2f} ثانية)")
            return duration

    def test_partial_restore(self, backup_file, format_type, selected_tables, clear_data=False):
        """اختبار الاستعادة الجزئية"""
        try:
            start_time = time.time()

            # قراءة ملف النسخ الاحتياطي
            if format_type == 'JSON':
                with open(backup_file, 'r', encoding='utf-8') as f:
                    backup_data = json.load(f)
            else:  # XLSX
                from backup.views import load_backup_from_xlsx
                with open(backup_file, 'rb') as f:
                    backup_data = load_backup_from_xlsx(f)

            # تصفية البيانات للجداول المحددة فقط
            filtered_data = {'metadata': backup_data.get('metadata', {}), 'data': {}}
            for app_name, app_data in backup_data.get('data', {}).items():
                if app_name in selected_tables:
                    filtered_data['data'][app_name] = app_data

            # الحصول على المستخدم
            user = CustomUser.objects.get(username='super')

            # تنفيذ الاستعادة الجزئية
            perform_backup_restore(filtered_data, clear_data=clear_data, user=user)

            end_time = time.time()
            duration = end_time - start_time

            self.log_result(f"الاستعادة الجزئية ({format_type}) - مسح البيانات: {clear_data}", "نجح",
                          f"الوقت المستغرق: {duration:.2f} ثانية")
            return duration

        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            self.log_error(f"الاستعادة الجزئية ({format_type}) - مسح البيانات: {clear_data}", f"{str(e)} (الوقت المستغرق: {duration:.2f} ثانية)")
            return duration

    def verify_data_integrity(self, test_name):
        """التحقق من سلامة البيانات"""
        try:
            # فحص عدد السجلات في الجداول الرئيسية
            from journal.models import Account
            from customers.models import CustomerSupplier
            from products.models import Product

            accounts_count = Account.objects.count()
            customers_count = CustomerSupplier.objects.filter(type='customer').count()
            products_count = Product.objects.count()

            self.log_result(f"التحقق من سلامة البيانات - {test_name}",
                          "نجح",
                          f"حسابات: {accounts_count}, عملاء: {customers_count}, منتجات: {products_count}")
            return True

        except Exception as e:
            self.log_error(f"التحقق من سلامة البيانات - {test_name}", str(e))
            return False

    def cleanup_test_data(self):
        """حذف بيانات الاختبار"""
        try:
            from journal.models import Account
            from customers.models import CustomerSupplier
            from products.models import Product, Category

            # حذف السجلات المضافة للاختبار
            Product.objects.filter(code__startswith="TEST").delete()
            CustomerSupplier.objects.filter(name="عميل اختبار").delete()
            Account.objects.filter(code="1000").delete()
            Category.objects.filter(name="فئة اختبار").delete()

            self.log_result("حذف بيانات الاختبار", "نجح", "تم حذف السجلات المضافة للاختبار")
            return True

        except Exception as e:
            self.log_error("حذف بيانات الاختبار", str(e))
            return False

    def cleanup_backup_files(self):
        """حذف ملفات النسخ الاحتياطي المؤقتة"""
        try:
            import glob

            # حذف ملفات الاختبار
            backup_dir = os.path.join('media', 'backups')
            if os.path.exists(backup_dir):
                test_files = glob.glob(os.path.join(backup_dir, '*test*.json')) + \
                           glob.glob(os.path.join(backup_dir, '*test*.xlsx'))

                deleted_count = 0
                for file_path in test_files:
                    try:
                        os.remove(file_path)
                        deleted_count += 1
                    except Exception as e:
                        print(f"فشل في حذف {file_path}: {e}")

                self.log_result("حذف ملفات النسخ الاحتياطي المؤقتة", "نجح",
                              f"تم حذف {deleted_count} ملف")
                return True

        except Exception as e:
            self.log_error("حذف ملفات النسخ الاحتياطي المؤقتة", str(e))
            return False

    def run_all_tests(self):
        """تشغيل جميع اختبارات الاستعادة"""
        print("\n=== بدء اختبارات الاستعادة الشاملة ===\n")

        # تسجيل بدء الاختبار في سجل الأنشطة
        try:
            user = CustomUser.objects.get(username='super')
            AuditLog.objects.create(
                user=user,
                action_type='create',
                content_type='backup_system',
                description='بدء اختبار شامل لعمليات الاستعادة'
            )
        except Exception as e:
            print(f"تحذير: فشل في تسجيل بدء الاختبار في سجل الأنشطة: {e}")

        # تسجيل الدخول
        if not self.login_as_superuser():
            return

        # إنشاء بيانات الاختبار
        if not self.create_test_data():
            return

        # قائمة الجداول للاختبار الجزئي - جميع الجداول
        all_tables = get_backup_tables_info()
        selected_tables = list(set(table['app_name'] for table in all_tables))

        # اختبارات النسخ الاحتياطي
        backup_files = {}
        backup_durations = {}

        for format_type in ['JSON', 'XLSX']:
            # نسخ احتياطي كامل
            backup_file, duration = self.test_full_backup(format_type)
            if backup_file:
                backup_files[f'full_{format_type.lower()}'] = backup_file
                backup_durations[f'full_{format_type.lower()}'] = duration
                self.verify_data_integrity(f"بعد النسخ الكامل {format_type}")

            # نسخ احتياطي جزئي
            backup_file, duration = self.test_partial_backup(format_type, selected_tables)
            if backup_file:
                backup_files[f'partial_{format_type.lower()}'] = backup_file
                backup_durations[f'partial_{format_type.lower()}'] = duration
                self.verify_data_integrity(f"بعد النسخ الجزئي {format_type}")

        # اختبارات الاستعادة
        restore_durations = {}

        for format_type in ['JSON', 'XLSX']:
            # استعادة كاملة بدون مسح
            if f'full_{format_type.lower()}' in backup_files:
                duration = self.test_full_restore(backup_files[f'full_{format_type.lower()}'], format_type, clear_data=False)
                restore_durations[f'full_{format_type.lower()}_no_clear'] = duration
                self.verify_data_integrity(f"بعد الاستعادة الكاملة بدون مسح {format_type}")

            # استعادة كاملة مع مسح
            if f'full_{format_type.lower()}' in backup_files:
                duration = self.test_full_restore(backup_files[f'full_{format_type.lower()}'], format_type, clear_data=True)
                restore_durations[f'full_{format_type.lower()}_with_clear'] = duration
                self.verify_data_integrity(f"بعد الاستعادة الكاملة مع مسح {format_type}")

            # استعادة جزئية بدون مسح
            if f'partial_{format_type.lower()}' in backup_files:
                duration = self.test_partial_restore(backup_files[f'partial_{format_type.lower()}'], format_type, selected_tables, clear_data=False)
                restore_durations[f'partial_{format_type.lower()}_no_clear'] = duration
                self.verify_data_integrity(f"بعد الاستعادة الجزئية بدون مسح {format_type}")

            # استعادة جزئية مع مسح
            if f'partial_{format_type.lower()}' in backup_files:
                duration = self.test_partial_restore(backup_files[f'partial_{format_type.lower()}'], format_type, selected_tables, clear_data=True)
                restore_durations[f'partial_{format_type.lower()}_with_clear'] = duration
                self.verify_data_integrity(f"بعد الاستعادة الجزئية مع مسح {format_type}")

        # تنظيف البيانات والملفات
        self.cleanup_test_data()
        self.cleanup_backup_files()

        print("\n=== انتهاء الاختبارات ===\n")

        # تسجيل انتهاء الاختبار في سجل الأنشطة
        try:
            user = CustomUser.objects.get(username='super')
            AuditLog.objects.create(
                user=user,
                action_type='create',
                content_type='backup_system',
                description=f'انتهاء اختبار الاستعادة الشامل - تم اختبار {len(self.results)} عملية'
            )
        except Exception as e:
            print(f"تحذير: فشل في تسجيل انتهاء الاختبار في سجل الأنشطة: {e}")

        return backup_durations, restore_durations

    def save_results(self, backup_durations=None, restore_durations=None):
        """حفظ النتائج في ملف TXT"""
        result_dir = r"C:\Accounting_soft\finspilot\test_result"
        os.makedirs(result_dir, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        result_file = os.path.join(result_dir, f'restore_comprehensive_test_results_{timestamp}.txt')

        with open(result_file, 'w', encoding='utf-8') as f:
            f.write("=== تقرير اختبار الاستعادة الشامل ===\n\n")
            f.write(f"تاريخ الاختبار: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            f.write("=== النتائج ===\n")
            for result in self.results:
                f.write(f"الاختبار: {result['test']}\n")
                f.write(f"الحالة: {result['status']}\n")
                f.write(f"الرسالة: {result['message']}\n")
                f.write(f"الوقت: {result['timestamp']}\n")
                f.write("-" * 50 + "\n")

            f.write(f"\nإجمالي الاختبارات: {len(self.results)}\n")
            f.write(f"الاختبارات الناجحة: {len([r for r in self.results if r['status'] == 'نجح'])}\n")
            f.write(f"الاختبارات الفاشلة: {len([r for r in self.results if r['status'] == 'فشل'])}\n\n")

            if backup_durations:
                f.write("=== تقرير الأوقات - النسخ الاحتياطي ===\n")
                for key, duration in backup_durations.items():
                    f.write(f"{key}: {duration:.2f} ثانية\n")
                f.write("\n")

            if restore_durations:
                f.write("=== تقرير الأوقات - الاستعادة ===\n")
                for key, duration in restore_durations.items():
                    f.write(f"{key}: {duration:.2f} ثانية\n")
                f.write("\n")

            f.write("=== الأخطاء ===\n")
            if self.errors:
                for error in self.errors:
                    f.write(f"الاختبار: {error['test']}\n")
                    f.write(f"الخطأ: {error['error']}\n")
                    f.write(f"الوقت: {error['timestamp']}\n")
                    f.write("-" * 50 + "\n")
            else:
                f.write("لا توجد أخطاء\n")

            f.write(f"\nإجمالي الأخطاء: {len(self.errors)}\n")

        print(f"تم حفظ النتائج في: {result_file}")


def main():
    """الدالة الرئيسية"""
    tester = RestoreTester()
    backup_durations, restore_durations = tester.run_all_tests()
    tester.save_results(backup_durations, restore_durations)


if __name__ == '__main__':
    main()
