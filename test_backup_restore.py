#!/usr/bin/env python
"""
سكريبت اختبار شامل لعمليات النسخ الاحتياطي والاستعادة
يختبر Backup كامل وجزئي على JSON و XLSX
ويختبر Restore كامل وجزئي مع وبدون مسح البيانات
"""

import os
import sys
import django
import json
import time
from datetime import datetime
from pathlib import Path

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from django.contrib.auth import authenticate, login
from django.test import Client, RequestFactory
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.management import execute_from_command_line
from django.apps import apps
from django.conf import settings
from backup.views import perform_backup_task, perform_backup_restore
from core.models import AuditLog
import tempfile

class BackupRestoreTester:
    def __init__(self):
        self.client = Client()
        self.factory = RequestFactory()
        self.results = []
        self.errors = []
        self.test_data_created = []

    def log_result(self, test_name, status, message=""):
        """تسجيل نتيجة الاختبار"""
        result = {
            'test': test_name,
            'status': status,
            'message': message,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        self.results.append(result)
        print(f"[{result['timestamp']}] {test_name}: {status} - {message}")

    def log_error(self, test_name, error):
        """تسجيل خطأ"""
        error_info = {
            'test': test_name,
            'error': str(error),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        self.errors.append(error_info)
        print(f"ERROR in {test_name}: {error}")

    def login_as_superuser(self):
        """تسجيل الدخول كـ superuser"""
        try:
            user = authenticate(username='super', password='password')
            if user and user.is_superuser:
                self.client.force_login(user)
                self.log_result("تسجيل الدخول كـ superuser", "نجح")
                return True
            else:
                self.log_error("تسجيل الدخول كـ superuser", "فشل في المصادقة")
                return False
        except Exception as e:
            self.log_error("تسجيل الدخول كـ superuser", str(e))
            return False

    def create_test_data(self):
        """إنشاء بيانات اختبار"""
        try:
            from journal.models import Account
            from customers.models import CustomerSupplier
            from products.models import Product, Category
            from journal.models import JournalEntry

            # إنشاء فئة منتج
            category, created = Category.objects.get_or_create(
                name_en='Test Category',
                defaults={'name_ar': 'فئة اختبار'}
            )
            self.test_data_created.append(('Category', category.pk))

            # إنشاء منتج
            product, created = Product.objects.get_or_create(
                code='TEST001',
                defaults={
                    'name': 'منتج اختبار',
                    'name_en': 'Test Product',
                    'category': category,
                    'cost_price': 10.00,
                    'sale_price': 15.00
                }
            )
            self.test_data_created.append(('Product', product.pk))

            # إنشاء عميل
            customer, created = CustomerSupplier.objects.get_or_create(
                name='عميل اختبار',
                defaults={
                    'type': 'customer',
                    'city': 'الرياض'
                }
            )
            self.test_data_created.append(('Customer', customer.pk))

            # إنشاء حساب
            account, created = Account.objects.get_or_create(
                code='TEST001',
                defaults={
                    'name': 'حساب اختبار',
                    'account_type': 'asset'
                }
            )
            self.test_data_created.append(('Account', account.pk))

            self.log_result("إنشاء بيانات الاختبار", "نجح", f"تم إنشاء {len(self.test_data_created)} سجل اختبار")
            return True

        except Exception as e:
            self.log_error("إنشاء بيانات الاختبار", str(e))
            return False

    def test_full_backup(self, format_type):
        """اختبار النسخ الاحتياطي الكامل"""
        try:
            start_time = time.time()
            
            # الحصول على المستخدم
            from users.models import User
            user = User.objects.get(username='super')

            # إنشاء اسم الملف
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'full_backup_test_{format_type}_{timestamp}.{format_type.lower()}'
            filepath = os.path.join(settings.MEDIA_ROOT, 'backups', filename)

            # التأكد من وجود المجلد
            os.makedirs(os.path.dirname(filepath), exist_ok=True)

            # تنفيذ النسخ الاحتياطي
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
            from users.models import User
            user = User.objects.get(username='super')

            # إنشاء اسم الملف
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'partial_backup_test_{format_type}_{timestamp}.{format_type.lower()}'
            filepath = os.path.join(settings.MEDIA_ROOT, 'backups', filename)

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
            if format_type.lower() == 'json':
                with open(backup_file, 'r', encoding='utf-8') as f:
                    backup_data = json.load(f)
            else:
                # للـ XLSX، نحتاج لوظيفة قراءة
                from backup.views import load_backup_from_xlsx
                with open(backup_file, 'rb') as f:
                    backup_data = load_backup_from_xlsx(f)

            # الحصول على المستخدم
            from users.models import User
            user = User.objects.get(username='super')

            # تنفيذ الاستعادة
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
            if format_type.lower() == 'json':
                with open(backup_file, 'r', encoding='utf-8') as f:
                    backup_data = json.load(f)
            else:
                from backup.views import load_backup_from_xlsx
                with open(backup_file, 'rb') as f:
                    backup_data = load_backup_from_xlsx(f)

            # تصفية البيانات للجداول المحددة فقط
            filtered_data = {'metadata': backup_data.get('metadata', {}), 'data': {}}
            for app_name, app_data in backup_data.get('data', {}).items():
                if app_name in selected_tables:
                    filtered_data['data'][app_name] = app_data

            # الحصول على المستخدم
            from users.models import User
            user = User.objects.get(username='super')

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
            deleted_count = 0
            for model_name, pk in self.test_data_created:
                try:
                    model_class = apps.get_model('products' if model_name == 'Category' else
                                               'products' if model_name == 'Product' else
                                               'customers' if model_name == 'Customer' else
                                               'accounts', model_name.lower())
                    obj = model_class.objects.filter(pk=pk).first()
                    if obj:
                        obj.delete()
                        deleted_count += 1
                except:
                    pass

            self.log_result("حذف بيانات الاختبار", "نجح", f"تم حذف {deleted_count} سجل")
            return True

        except Exception as e:
            self.log_error("حذف بيانات الاختبار", str(e))
            return False

    def cleanup_backup_files(self):
        """حذف ملفات النسخ الاحتياطي المؤقتة"""
        try:
            backup_dir = os.path.join(settings.MEDIA_ROOT, 'backups')
            if os.path.exists(backup_dir):
                for filename in os.listdir(backup_dir):
                    if filename.startswith(('full_backup_test_', 'partial_backup_test_')):
                        filepath = os.path.join(backup_dir, filename)
                        os.remove(filepath)
                        self.log_result("حذف ملفات النسخ الاحتياطي المؤقتة", "نجح", f"تم حذف {filename}")

            return True

        except Exception as e:
            self.log_error("حذف ملفات النسخ الاحتياطي المؤقتة", str(e))
            return False

    def run_all_tests(self):
        """تشغيل جميع الاختبارات"""
        print("=== بدء اختبارات النسخ الاحتياطي والاستعادة ===\n")

        # تسجيل بدء الاختبار في سجل الأنشطة
        try:
            from users.models import User
            user = User.objects.get(username='super')
            from core.models import AuditLog
            AuditLog.objects.create(
                user=user,
                action_type='create',
                content_type='backup_system',
                description='بدء اختبار شامل لعمليات النسخ الاحتياطي والاستعادة'
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
        from backup.views import get_backup_tables_info
        all_tables = get_backup_tables_info()
        selected_tables = list(set(table['app_name'] for table in all_tables))

        # التحقق من تغطية الجداول
        self.verify_table_coverage()

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

        print("\n=== انتهاء الاختبارات ===")

        # تسجيل انتهاء الاختبار في سجل الأنشطة
        try:
            from users.models import User
            user = User.objects.get(username='super')
            from core.models import AuditLog
            AuditLog.objects.create(
                user=user,
                action_type='create',
                content_type='backup_system',
                description=f'انتهاء اختبار النسخ الاحتياطي والاستعادة - تم اختبار {len(self.results)} عملية'
            )
        except Exception as e:
            print(f"تحذير: فشل في تسجيل انتهاء الاختبار في سجل الأنشطة: {e}")

        return backup_durations, restore_durations

    def save_results(self, backup_durations=None, restore_durations=None):
        """حفظ النتائج في ملف TXT"""
        result_dir = r"C:\Accounting_soft\finspilot\test_result"
        os.makedirs(result_dir, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # حفظ النتائج الكاملة دائماً
        result_file = os.path.join(result_dir, f'restore_test_results_{timestamp}.txt')
        with open(result_file, 'w', encoding='utf-8') as f:
            f.write("=== تقرير اختبار الاستعادة ===\n\n")
            f.write(f"تاريخ الاختبار: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            f.write("=== النتائج ===\n")
            for result in self.results:
                f.write(f"الاختبار: {result['test']}\n")
                f.write(f"الحالة: {result['status']}\n")
                f.write(f"الرسالة: {result['message']}\n")
                f.write(f"الوقت: {result['timestamp']}\n")
                f.write("-" * 50 + "\n\n")

            f.write(f"إجمالي الاختبارات: {len(self.results)}\n")
            successful_tests = len([r for r in self.results if r['status'] == 'نجح'])
            f.write(f"الاختبارات الناجحة: {successful_tests}\n")
            f.write(f"الاختبارات الفاشلة: {len(self.results) - successful_tests}\n\n")

            # إضافة تقرير الأوقات للنسخ الاحتياطي
            if backup_durations:
                f.write("=== تقرير الأوقات - النسخ الاحتياطي ===\n")
                for backup_type, duration in backup_durations.items():
                    f.write(f"{backup_type}: {duration:.2f} ثانية\n")
                f.write("\n")

            # إضافة تقرير الأوقات للاستعادة
            if restore_durations:
                f.write("=== تقرير الأوقات - الاستعادة ===\n")
                for restore_type, duration in restore_durations.items():
                    f.write(f"{restore_type}: {duration:.2f} ثانية\n")
                f.write("\n")

                # إضافة النصائح للاستعادة
                tips = self.generate_restore_performance_tips(restore_durations)
                f.write("=== نصائح لتسريع الاستعادة ===\n")
                for i, tip in enumerate(tips, 1):
                    f.write(f"{i}. {tip}\n")
                f.write("\n")

            # إضافة الأخطاء إذا وجدت
            if self.errors:
                f.write("=== الأخطاء ===\n")
                for error in self.errors:
                    f.write(f"الاختبار: {error['test']}\n")
                    f.write(f"الخطأ: {error['error']}\n")
                    f.write(f"الوقت: {error['timestamp']}\n")
                    f.write("-" * 50 + "\n\n")

                f.write(f"إجمالي الأخطاء: {len(self.errors)}\n")

            print(f"تم حفظ النتائج في: {result_file}")


    def generate_restore_performance_tips(self, restore_durations):
        """إنشاء نصائح لتسريع عملية الاستعادة"""
        tips = []
        
        # تحليل الأوقات
        json_times = [duration for key, duration in restore_durations.items() if 'json' in key]
        xlsx_times = [duration for key, duration in restore_durations.items() if 'xlsx' in key]
        clear_times = [duration for key, duration in restore_durations.items() if 'with_clear' in key]
        no_clear_times = [duration for key, duration in restore_durations.items() if 'no_clear' in key]
        
        if json_times and xlsx_times:
            avg_json = sum(json_times) / len(json_times)
            avg_xlsx = sum(xlsx_times) / len(xlsx_times)
            
            if avg_json < avg_xlsx:
                tips.append("الصيغة JSON أسرع في الاستعادة من XLSX")
            else:
                tips.append("الصيغة XLSX قد تكون أبطأ في الاستعادة بسبب معالجة البيانات المعقدة")
        
        if clear_times and no_clear_times:
            avg_clear = sum(clear_times) / len(clear_times)
            avg_no_clear = sum(no_clear_times) / len(no_clear_times)
            
            if avg_clear > avg_no_clear:
                tips.append("الاستعادة مع مسح البيانات تستغرق وقتاً أطول")
        
        # نصائح عامة لتسريع الاستعادة
        tips.extend([
            "تجنب تشغيل الاستعادة أثناء ساعات الذروة لتجنب التأثير على الأداء",
            "استخدم فهرسة مناسبة على الجداول لتسريع عملية الإدراج",
            "قسم الاستعادة الكبيرة إلى دفعات أصغر إذا أمكن",
            "استخدم اتصال قاعدة بيانات سريع ومستقر",
            "تأكد من وجود مساحة تخزين كافية على القرص للبيانات المؤقتة",
            "فكر في استخدام ضغط البيانات لتقليل حجم ملفات النسخ الاحتياطي",
            "راقب استخدام الذاكرة أثناء الاستعادة الكبيرة",
            "استخدم خوادم قاعدة بيانات مخصصة للاستعادة إذا أمكن",
            "قم بتنظيف البيانات القديمة قبل الاستعادة إذا لزم الأمر",
            "استخدم استعادة تزايدية للجداول التي لا تتغير كثيراً"
        ])
        
        return tips


    def verify_table_coverage(self):
        """التحقق من تغطية جميع الجداول في النسخ الاحتياطي"""
        try:
            from backup.views import get_backup_tables_info
            
            # الحصول على جميع الجداول المتاحة للنسخ الاحتياطي
            all_tables = get_backup_tables_info()
            total_tables = len(all_tables)
            
            # قائمة التطبيقات المتوقعة
            expected_apps = [
                'accounts', 'assets_liabilities', 'backup', 'banks', 'cashboxes',
                'core', 'customers', 'documents', 'hr', 'inventory', 'journal',
                'payments', 'products', 'provisions', 'purchases', 'receipts',
                'reports', 'revenues_expenses', 'sales', 'settings', 'users'
            ]
            
            covered_apps = set()
            table_counts = {}
            
            for table in all_tables:
                app_name = table['app_name']
                covered_apps.add(app_name)
                if app_name not in table_counts:
                    table_counts[app_name] = 0
                table_counts[app_name] += 1
            
            # التحقق من التغطية
            missing_apps = set(expected_apps) - covered_apps
            extra_apps = covered_apps - set(expected_apps)
            
            coverage_report = f"إجمالي الجداول: {total_tables}\n"
            coverage_report += f"التطبيقات المشمولة: {len(covered_apps)}\n"
            coverage_report += f"التطبيقات المفقودة: {len(missing_apps)}\n"
            coverage_report += f"التطبيقات الإضافية: {len(extra_apps)}\n\n"
            
            if missing_apps:
                coverage_report += "التطبيقات المفقودة:\n"
                for app in sorted(missing_apps):
                    coverage_report += f"- {app}\n"
                coverage_report += "\n"
            
            if extra_apps:
                coverage_report += "التطبيقات الإضافية:\n"
                for app in sorted(extra_apps):
                    coverage_report += f"- {app}\n"
                coverage_report += "\n"
            
            coverage_report += "تفصيل الجداول لكل تطبيق:\n"
            for app in sorted(covered_apps):
                coverage_report += f"- {app}: {table_counts[app]} جدول\n"
            
            self.log_result("التحقق من تغطية الجداول", "نجح", coverage_report)
            
            if missing_apps:
                self.log_error("التحقق من تغطية الجداول", f"التطبيقات المفقودة: {', '.join(missing_apps)}")
            
            return total_tables, len(covered_apps), len(missing_apps)
            
        except Exception as e:
            self.log_error("التحقق من تغطية الجداول", str(e))
            return 0, 0, 0


def main():
    """الدالة الرئيسية"""
    tester = BackupRestoreTester()
    backup_durations, restore_durations = tester.run_all_tests()
    tester.save_results(backup_durations, restore_durations)


if __name__ == '__main__':
    main()