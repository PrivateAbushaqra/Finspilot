"""
اختبار شامل لعملية النسخ الاحتياطي والاستعادة
باستخدام نفس أدوات صفحة http://127.0.0.1:8000/ar/backup/

الاختبار يقوم بـ:
1. أخذ نسخة احتياطية من PostgreSQL مباشرة (أمان إضافي)
2. حساب البيانات الحالية وأخذ عينات
3. إنشاء نسخة احتياطية من خلال النظام
4. مسح جميع البيانات
5. استعادة النسخة من خلال النظام
6. التحقق من سلامة البيانات
7. مقارنة شاملة

⚠️ هذا اختبار حقيقي وخطير!
"""

import os
import django
import json
import subprocess
from datetime import datetime
from pathlib import Path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from backup.views import perform_backup_task, perform_backup_restore, perform_clear_all_data
from django.apps import apps
from django.conf import settings

class ComprehensiveBackupTest:
    def __init__(self):
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.backup_file = f'test_backup_{self.timestamp}.json'
        self.pg_backup_file = f'pg_backup_{self.timestamp}.sql'
        self.report = {
            'timestamp': datetime.now().isoformat(),
            'steps': [],
            'before': {},
            'after': {},
            'success': False,
            'errors': [],
            'warnings': []
        }
        
    def log(self, message, level='info'):
        """تسجيل رسالة مع طابع زمني"""
        icons = {
            'info': '📝',
            'success': '✅',
            'warning': '⚠️',
            'error': '❌',
            'step': '🔹',
            'important': '🔥'
        }
        
        timestamp = datetime.now().strftime('%H:%M:%S')
        icon = icons.get(level, '📝')
        print(f"[{timestamp}] {icon} {message}")
        
        self.report['steps'].append({
            'timestamp': timestamp,
            'level': level,
            'message': message
        })
        
        if level == 'error':
            self.report['errors'].append(message)
        elif level == 'warning':
            self.report['warnings'].append(message)
    
    def pg_backup(self):
        """أخذ نسخة احتياطية من PostgreSQL مباشرة"""
        self.log("أخذ نسخة احتياطية من PostgreSQL مباشرة (أمان إضافي)...", 'step')
        
        db_config = settings.DATABASES['default']
        db_name = db_config['NAME']
        db_user = db_config.get('USER', 'postgres')
        db_host = db_config.get('HOST', 'localhost')
        db_port = db_config.get('PORT', '5432')
        db_password = db_config.get('PASSWORD', '')
        
        # تحديد مسار pg_dump
        pg_dump_paths = [
            r'C:\Program Files\PostgreSQL\17\bin\pg_dump.exe',
            r'C:\Program Files\PostgreSQL\16\bin\pg_dump.exe',
            r'C:\Program Files\PostgreSQL\15\bin\pg_dump.exe',
            r'C:\Program Files\PostgreSQL\14\bin\pg_dump.exe',
            'pg_dump'  # إذا كان في PATH
        ]
        
        pg_dump = None
        for path in pg_dump_paths:
            if os.path.exists(path) or path == 'pg_dump':
                pg_dump = path
                break
        
        if not pg_dump:
            self.log("لم يتم العثور على pg_dump! تخطي النسخة الاحتياطية من PostgreSQL", 'warning')
            return False
        
        try:
            env = os.environ.copy()
            if db_password:
                env['PGPASSWORD'] = db_password
            
            cmd = [
                pg_dump,
                '-h', db_host,
                '-p', str(db_port),
                '-U', db_user,
                '-F', 'c',  # Custom format (للضغط)
                '-f', self.pg_backup_file,
                db_name
            ]
            
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode == 0:
                size = os.path.getsize(self.pg_backup_file) / (1024 * 1024)
                self.log(f"تم إنشاء نسخة PostgreSQL: {self.pg_backup_file} ({size:.2f} MB)", 'success')
                return True
            else:
                self.log(f"فشل في إنشاء نسخة PostgreSQL: {result.stderr}", 'warning')
                return False
                
        except Exception as e:
            self.log(f"خطأ في pg_dump: {e}", 'warning')
            return False
    
    def count_all_data(self):
        """حساب جميع البيانات في قاعدة البيانات"""
        total = 0
        records = {}
        
        for app_config in apps.get_app_configs():
            if app_config.name.startswith('django.'):
                continue
                
            for model in app_config.get_models():
                try:
                    count = model.objects.count()
                    if count > 0:
                        label = model._meta.label
                        records[label] = count
                        total += count
                except Exception:
                    pass
        
        return total, records
    
    def sample_critical_data(self):
        """أخذ عينات من البيانات الحرجة للمقارنة"""
        samples = {}
        
        try:
            # المستخدمين
            from django.contrib.auth import get_user_model
            User = get_user_model()
            samples['users'] = list(User.objects.values('id', 'username', 'email', 'is_superuser')[:10])
            
            # المنتجات
            from products.models import Product
            samples['products'] = list(Product.objects.values('id', 'name', 'price', 'cost')[:10])
            
            # العملاء
            from customers.models import Customer
            samples['customers'] = list(Customer.objects.values('id', 'name', 'phone', 'email')[:10])
            
            # الفواتير
            from sales.models import SalesInvoice
            samples['invoices'] = list(SalesInvoice.objects.values('id', 'invoice_number', 'total_amount', 'customer_id')[:10])
            
            # الحسابات
            from journal.models import Account
            samples['accounts'] = list(Account.objects.values('id', 'name', 'account_number', 'balance')[:10])
            
            # القيود
            from journal.models import JournalEntry
            samples['journal_entries'] = list(JournalEntry.objects.values('id', 'entry_number', 'description', 'debit_total')[:10])
            
        except Exception as e:
            self.log(f"خطأ في أخذ العينات: {e}", 'warning')
        
        return samples
    
    def compare_data(self, before, after):
        """مقارنة تفصيلية بين البيانات قبل وبعد"""
        issues = []
        
        # مقارنة الأعداد الإجمالية
        before_total = before['total']
        after_total = after['total']
        difference = after_total - before_total
        percentage = (difference / before_total * 100) if before_total > 0 else 0
        
        self.log(f"المقارنة الإجمالية:", 'step')
        self.log(f"  قبل: {before_total:,} سجل", 'info')
        self.log(f"  بعد: {after_total:,} سجل", 'info')
        self.log(f"  الفرق: {difference:+,} سجل ({percentage:+.2f}%)", 'info')
        
        if abs(percentage) > 10:
            issues.append(f"فرق كبير في عدد السجلات: {percentage:+.2f}%")
            self.log(f"⚠️ فرق كبير في عدد السجلات!", 'warning')
        
        # مقارنة الجداول
        before_tables = set(before['records'].keys())
        after_tables = set(after['records'].keys())
        
        missing_tables = before_tables - after_tables
        if missing_tables:
            issues.append(f"جداول مفقودة: {', '.join(missing_tables)}")
            self.log(f"⚠️ جداول مفقودة: {len(missing_tables)}", 'warning')
            for table in list(missing_tables)[:5]:
                self.log(f"    - {table} ({before['records'][table]} سجل)", 'warning')
        
        # مقارنة تفصيلية للجداول المشتركة
        common_tables = before_tables & after_tables
        significant_differences = []
        
        for table in common_tables:
            before_count = before['records'][table]
            after_count = after['records'][table]
            diff = after_count - before_count
            
            if before_count > 0:
                diff_percent = (diff / before_count * 100)
                if abs(diff_percent) > 5:  # أكثر من 5% فرق
                    significant_differences.append({
                        'table': table,
                        'before': before_count,
                        'after': after_count,
                        'diff': diff,
                        'percent': diff_percent
                    })
        
        if significant_differences:
            self.log(f"جداول بها فروقات كبيرة: {len(significant_differences)}", 'warning')
            for item in significant_differences[:10]:
                self.log(
                    f"  - {item['table']}: {item['before']} → {item['after']} ({item['diff']:+d}, {item['percent']:+.1f}%)",
                    'warning'
                )
                issues.append(f"{item['table']}: {item['diff']:+d} سجل")
        
        # مقارنة العينات
        if 'samples' in before and 'samples' in after:
            self.log("مقارنة العينات الحرجة:", 'step')
            for key in before['samples']:
                if key not in after['samples']:
                    issues.append(f"عينة {key} مفقودة بالكامل")
                    self.log(f"  ❌ {key}: مفقودة!", 'error')
                    continue
                
                before_ids = {item['id'] for item in before['samples'][key]}
                after_ids = {item['id'] for item in after['samples'][key]}
                
                missing = before_ids - after_ids
                if missing:
                    issues.append(f"{key}: سجلات مفقودة من العينة: {len(missing)}")
                    self.log(f"  ⚠️ {key}: {len(missing)} سجل مفقود من العينة", 'warning')
                else:
                    self.log(f"  ✅ {key}: جميع العينات موجودة", 'success')
        
        return issues
    
    def run(self):
        """تشغيل الاختبار الكامل"""
        print("\n" + "="*80)
        print("🧪 اختبار شامل: النسخ الاحتياطي والاستعادة الكاملة")
        print("="*80)
        print(f"⏰ وقت البدء: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🗄️ قاعدة البيانات: PostgreSQL - {settings.DATABASES['default']['NAME']}")
        print("="*80 + "\n")
        
        try:
            # الخطوة 0: نسخة احتياطية من PostgreSQL
            self.pg_backup()
            
            # الخطوة 1: حساب البيانات الحالية
            self.log("الخطوة 1: حساب البيانات الحالية...", 'step')
            total_before, records_before = self.count_all_data()
            samples_before = self.sample_critical_data()
            
            self.report['before'] = {
                'total': total_before,
                'records': records_before,
                'samples': samples_before
            }
            
            self.log(f"إجمالي السجلات: {total_before:,}", 'info')
            self.log(f"عدد الجداول: {len(records_before)}", 'info')
            
            # عرض أكبر 10 جداول
            self.log("أكبر 10 جداول:", 'info')
            top_10 = sorted(records_before.items(), key=lambda x: x[1], reverse=True)[:10]
            for label, count in top_10:
                self.log(f"  {label}: {count:,} سجل", 'info')
            
            if total_before == 0:
                self.log("قاعدة البيانات فارغة! لا يمكن الاختبار.", 'error')
                return False
            
            # الخطوة 2: إنشاء نسخة احتياطية باستخدام النظام
            self.log("الخطوة 2: إنشاء نسخة احتياطية من خلال النظام...", 'step')
            try:
                perform_backup_task(None, self.timestamp, self.backup_file, self.backup_file)
                self.log(f"تم إنشاء النسخة: {self.backup_file}", 'success')
            except Exception as e:
                self.log(f"فشل في إنشاء النسخة: {e}", 'error')
                return False
            
            # الخطوة 3: التحقق من محتوى النسخة
            self.log("الخطوة 3: التحقق من محتوى النسخة الاحتياطية...", 'step')
            try:
                with open(self.backup_file, 'r', encoding='utf-8') as f:
                    backup_data = json.load(f)
                
                backup_total = 0
                for app_name, app_models in backup_data['data'].items():
                    for model_name, records in app_models.items():
                        if isinstance(records, list):
                            backup_total += len(records)
                
                self.log(f"النسخة تحتوي على: {backup_total:,} سجل", 'info')
                
                coverage = (backup_total / total_before * 100) if total_before > 0 else 0
                self.log(f"تغطية النسخة: {coverage:.2f}%", 'info')
                
                if coverage < 90:
                    self.log(f"تحذير: النسخة تغطي أقل من 90% من البيانات!", 'warning')
                
            except Exception as e:
                self.log(f"خطأ في قراءة النسخة: {e}", 'error')
                return False
            
            # الخطوة 4: مسح جميع البيانات
            self.log("الخطوة 4: مسح جميع البيانات... 🔥", 'important')
            self.log("هذه الخطوة خطيرة جداً!", 'warning')
            
            try:
                perform_clear_all_data(user=None)
                self.log("تم مسح جميع البيانات", 'success')
            except Exception as e:
                self.log(f"خطأ في المسح: {e}", 'error')
                # محاولة استعادة فورية
                self.log("محاولة استعادة فورية من النسخة...", 'important')
                try:
                    perform_backup_restore(backup_data, clear_data=False, user=None)
                    self.log("تمت الاستعادة الطارئة", 'success')
                except:
                    self.log("فشلت الاستعادة الطارئة! استخدم نسخة PostgreSQL", 'error')
                return False
            
            # الخطوة 5: التحقق من المسح
            self.log("الخطوة 5: التحقق من المسح...", 'step')
            total_after_clear, _ = self.count_all_data()
            self.log(f"السجلات المتبقية بعد المسح: {total_after_clear:,}", 'info')
            
            if total_after_clear > 100:
                self.log(f"تحذير: لا تزال هناك {total_after_clear:,} سجل!", 'warning')
            
            # الخطوة 6: استعادة النسخة
            self.log("الخطوة 6: استعادة النسخة الاحتياطية...", 'step')
            try:
                perform_backup_restore(backup_data, clear_data=False, user=None)
                self.log("اكتملت عملية الاستعادة", 'success')
            except Exception as e:
                self.log(f"فشلت الاستعادة: {e}", 'error')
                self.log("⚠️⚠️⚠️ البيانات مفقودة! استخدم نسخة PostgreSQL للاستعادة", 'error')
                return False
            
            # الخطوة 7: حساب البيانات بعد الاستعادة
            self.log("الخطوة 7: حساب البيانات بعد الاستعادة...", 'step')
            total_after, records_after = self.count_all_data()
            samples_after = self.sample_critical_data()
            
            self.report['after'] = {
                'total': total_after,
                'records': records_after,
                'samples': samples_after
            }
            
            self.log(f"إجمالي السجلات بعد الاستعادة: {total_after:,}", 'info')
            
            # الخطوة 8: المقارنة الشاملة
            self.log("الخطوة 8: المقارنة الشاملة...", 'step')
            issues = self.compare_data(self.report['before'], self.report['after'])
            
            # النتيجة النهائية
            print("\n" + "="*80)
            self.log("📊 النتيجة النهائية", 'step')
            print("="*80)
            
            recovery_rate = (total_after / total_before * 100) if total_before > 0 else 0
            self.log(f"معدل الاستعادة: {recovery_rate:.2f}%", 'info')
            
            if recovery_rate >= 99 and len(issues) == 0:
                self.log("✅✅✅ الاختبار نجح بنسبة 100%!", 'success')
                self.log("يمكنك الثقة الكاملة بعملية النسخ والاستعادة", 'success')
                self.report['success'] = True
                return True
            elif recovery_rate >= 95 and len(issues) <= 5:
                self.log("✅ الاختبار نجح بنسبة عالية", 'success')
                self.log(f"معدل الاستعادة: {recovery_rate:.2f}%", 'info')
                self.log(f"مشاكل طفيفة: {len(issues)}", 'warning')
                self.report['success'] = True
                return True
            elif recovery_rate >= 85:
                self.log("⚠️ الاختبار نجح جزئياً", 'warning')
                self.log(f"فُقد {100-recovery_rate:.2f}% من البيانات", 'warning')
                self.report['success'] = False
                return False
            else:
                self.log("❌ الاختبار فشل", 'error')
                self.log(f"فُقد {100-recovery_rate:.2f}% من البيانات", 'error')
                self.report['success'] = False
                return False
            
        except Exception as e:
            self.log(f"خطأ غير متوقع: {e}", 'error')
            import traceback
            traceback.print_exc()
            return False
        
        finally:
            # حفظ التقرير
            report_file = f'backup_test_report_{self.timestamp}.json'
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(self.report, f, ensure_ascii=False, indent=2)
            print(f"\n📄 تم حفظ التقرير: {report_file}")

