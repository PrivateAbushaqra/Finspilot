#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
اختبار وظيفة الاستعادة في واجهة المستخدم
اختبار شامل للتأكد من عمل زر الاستعادة وخيار مسح البيانات بشكل صحيح
"""

import os
import sys
import json
import time
import requests
from datetime import datetime
from pathlib import Path

# إضافة مجلد المشروع إلى المسار
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
import django
django.setup()

from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from backup.views import perform_backup_restore, load_backup_from_xlsx
import openpyxl

class RestoreUITester:
    """فئة لاختبار وظيفة الاستعادة في الواجهة"""

    def __init__(self):
        self.client = Client()
        self.base_url = 'http://127.0.0.1:8000'
        self.session = requests.Session()
        self.test_results = []
        self.backup_files = [
            'backup_20250927_091459.json',
            'backup_20250927_091623.xlsx'
        ]

    def login(self):
        """تسجيل الدخول للحصول على الجلسة"""
        try:
            # الحصول على نموذج المستخدم
            User = get_user_model()

            # إنشاء مستخدم اختبار إذا لم يكن موجوداً
            test_user, created = User.objects.get_or_create(
                username='test_restore_user',
                defaults={
                    'email': 'test@example.com',
                    'is_staff': True,
                    'is_superuser': True
                }
            )

            if created:
                test_user.set_password('testpass123')
                test_user.save()
                print("✅ تم إنشاء مستخدم اختبار")

            # تسجيل الدخول مباشرة باستخدام requests
            login_url = f"{self.base_url}/ar/accounts/login/"

            # الحصول على صفحة تسجيل الدخول أولاً للحصول على CSRF token
            response = self.session.get(login_url)
            if 'csrfmiddlewaretoken' in response.text:
                import re
                csrf_match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', response.text)
                if csrf_match:
                    csrf_token = csrf_match.group(1)
                else:
                    raise Exception("لم يتم العثور على CSRF token في صفحة تسجيل الدخول")
            else:
                raise Exception("لم يتم العثور على CSRF token في صفحة تسجيل الدخول")

            # إرسال بيانات تسجيل الدخول
            login_data = {
                'username': 'test_restore_user',
                'password': 'testpass123',
                'csrfmiddlewaretoken': csrf_token
            }

            headers = {
                'Referer': login_url
            }

            response = self.session.post(login_url, data=login_data, headers=headers)

            if response.status_code == 200 and 'login' not in response.url.lower():
                print("✅ تم تسجيل الدخول بنجاح")
                return True
            else:
                raise Exception(f"فشل في تسجيل الدخول - HTTP {response.status_code}")

        except Exception as e:
            print(f"❌ خطأ في تسجيل الدخول: {str(e)}")
            return False

    def get_backup_file_info(self, filename):
        """الحصول على معلومات ملف النسخة الاحتياطي"""
        backup_dir = BASE_DIR / 'media' / 'backups'
        filepath = backup_dir / filename

        if not filepath.exists():
            raise Exception(f"ملف النسخة الاحتياطي غير موجود: {filename}")

        file_size = filepath.stat().st_size
        file_format = 'xlsx' if filename.endswith('.xlsx') else 'json'

        return {
            'filename': filename,
            'filepath': str(filepath),
            'format': file_format,
            'size': file_size
        }

    def count_database_records(self):
        """عد السجلات في قاعدة البيانات قبل وبعد الاستعادة"""
        from django.apps import apps

        record_counts = {}
        excluded_apps = [
            'django.contrib.admin',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django.contrib.messages',
            'django.contrib.staticfiles',
            'corsheaders',
            'rest_framework',
            'django_bootstrap5',
            'crispy_forms',
            'crispy_bootstrap5',
        ]

        for app_config in apps.get_app_configs():
            if app_config.name in excluded_apps:
                continue

            for model in app_config.get_models():
                if getattr(model._meta, 'managed', True) is False:
                    continue

                try:
                    count = model.objects.count()
                    key = f"{app_config.name}.{model._meta.model_name}"
                    record_counts[key] = count
                except Exception as e:
                    print(f"⚠️ خطأ في عد السجلات لـ {app_config.name}.{model._meta.model_name}: {str(e)}")

        return record_counts

    def test_restore_operation(self, filename, clear_data=False):
        """اختبار عملية الاستعادة"""
        print(f"\n🔄 اختبار الاستعادة: {filename} (مسح البيانات: {clear_data})")

        start_time = time.time()

        try:
            # الحصول على معلومات الملف
            file_info = self.get_backup_file_info(filename)

            # عد السجلات قبل الاستعادة
            records_before = self.count_database_records()
            total_before = sum(records_before.values())

            print(f"📊 السجلات قبل الاستعادة: {total_before:,}")

            # إرسال طلب الاستعادة
            url = f"{self.base_url}/ar/backup/restore-backup/"

            # الحصول على CSRF token من صفحة النسخ الاحتياطي
            page_response = self.session.get(f"{self.base_url}/ar/backup/")
            if 'csrfmiddlewaretoken' in page_response.text:
                import re
                csrf_match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', page_response.text)
                if csrf_match:
                    csrf_token = csrf_match.group(1)
                else:
                    raise Exception("لم يتم العثور على CSRF token")
            else:
                raise Exception("لم يتم العثور على CSRF token في الصفحة")

            # إعداد البيانات للاستعادة
            with open(file_info['filepath'], 'rb') as f:
                files = {'backup_file': (filename, f, 'application/octet-stream')}
                data = {
                    'csrfmiddlewaretoken': csrf_token,
                    'clear_data': 'on' if clear_data else ''
                }

                headers = {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Referer': f"{self.base_url}/ar/backup/"
                }

                response = self.session.post(url, files=files, data=data, headers=headers)

            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}: {response.text}")

            result = response.json()

            if not result.get('success'):
                raise Exception(f"فشل في الاستعادة: {result.get('error', 'خطأ غير معروف')}")

            print("✅ تم بدء عملية الاستعادة بنجاح")

            # انتظار انتهاء العملية
            self.wait_for_restore_completion()

            # عد السجلات بعد الاستعادة
            records_after = self.count_database_records()
            total_after = sum(records_after.values())

            print(f"📊 السجلات بعد الاستعادة: {total_after:,}")

            # التحقق من الاستعادة
            self.verify_restore_success(file_info, records_before, records_after, clear_data)

            duration = time.time() - start_time

            self.test_results.append({
                'test': f'استعادة {file_info["format"].upper()} (مسح: {clear_data})',
                'status': 'نجح',
                'duration': f"{duration:.2f} ثانية",
                'filename': filename,
                'records_before': total_before,
                'records_after': total_after,
                'clear_data': clear_data,
                'details': f"تمت الاستعادة بنجاح - السجلات: {total_before:,} → {total_after:,}"
            })

            return True

        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"فشل في اختبار الاستعادة: {str(e)}"
            print(f"❌ {error_msg}")

            self.test_results.append({
                'test': f'استعادة {filename} (مسح: {clear_data})',
                'status': 'فشل',
                'duration': f"{duration:.2f} ثانية",
                'error': str(e),
                'clear_data': clear_data,
                'details': error_msg
            })

            return False

    def wait_for_restore_completion(self, timeout=300):
        """انتظار انتهاء عملية الاستعادة"""
        print("⏳ انتظار انتهاء عملية الاستعادة...")

        start_time = time.time()
        url = f"{self.base_url}/ar/backup/restore-progress/"

        while time.time() - start_time < timeout:
            try:
                response = self.session.get(url)
                if response.status_code == 200:
                    progress = response.json().get('progress', {})
                    if not progress.get('is_running', False):
                        if progress.get('status') == 'completed':
                            print("✅ انتهت عملية الاستعادة بنجاح")
                            return True
                        elif progress.get('status') == 'error':
                            raise Exception(f"خطأ في الاستعادة: {progress.get('error', 'خطأ غير معروف')}")
                        else:
                            print(f"⚠️ انتهت العملية بحالة: {progress.get('status')}")
                            return True

                    # طباعة التقدم
                    percentage = progress.get('percentage', 0)
                    current_table = progress.get('current_table', '')
                    if percentage > 0:
                        print(f"📊 التقدم: {percentage}% - {current_table}")

                time.sleep(2)

            except Exception as e:
                print(f"⚠️ خطأ في مراقبة التقدم: {str(e)}")
                time.sleep(2)

        raise Exception(f"انتهت مهلة الانتظار ({timeout} ثانية)")

    def verify_restore_success(self, file_info, records_before, records_after, clear_data):
        """التحقق من نجاح عملية الاستعادة"""
        print("🔍 التحقق من نجاح الاستعادة...")

        # قراءة محتوى ملف النسخة الاحتياطي
        if file_info['format'] == 'json':
            with open(file_info['filepath'], 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
        elif file_info['format'] == 'xlsx':
            backup_data = load_backup_from_xlsx(open(file_info['filepath'], 'rb'))
        else:
            raise Exception(f"تنسيق غير مدعوم: {file_info['format']}")

        # عد السجلات المتوقعة في النسخة الاحتياطية
        expected_records = 0
        for app_name, app_data in backup_data.get('data', {}).items():
            for model_name, model_data in app_data.items():
                if isinstance(model_data, list):
                    expected_records += len(model_data)

        print(f"📊 السجلات المتوقعة في النسخة الاحتياطية: {expected_records:,}")

        # التحقق من النتائج
        total_before = sum(records_before.values())
        total_after = sum(records_after.values())

        if clear_data:
            # إذا تم مسح البيانات، يجب أن تكون السجلات بعد الاستعادة مساوية للسجلات في النسخة الاحتياطية
            if abs(total_after - expected_records) > 10:  # هامش خطأ صغير
                raise Exception(f"عدم تطابق في عدد السجلات بعد مسح البيانات. متوقع: {expected_records}, فعلي: {total_after}")
            print("✅ تم مسح البيانات واستعادتها بشكل صحيح")
        else:
            # إذا لم يتم مسح البيانات، يجب أن تكون السجلات بعد الاستعادة أكبر أو مساوية
            if total_after < total_before:
                raise Exception(f"انخفاض في عدد السجلات بعد الاستعادة بدون مسح. قبل: {total_before}, بعد: {total_after}")
            print("✅ تمت إضافة البيانات بدون مسح البيانات الموجودة")

        print("✅ تم التحقق من نجاح الاستعادة")

    def run_all_tests(self):
        """تشغيل جميع اختبارات الاستعادة"""
        print("🚀 بدء اختبار وظيفة الاستعادة في الواجهة")
        print("=" * 60)

        # تسجيل الدخول
        if not self.login():
            print("❌ فشل في تسجيل الدخول - إيقاف الاختبار")
            return False

        # اختبار الاستعادة لكل ملف
        for filename in self.backup_files:
            # اختبار بدون مسح البيانات
            self.test_restore_operation(filename, clear_data=False)

            # انتظار قليل بين الاختبارات
            time.sleep(10)

            # اختبار مع مسح البيانات
            self.test_restore_operation(filename, clear_data=True)

            # انتظار أطول بين الملفات
            time.sleep(15)

        # ملخص النتائج
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['status'] == 'نجح'])
        failed_tests = total_tests - passed_tests

        print("\n" + "=" * 60)
        print("📊 ملخص نتائج الاختبار:")
        print(f"إجمالي الاختبارات: {total_tests}")
        print(f"الناجحة: {passed_tests}")
        print(f"الفاشلة: {failed_tests}")

        if failed_tests == 0:
            print("✅ جميع اختبارات الاستعادة نجحت!")
        else:
            print("❌ فشل في بعض الاختبارات")

        return failed_tests == 0

    def save_results(self):
        """حفظ نتائج الاختبار في ملف TXT"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"ui_restore_test_results_{timestamp}.txt"
        filepath = BASE_DIR / 'test_result' / filename

        # التأكد من وجود مجلد test_result
        filepath.parent.mkdir(exist_ok=True)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("اختبار وظيفة الاستعادة في الواجهة\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"تاريخ الاختبار: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"الخادم: {self.base_url}\n\n")

            # إحصائيات عامة
            total_tests = len(self.test_results)
            passed_tests = len([r for r in self.test_results if r['status'] == 'نجح'])
            failed_tests = total_tests - passed_tests

            f.write("إحصائيات الاختبار:\n")
            f.write(f"- إجمالي الاختبارات: {total_tests}\n")
            f.write(f"- الناجحة: {passed_tests}\n")
            f.write(f"- الفاشلة: {failed_tests}\n\n")

            # تفاصيل كل اختبار
            f.write("تفاصيل الاختبارات:\n")
            f.write("-" * 40 + "\n")

            for result in self.test_results:
                f.write(f"\nاختبار: {result['test']}\n")
                f.write(f"الحالة: {result['status']}\n")
                f.write(f"المدة: {result['duration']}\n")

                if 'filename' in result:
                    f.write(f"الملف: {result['filename']}\n")
                if 'records_before' in result:
                    f.write(f"السجلات قبل: {result['records_before']:,}\n")
                if 'records_after' in result:
                    f.write(f"السجلات بعد: {result['records_after']:,}\n")
                if 'clear_data' in result:
                    f.write(f"مسح البيانات: {'نعم' if result['clear_data'] else 'لا'}\n")
                if 'error' in result:
                    f.write(f"الخطأ: {result['error']}\n")

                f.write(f"التفاصيل: {result['details']}\n")
                f.write("-" * 40 + "\n")

        print(f"💾 تم حفظ النتائج في: {filepath}")
        return str(filepath)


def main():
    """الدالة الرئيسية"""
    tester = RestoreUITester()

    try:
        success = tester.run_all_tests()
        results_file = tester.save_results()

        print(f"\n📄 تم حفظ تفاصيل النتائج في: {results_file}")

        if success:
            print("🎉 جميع اختبارات الاستعادة نجحت!")
            return 0
        else:
            print("⚠️ فشل في بعض الاختبارات")
            return 1

    except Exception as e:
        print(f"❌ خطأ عام في الاختبار: {str(e)}")
        return 1


if __name__ == '__main__':
    sys.exit(main())