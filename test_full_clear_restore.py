"""
اختبار شامل ونهائي: مسح كامل + استعادة كاملة

هذا الاختبار سيقوم بـ:
1. حساب البيانات الحالية
2. إنشاء نسخة احتياطية
3. حفظ بيانات اختبارية للمقارنة
4. مسح جميع البيانات (DANGEROUS!)
5. استعادة النسخة الاحتياطية
6. التحقق من سلامة البيانات المستعادة
7. مقارنة البيانات قبل وبعد

⚠️ تحذير: هذا الاختبار سيمسح جميع البيانات!
"""

import os
import django
import json
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from backup.views import perform_backup_task, perform_backup_restore, perform_clear_all_data
from django.apps import apps
from django.db import connection, transaction

class BackupRestoreTest:
    def __init__(self):
        self.test_results = {
            'timestamp': datetime.now().isoformat(),
            'steps': [],
            'success': False,
            'errors': [],
            'warnings': []
        }
        self.before_data = {}
        self.after_data = {}
        self.backup_file = 'test_full_restore_backup.json'
    
    def log(self, message, level='info'):
        """تسجيل رسالة"""
        prefix = {
            'info': '📝',
            'success': '✅',
            'warning': '⚠️',
            'error': '❌',
            'step': '🔹'
        }
        print(f"{prefix.get(level, '📝')} {message}")
        
        step = {
            'message': message,
            'level': level,
            'timestamp': datetime.now().isoformat()
        }
        self.test_results['steps'].append(step)
        
        if level == 'error':
            self.test_results['errors'].append(message)
        elif level == 'warning':
            self.test_results['warnings'].append(message)
    
    def count_records(self):
        """حساب جميع السجلات في قاعدة البيانات"""
        records = {}
        total = 0
        
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
    
    def sample_data(self):
        """أخذ عينات من البيانات للمقارنة"""
        samples = {}
        
        try:
            # عينة من المستخدمين
            from django.contrib.auth import get_user_model
            User = get_user_model()
            users = list(User.objects.values('id', 'username', 'email')[:5])
            samples['users'] = users
            
            # عينة من المنتجات
            from products.models import Product
            products = list(Product.objects.values('id', 'name', 'price')[:5])
            samples['products'] = products
            
            # عينة من العملاء
            from customers.models import Customer
            customers = list(Customer.objects.values('id', 'name', 'phone')[:5])
            samples['customers'] = customers
            
            # عينة من الفواتير
            from sales.models import SalesInvoice
            invoices = list(SalesInvoice.objects.values('id', 'invoice_number', 'total_amount')[:5])
            samples['invoices'] = invoices
            
        except Exception as e:
            self.log(f"خطأ في أخذ العينات: {e}", 'warning')
        
        return samples
    
    def verify_data_integrity(self, before_samples, after_samples):
        """التحقق من سلامة البيانات"""
        issues = []
        
        for key, before_list in before_samples.items():
            if key not in after_samples:
                issues.append(f"فقدان كامل لـ {key}")
                continue
            
            after_list = after_samples[key]
            
            # مقارنة عدد السجلات
            if len(before_list) != len(after_list):
                issues.append(f"{key}: عدد السجلات مختلف (قبل: {len(before_list)}, بعد: {len(after_list)})")
            
            # مقارنة السجلات نفسها
            before_ids = {item['id'] for item in before_list}
            after_ids = {item['id'] for item in after_list}
            
            missing = before_ids - after_ids
            if missing:
                issues.append(f"{key}: سجلات مفقودة: {missing}")
        
        return issues
    
    def run_test(self):
        """تشغيل الاختبار الكامل"""
        print("\n" + "="*80)
        print("🧪 اختبار شامل: مسح كامل + استعادة كاملة")
        print("="*80)
        
        try:
            # الخطوة 1: حساب البيانات الأولية
            self.log("الخطوة 1: حساب البيانات الحالية...", 'step')
            total_before, records_before = self.count_records()
            self.before_data = {
                'total': total_before,
                'records': records_before
            }
            self.log(f"إجمالي السجلات قبل: {total_before}", 'info')
            self.log(f"عدد الجداول: {len(records_before)}", 'info')
            
            # عرض أكبر 5 جداول
            top_5 = sorted(records_before.items(), key=lambda x: x[1], reverse=True)[:5]
            for label, count in top_5:
                self.log(f"  - {label}: {count}", 'info')
            
            if total_before == 0:
                self.log("قاعدة البيانات فارغة! لا يمكن الاختبار.", 'error')
                return False
            
            # الخطوة 2: أخذ عينات
            self.log("الخطوة 2: أخذ عينات من البيانات للمقارنة...", 'step')
            samples_before = self.sample_data()
            for key, items in samples_before.items():
                self.log(f"  - {key}: {len(items)} عينة", 'info')
            
            # الخطوة 3: إنشاء نسخة احتياطية
            self.log("الخطوة 3: إنشاء نسخة احتياطية...", 'step')
            try:
                perform_backup_task(None, 'test', self.backup_file, self.backup_file)
                self.log("تم إنشاء النسخة الاحتياطية بنجاح", 'success')
            except Exception as e:
                self.log(f"فشل في إنشاء النسخة الاحتياطية: {e}", 'error')
                return False
            
            # الخطوة 4: التحقق من محتوى النسخة
            self.log("الخطوة 4: التحقق من محتوى النسخة الاحتياطية...", 'step')
            try:
                with open(self.backup_file, 'r', encoding='utf-8') as f:
                    backup_data = json.load(f)
                
                backup_total = 0
                for app_name, app_models in backup_data['data'].items():
                    for model_name, records in app_models.items():
                        if isinstance(records, list):
                            backup_total += len(records)
                
                self.log(f"النسخة تحتوي على {backup_total} سجل", 'info')
                
                if backup_total < total_before * 0.9:  # إذا فقد أكثر من 10%
                    self.log(f"تحذير: النسخة تحتوي على سجلات أقل بكثير! (فرق: {total_before - backup_total})", 'warning')
                
            except Exception as e:
                self.log(f"خطأ في قراءة النسخة الاحتياطية: {e}", 'error')
                return False
            
            # الخطوة 5: مسح جميع البيانات
            self.log("الخطوة 5: مسح جميع البيانات... ⚠️", 'step')
            self.log("هذه الخطوة خطيرة! سيتم مسح كل شيء.", 'warning')
            
            try:
                perform_clear_all_data(user=None)
                self.log("تم مسح جميع البيانات", 'success')
            except Exception as e:
                self.log(f"خطأ في مسح البيانات: {e}", 'error')
                # محاولة الاستعادة الفورية
                self.log("محاولة استعادة النسخة فوراً...", 'warning')
                perform_backup_restore(backup_data, clear_data=False, user=None)
                return False
            
            # الخطوة 6: التحقق من المسح
            self.log("الخطوة 6: التحقق من المسح الكامل...", 'step')
            total_after_clear, records_after_clear = self.count_records()
            self.log(f"السجلات بعد المسح: {total_after_clear}", 'info')
            
            if total_after_clear > 100:  # بعض الجداول الأساسية قد تبقى
                self.log(f"تحذير: لا تزال هناك {total_after_clear} سجل بعد المسح", 'warning')
            
            # الخطوة 7: استعادة النسخة الاحتياطية
            self.log("الخطوة 7: استعادة النسخة الاحتياطية...", 'step')
            try:
                perform_backup_restore(backup_data, clear_data=False, user=None)
                self.log("تمت عملية الاستعادة", 'success')
            except Exception as e:
                self.log(f"فشل في الاستعادة: {e}", 'error')
                self.log("⚠️⚠️⚠️ البيانات مفقودة! ⚠️⚠️⚠️", 'error')
                return False
            
            # الخطوة 8: حساب البيانات بعد الاستعادة
            self.log("الخطوة 8: حساب البيانات بعد الاستعادة...", 'step')
            total_after, records_after = self.count_records()
            self.after_data = {
                'total': total_after,
                'records': records_after
            }
            self.log(f"إجمالي السجلات بعد: {total_after}", 'info')
            
            # الخطوة 9: أخذ عينات بعد الاستعادة
            self.log("الخطوة 9: التحقق من العينات بعد الاستعادة...", 'step')
            samples_after = self.sample_data()
            
            # الخطوة 10: مقارنة البيانات
            self.log("الخطوة 10: مقارنة البيانات قبل وبعد...", 'step')
            
            # مقارنة الأعداد
            difference = total_after - total_before
            percentage = (difference / total_before * 100) if total_before > 0 else 0
            
            self.log(f"الفرق: {difference:+d} سجل ({percentage:+.1f}%)", 'info')
            
            if abs(difference) > total_before * 0.1:  # إذا الفرق أكثر من 10%
                self.log(f"تحذير كبير: فرق كبير في عدد السجلات!", 'warning')
            
            # مقارنة العينات
            integrity_issues = self.verify_data_integrity(samples_before, samples_after)
            
            if integrity_issues:
                self.log("مشاكل في سلامة البيانات:", 'warning')
                for issue in integrity_issues:
                    self.log(f"  - {issue}", 'warning')
            else:
                self.log("جميع العينات تطابقت بنجاح!", 'success')
            
            # النتيجة النهائية
            if total_after >= total_before * 0.95 and len(integrity_issues) == 0:
                self.log("✅ الاختبار نجح! البيانات استُعيدت بشكل صحيح", 'success')
                self.test_results['success'] = True
                return True
            elif total_after >= total_before * 0.85:
                self.log("⚠️ الاختبار نجح جزئياً: فُقدت بعض البيانات", 'warning')
                self.test_results['success'] = False
                return False
            else:
                self.log("❌ الاختبار فشل: فُقدت بيانات كثيرة", 'error')
                self.test_results['success'] = False
                return False
                
        except Exception as e:
            self.log(f"خطأ غير متوقع: {e}", 'error')
            import traceback
            traceback.print_exc()
            return False
    
    def save_report(self):
        """حفظ تقرير الاختبار"""
        report_file = 'backup_restore_test_report.json'
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(self.test_results, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 تم حفظ التقرير في: {report_file}")

def main():
    print("\n" + "⚠️ "*20)
    print("تحذير: هذا الاختبار سيمسح جميع البيانات في قاعدة البيانات!")
    print("⚠️ "*20)
    
    response = input("\nهل أنت متأكد من المتابعة؟ اكتب 'نعم' للمتابعة: ")
    
    if response.strip().lower() not in ['نعم', 'yes', 'y']:
        print("❌ تم إلغاء الاختبار")
        return
    
    print("\n⏳ بدء الاختبار...")
    
    test = BackupRestoreTest()
    success = test.run_test()
    test.save_report()
    
    print("\n" + "="*80)
    if success:
        print("✅ النتيجة النهائية: الاختبار نجح!")
        print("✅ يمكنك الآن الثقة بعملية المسح والاستعادة")
    else:
        print("❌ النتيجة النهائية: الاختبار فشل!")
        print("❌ لا تقم بمسح البيانات على الإنتاج!")
    print("="*80)
    
    # عرض الأخطاء والتحذيرات
    if test.test_results['errors']:
        print("\n❌ الأخطاء:")
        for error in test.test_results['errors']:
            print(f"  - {error}")
    
    if test.test_results['warnings']:
        print("\n⚠️ التحذيرات:")
        for warning in test.test_results['warnings']:
            print(f"  - {warning}")

if __name__ == "__main__":
    main()
