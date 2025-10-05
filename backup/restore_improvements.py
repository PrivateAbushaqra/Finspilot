# نسخة محسّنة من دالة الاستعادة مع logging مفصل وتقرير كامل

import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def perform_backup_restore_with_reporting(backup_file_path, backup_format='json', restore_mode='tolerant'):
    """
    نسخة محسّنة من دالة الاستعادة مع:
    - Logging مفصل لكل خطوة
    - تقرير شامل بعد الانتهاء
    - وضع tolerant يحاول الاستمرار بدلاً من الفشل
    - معالجة أفضل للأخطاء
    
    Args:
        backup_file_path: مسار ملف النسخة الاحتياطية
        backup_format: نوع الملف (json أو excel)
        restore_mode: 'strict' أو 'tolerant'
    
    Returns:
        dict: تقرير شامل بنتائج الاستعادة
    """
    
    # إنشاء تقرير الاستعادة
    restore_report = {
        'started_at': datetime.now(),
        'backup_file': backup_file_path,
        'backup_format': backup_format,
        'restore_mode': restore_mode,
        'total_records_expected': 0,
        'records_restored': 0,
        'records_skipped': 0,
        'records_failed': 0,
        'tables_processed': 0,
        'errors': [],
        'warnings': [],
        'details_by_table': {}
    }
    
    try:
        # 1. تحميل الملف
        logger.info(f"📂 بدء تحميل ملف النسخة الاحتياطية: {backup_file_path}")
        
        if backup_format == 'json':
            with open(backup_file_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
        elif backup_format == 'excel':
            from backup.views import load_backup_from_xlsx
            backup_data = load_backup_from_xlsx(backup_file_path)
        else:
            raise ValueError(f"Unsupported backup format: {backup_format}")
        
        restore_report['total_records_expected'] = len(backup_data)
        logger.info(f"✅ تم تحميل {len(backup_data)} سجل من الملف")
        
        # 2. تجميع السجلات حسب الجداول
        tables_data = {}
        for record in backup_data:
            model_name = record.get('model')
            if model_name not in tables_data:
                tables_data[model_name] = []
            tables_data[model_name].append(record)
        
        logger.info(f"📊 عدد الجداول: {len(tables_data)}")
        
        # 3. ترتيب الجداول حسب التبعيات
        # استخدام ترتيب ثابت مبدئياً
        restoration_order = [
            'core.documentsequence',
            'core.companysettings',
            'auth.group',
            'auth.user',
            'core.auditlog',
            'accounts.account',
            'accounts.costcenter',
            'customers.customer',
            'customers.customercategory',
            'products.category',
            'products.unit',
            'products.product',
            'sales.salesinvoice',
            'sales.salesinvoiceitem',
            'purchases.purchaseinvoice',
            'purchases.purchaseinvoiceitem',
        ]
        
        # إضافة أي جداول أخرى غير مدرجة
        for model_name in tables_data.keys():
            if model_name not in restoration_order:
                restoration_order.append(model_name)
        
        # 4. استعادة كل جدول
        for model_name in restoration_order:
            if model_name not in tables_data:
                continue
            
            table_records = tables_data[model_name]
            logger.info(f"\n🔄 معالجة الجدول: {model_name} ({len(table_records)} سجل)")
            
            table_report = {
                'total': len(table_records),
                'restored': 0,
                'skipped': 0,
                'failed': 0,
                'errors': []
            }
            
            # الحصول على Model
            try:
                app_label, model_name_only = model_name.split('.')
                from django.apps import apps
                model = apps.get_model(app_label, model_name_only)
            except Exception as e:
                logger.error(f"❌ فشل في الحصول على Model {model_name}: {e}")
                restore_report['errors'].append({
                    'type': 'model_not_found',
                    'model': model_name,
                    'error': str(e)
                })
                continue
            
            # استعادة كل سجل في الجدول
            for record in table_records:
                pk_value = record.get('pk')
                fields_data = record.get('fields', {})
                
                try:
                    # محاولة استعادة السجل
                    cleaned_data = {}
                    many_to_many_data = {}
                    
                    # تنظيف البيانات
                    for key, value in fields_data.items():
                        try:
                            field = model._meta.get_field(key)
                            
                            # معالجة Many-to-Many
                            if field.many_to_many:
                                many_to_many_data[key] = value
                                continue
                            
                            # معالجة Foreign Key
                            if field.is_relation and not field.many_to_many:
                                if value is not None:
                                    related_obj = field.related_model.objects.filter(pk=int(value)).first()
                                    if related_obj:
                                        cleaned_data[key] = related_obj
                                    elif not field.null:
                                        if restore_mode == 'tolerant':
                                            # في وضع tolerant، نستخدم أول سجل متاح أو None
                                            first_related = field.related_model.objects.first()
                                            if first_related:
                                                cleaned_data[key] = first_related
                                                restore_report['warnings'].append({
                                                    'model': model_name,
                                                    'pk': pk_value,
                                                    'field': key,
                                                    'message': f"استخدام FK افتراضي: {first_related.pk} بدلاً من {value}"
                                                })
                                            else:
                                                raise ValueError(f"لا يوجد سجلات في {field.related_model.__name__}")
                                        else:
                                            raise ValueError(f"FK_NOT_FOUND:{key}={value}")
                            else:
                                # حقول عادية
                                from backup.views import convert_field_value
                                cleaned_data[key] = convert_field_value(field, value)
                        
                        except Exception as field_err:
                            if restore_mode == 'tolerant':
                                # في وضع tolerant، نتخطى الحقل مع تحذير
                                logger.warning(f"⚠️ تخطي حقل {key} في {model_name}[{pk_value}]: {field_err}")
                                restore_report['warnings'].append({
                                    'model': model_name,
                                    'pk': pk_value,
                                    'field': key,
                                    'error': str(field_err)
                                })
                            else:
                                raise
                    
                    # إنشاء أو تحديث السجل
                    obj, created = model.objects.update_or_create(
                        pk=pk_value,
                        defaults=cleaned_data
                    )
                    
                    # معالجة Many-to-Many
                    for m2m_field, m2m_values in many_to_many_data.items():
                        if isinstance(m2m_values, list):
                            field = model._meta.get_field(m2m_field)
                            m2m_manager = getattr(obj, m2m_field)
                            
                            # جمع الكائنات المرتبطة
                            related_objects = []
                            for rel_pk in m2m_values:
                                rel_obj = field.related_model.objects.filter(pk=rel_pk).first()
                                if rel_obj:
                                    related_objects.append(rel_obj)
                            
                            # تعيين العلاقات
                            if related_objects:
                                m2m_manager.set(related_objects)
                    
                    # تسجيل النجاح
                    table_report['restored'] += 1
                    restore_report['records_restored'] += 1
                    logger.debug(f"✅ استعادة سجل {model_name}[{pk_value}]")
                
                except Exception as rec_err:
                    error_msg = str(rec_err)
                    
                    if restore_mode == 'tolerant' and not error_msg.startswith("FK_NOT_FOUND:"):
                        # في وضع tolerant، نسجل الخطأ ونستمر
                        table_report['skipped'] += 1
                        restore_report['records_skipped'] += 1
                        
                        logger.warning(f"⚠️ تخطي سجل {model_name}[{pk_value}]: {rec_err}")
                        
                        table_report['errors'].append({
                            'pk': pk_value,
                            'error': error_msg
                        })
                    else:
                        # في وضع strict أو خطأ FK، نفشل
                        table_report['failed'] += 1
                        restore_report['records_failed'] += 1
                        
                        logger.error(f"❌ فشل في استعادة سجل {model_name}[{pk_value}]: {rec_err}")
                        
                        table_report['errors'].append({
                            'pk': pk_value,
                            'error': error_msg
                        })
                        
                        restore_report['errors'].append({
                            'model': model_name,
                            'pk': pk_value,
                            'error': error_msg
                        })
            
            # إضافة تقرير الجدول
            restore_report['details_by_table'][model_name] = table_report
            restore_report['tables_processed'] += 1
            
            # طباعة ملخص الجدول
            logger.info(
                f"📈 {model_name}: "
                f"✅ {table_report['restored']} استعادة، "
                f"⚠️ {table_report['skipped']} تخطي، "
                f"❌ {table_report['failed']} فشل"
            )
    
    except Exception as e:
        logger.error(f"❌ خطأ عام في الاستعادة: {e}")
        restore_report['errors'].append({
            'type': 'general_error',
            'error': str(e)
        })
    
    finally:
        restore_report['finished_at'] = datetime.now()
        duration = restore_report['finished_at'] - restore_report['started_at']
        restore_report['duration_seconds'] = duration.total_seconds()
    
    # طباعة الملخص النهائي
    print("\n" + "="*80)
    print("📊 تقرير الاستعادة النهائي")
    print("="*80)
    print(f"⏱️  المدة: {restore_report['duration_seconds']:.2f} ثانية")
    print(f"📁 الملف: {backup_file_path}")
    print(f"📊 الوضع: {restore_mode}")
    print(f"\n📈 الإحصائيات:")
    print(f"  • إجمالي السجلات المتوقعة: {restore_report['total_records_expected']}")
    print(f"  • السجلات المستعادة: ✅ {restore_report['records_restored']}")
    print(f"  • السجلات المتخطاة: ⚠️ {restore_report['records_skipped']}")
    print(f"  • السجلات الفاشلة: ❌ {restore_report['records_failed']}")
    print(f"  • الجداول المعالجة: {restore_report['tables_processed']}")
    print(f"\n⚠️  التحذيرات: {len(restore_report['warnings'])}")
    print(f"❌ الأخطاء: {len(restore_report['errors'])}")
    
    if restore_report['errors']:
        print("\n❌ أهم الأخطاء:")
        for i, error in enumerate(restore_report['errors'][:5], 1):
            print(f"  {i}. {error.get('model', 'N/A')}[{error.get('pk', 'N/A')}]: {error.get('error', 'N/A')}")
        
        if len(restore_report['errors']) > 5:
            print(f"  ... و {len(restore_report['errors']) - 5} خطأ آخر")
    
    print("\n" + "="*80)
    
    return restore_report


# دالة مساعدة لحفظ التقرير
def save_restore_report(report, output_path='restore_report.json'):
    """حفظ تقرير الاستعادة إلى ملف JSON"""
    import json
    from datetime import datetime
    
    # تحويل التواريخ إلى نصوص
    report_copy = report.copy()
    report_copy['started_at'] = report['started_at'].isoformat()
    report_copy['finished_at'] = report['finished_at'].isoformat()
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report_copy, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 تم حفظ التقرير في: {output_path}")