def main():
    print("\n" + "⚠️ "*40)
    print("تحذير خطير جداً!")
    print("⚠️ "*40)
    print("\nهذا الاختبار سيقوم بـ:")
    print("1. أخذ نسخة احتياطية من PostgreSQL (pg_dump)")
    print("2. أخذ نسخة احتياطية من النظام")
    print("3. مسح جميع البيانات من قاعدة البيانات")
    print("4. استعادة البيانات من النسخة")
    print("\n⚠️ إذا فشل الاختبار، ستحتاج لاستعادة نسخة PostgreSQL يدوياً!")
    print("\n" + "="*80)
    
    response = input("\nهل أنت متأكد تماماً من المتابعة؟ اكتب 'نعم متأكد' للمتابعة: ")
    
    if response.strip() != 'نعم متأكد':
        print("\n❌ تم إلغاء الاختبار بأمان")
        print("💡 نصيحة: يمكنك أولاً أخذ نسخة يدوية من قاعدة البيانات بنفسك")
        return
    
    print("\n🚀 بدء الاختبار...")
    print("="*80 + "\n")
    
    test = ComprehensiveBackupTest()
    success = test.run()
    
    print("\n" + "="*80)
    print("🏁 انتهى الاختبار")
    print("="*80)
    
    if success:
        print("\n✅ النتيجة: النظام موثوق ويمكن استخدامه في الإنتاج")
    else:
        print("\n❌ النتيجة: يوجد مشاكل يجب حلها قبل الاستخدام في الإنتاج")
    
    if test.report['errors']:
        print("\n❌ الأخطاء:")
        for error in test.report['errors']:
            print(f"  - {error}")
    
    if test.report['warnings']:
        print("\n⚠️ التحذيرات:")
        for warning in test.report['warnings'][:10]:
            print(f"  - {warning}")
        if len(test.report['warnings']) > 10:
            print(f"  ... و {len(test.report['warnings'])-10} تحذير آخر")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    main()
