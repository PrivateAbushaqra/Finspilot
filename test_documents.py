#!/usr/bin/env python
"""
سكريبت اختبار نظام أرشفة المستندات الداعمة
يختبر رفع المستندات، ربطها بالكائنات، عرضها، وحذفها
يحفظ النتائج في ملف test_documents_result.txt
"""

import os
import sys
import django
from datetime import datetime
from decimal import Decimal

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from users.models import User
from django.core.files.base import ContentFile
from django.test import TestCase
from django.db import transaction
from documents.models import Document
from journal.models import Account
from journal.models import JournalEntry
from sales.models import SalesInvoice
from customers.models import CustomerSupplier
from core.models import AuditLog

class DocumentArchivingTest:
    def __init__(self):
        self.results = []
        self.test_user = None
        self.test_account = None
        self.test_journal = None
        self.test_invoice = None
        self.test_customer = None

    def log(self, message):
        """تسجيل رسالة في النتائج"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.results.append(f"[{timestamp}] {message}")
        print(message)

    def setup_test_data(self):
        """إعداد البيانات التجريبية"""
        self.log("=== إعداد البيانات التجريبية ===")

        try:
            # إنشاء مستخدم تجريبي
            self.test_user, created = User.objects.get_or_create(
                username='test_document_user',
                defaults={
                    'email': 'test@example.com',
                    'first_name': 'Test',
                    'last_name': 'User'
                }
            )
            if created:
                self.test_user.set_password('testpass123')
                self.test_user.save()
                self.log("✓ تم إنشاء مستخدم تجريبي")
            else:
                self.log("✓ تم العثور على مستخدم تجريبي موجود")

            # إنشاء حساب تجريبي
            self.test_account, created = Account.objects.get_or_create(
                code='TEST001',
                defaults={
                    'name': 'حساب تجريبي للاختبار',
                    'account_type': 'asset',
                    'is_active': True
                }
            )
            if created:
                self.log("✓ تم إنشاء حساب تجريبي")
            else:
                self.log("✓ تم العثور على حساب تجريبي موجود")

            # إنشاء قيد تجريبي
            self.test_journal, created = JournalEntry.objects.get_or_create(
                entry_number='TEST-JRNL-001',
                defaults={
                    'entry_date': datetime.now().date(),
                    'description': 'قيد تجريبي لاختبار الأرشفة',
                    'reference_type': 'manual',
                    'total_amount': Decimal('1000.00'),
                    'created_by': self.test_user
                }
            )
            if created:
                self.log("✓ تم إنشاء قيد تجريبي")
            else:
                self.log("✓ تم العثور على قيد تجريبي موجود")

            # إنشاء عميل تجريبي
            self.test_customer, created = CustomerSupplier.objects.get_or_create(
                name='عميل تجريبي للاختبار',
                defaults={
                    'type': 'customer',
                    'city': 'الرياض',
                    'is_active': True
                }
            )
            if created:
                self.log("✓ تم إنشاء عميل تجريبي")
            else:
                self.log("✓ تم العثور على عميل تجريبي موجود")

            # إنشاء فاتورة تجريبية
            self.test_invoice, created = SalesInvoice.objects.get_or_create(
                invoice_number='TEST-INV-001',
                defaults={
                    'date': datetime.now().date(),
                    'customer': self.test_customer,
                    'payment_type': 'cash',
                    'total_amount': Decimal('1000.00'),
                    'created_by': self.test_user
                }
            )
            if created:
                self.log("✓ تم إنشاء فاتورة تجريبية")
            else:
                self.log("✓ تم العثور على فاتورة تجريبية موجودة")

        except Exception as e:
            self.log(f"✗ خطأ في إعداد البيانات التجريبية: {str(e)}")
            return False

        return True

    def test_document_upload(self):
        """اختبار رفع المستندات"""
        self.log("\n=== اختبار رفع المستندات ===")

        try:
            # إنشاء ملف تجريبي
            test_content = b"This is a test document content for archiving system."
            test_file = ContentFile(test_content, name='test_document.txt')

            # رفع مستند مربوط بالقيد
            doc1 = Document.objects.create(
                title='مستند داعم للقيد التجريبي',
                file=test_file,
                uploaded_by=self.test_user,
                content_object=self.test_journal
            )
            self.log(f"✓ تم رفع مستند للقيد: {doc1.title}")

            # رفع مستند مربوط بالفاتورة
            test_file2 = ContentFile(test_content, name='test_invoice_doc.pdf')
            doc2 = Document.objects.create(
                title='مستند داعم للفاتورة التجريبية',
                file=test_file2,
                uploaded_by=self.test_user,
                content_object=self.test_invoice
            )
            self.log(f"✓ تم رفع مستند للفاتورة: {doc2.title}")

            # رفع مستند عام (غير مربوط)
            test_file3 = ContentFile(test_content, name='general_doc.docx')
            doc3 = Document.objects.create(
                title='مستند عام تجريبي',
                file=test_file3,
                uploaded_by=self.test_user
                # لا نحدد content_object للمستند العام
            )
            self.log(f"✓ تم رفع مستند عام: {doc3.title}")

            return [doc1, doc2, doc3]

        except Exception as e:
            self.log(f"✗ خطأ في رفع المستندات: {str(e)}")
            return []

    def test_document_listing(self, documents):
        """اختبار عرض قائمة المستندات"""
        self.log("\n=== اختبار عرض قائمة المستندات ===")

        try:
            # اختبار عرض جميع المستندات
            all_docs = Document.objects.all()
            self.log(f"✓ عدد المستندات في النظام: {all_docs.count()}")

            # اختبار عرض المستندات المربوطة بالقيد
            journal_docs = Document.objects.filter(
                content_type__model='journalentry',
                object_id=self.test_journal.id
            )
            self.log(f"✓ عدد المستندات المربوطة بالقيد: {journal_docs.count()}")

            # اختبار عرض المستندات المربوطة بالفاتورة
            invoice_docs = Document.objects.filter(
                content_type__model='salesinvoice',
                object_id=self.test_invoice.id
            )
            self.log(f"✓ عدد المستندات المربوطة بالفاتورة: {invoice_docs.count()}")

            # اختبار عرض المستندات العامة
            general_docs = Document.objects.filter(content_type__isnull=True)
            self.log(f"✓ عدد المستندات العامة: {general_docs.count()}")

            return True

        except Exception as e:
            self.log(f"✗ خطأ في عرض قائمة المستندات: {str(e)}")
            return False

    def test_document_deletion(self, documents):
        """اختبار حذف المستندات"""
        self.log("\n=== اختبار حذف المستندات ===")

        try:
            # حذف أحد المستندات
            doc_to_delete = documents[0]
            deleted_title = doc_to_delete.title
            doc_to_delete.delete()
            self.log(f"✓ تم حذف المستند: {deleted_title}")

            # التحقق من الحذف
            remaining_count = Document.objects.filter(id=doc_to_delete.id).count()
            if remaining_count == 0:
                self.log("✓ تم التحقق من حذف المستند بنجاح")
            else:
                self.log("✗ فشل في حذف المستند")

            return True

        except Exception as e:
            self.log(f"✗ خطأ في حذف المستندات: {str(e)}")
            return False

    def test_audit_logging(self):
        """اختبار تسجيل الأنشطة في سجل المراجعة"""
        self.log("\n=== اختبار سجل المراجعة ===")

        try:
            # البحث عن سجلات المراجعة المتعلقة بالمستندات
            audit_logs = AuditLog.objects.filter(
                content_type='documents'
            ).order_by('-timestamp')[:10]

            self.log(f"✓ عدد سجلات المراجعة للمستندات: {audit_logs.count()}")

            for log in audit_logs:
                self.log(f"  - {log.action_type}: {log.description}")

            return True

        except Exception as e:
            self.log(f"✗ خطأ في اختبار سجل المراجعة: {str(e)}")
            return False

    def generate_report(self):
        """إنشاء تقرير إحصائي"""
        self.log("\n=== تقرير إحصائي ===")

        try:
            total_docs = Document.objects.count()
            journal_docs = Document.objects.filter(content_type__model='journalentry').count()
            invoice_docs = Document.objects.filter(content_type__model='salesinvoice').count()
            general_docs = Document.objects.filter(content_type__isnull=True).count()

            self.log(f"إجمالي المستندات: {total_docs}")
            self.log(f"مستندات مربوطة بالقيود: {journal_docs}")
            self.log(f"مستندات مربوطة بالفواتير: {invoice_docs}")
            self.log(f"مستندات عامة: {general_docs}")

            # إحصائيات حسب نوع الملف
            file_types = {}
            for doc in Document.objects.all():
                ext = os.path.splitext(doc.file.name)[1].lower()
                file_types[ext] = file_types.get(ext, 0) + 1

            self.log("توزيع أنواع الملفات:")
            for ext, count in file_types.items():
                self.log(f"  {ext}: {count} ملف")

            return True

        except Exception as e:
            self.log(f"✗ خطأ في إنشاء التقرير: {str(e)}")
            return False

    def cleanup_test_data(self):
        """تنظيف البيانات التجريبية"""
        self.log("\n=== تنظيف البيانات التجريبية ===")

        try:
            # حذف المستندات المتبقية
            Document.objects.filter(uploaded_by=self.test_user).delete()
            self.log("✓ تم حذف المستندات التجريبية")

            # حذف البيانات التجريبية الأخرى
            if self.test_invoice and self.test_invoice.invoice_number.startswith('TEST-'):
                self.test_invoice.delete()
                self.log("✓ تم حذف الفاتورة التجريبية")

            if self.test_customer and self.test_customer.name == 'عميل تجريبي للاختبار':
                self.test_customer.delete()
                self.log("✓ تم حذف العميل التجريبي")

            if self.test_journal and self.test_journal.entry_number.startswith('TEST-'):
                self.test_journal.delete()
                self.log("✓ تم حذف القيد التجريبي")

            if self.test_account and self.test_account.code.startswith('TEST'):
                self.test_account.delete()
                self.log("✓ تم حذف الحساب التجريبي")

            # لا نحذف المستخدم التجريبي لإعادة استخدامه في الاختبارات المستقبلية

            return True

        except Exception as e:
            self.log(f"✗ خطأ في تنظيف البيانات: {str(e)}")
            return False

    def run_tests(self):
        """تشغيل جميع الاختبارات"""
        self.log("=== بدء اختبار نظام أرشفة المستندات ===\n")

        success = True

        # إعداد البيانات
        if not self.setup_test_data():
            success = False

        # اختبار الرفع
        documents = self.test_document_upload()
        if not documents:
            success = False

        # اختبار العرض
        if not self.test_document_listing(documents):
            success = False

        # اختبار الحذف
        if not self.test_document_deletion(documents):
            success = False

        # اختبار سجل المراجعة
        if not self.test_audit_logging():
            success = False

        # إنشاء التقرير
        if not self.generate_report():
            success = False

        # تنظيف البيانات
        if not self.cleanup_test_data():
            success = False

        # النتيجة النهائية
        self.log("\n" + "="*50)
        if success:
            self.log("✅ جميع الاختبارات نجحت!")
        else:
            self.log("❌ فشل في بعض الاختبارات!")
        self.log("="*50)

        return success

    def save_results(self, filename='test_documents_result.txt'):
        """حفظ النتائج في ملف"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("نتائج اختبار نظام أرشفة المستندات الداعمة\n")
                f.write("="*60 + "\n\n")
                f.write("\n".join(self.results))
                f.write("\n\nتم إنشاء التقرير في: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

            self.log(f"\n✓ تم حفظ النتائج في الملف: {filename}")
            return True

        except Exception as e:
            self.log(f"✗ خطأ في حفظ النتائج: {str(e)}")
            return False

def main():
    """الدالة الرئيسية"""
    tester = DocumentArchivingTest()
    success = tester.run_tests()
    tester.save_results()

    # إرجاع كود الخروج
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())