"""
أمر Django لإصلاح جميع sequences في قاعدة البيانات
يستخدم هذا الأمر لحل مشاكل تضارب ID بعد استعادة النسخ الاحتياطية

الاستخدام:
    python manage.py fix_sequences
"""
from django.core.management.base import BaseCommand
from django.db import connection
from django.utils.translation import gettext as _


class Command(BaseCommand):
    help = _('إصلاح جميع sequences في قاعدة البيانات')

    def add_arguments(self, parser):
        parser.add_argument(
            '--verbose',
            action='store_true',
            help=_('عرض تفاصيل كل sequence تم إصلاحه'),
        )

    def handle(self, *args, **options):
        verbose = options['verbose']
        
        self.stdout.write(self.style.WARNING(_('بدء إصلاح جميع التسلسلات (sequences)...')))
        
        try:
            with connection.cursor() as cursor:
                # جلب جميع sequences والجداول المرتبطة بها
                cursor.execute("""
                    SELECT 
                        c.relname as table_name,
                        s.relname as sequence_name
                    FROM pg_class s
                    JOIN pg_depend d ON d.objid = s.oid
                    JOIN pg_class c ON d.refobjid = c.oid
                    WHERE s.relkind = 'S'
                    AND c.relkind = 'r'
                    AND s.relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
                    ORDER BY c.relname;
                """)
                
                sequences = cursor.fetchall()
                fixed_count = 0
                total_count = len(sequences)
                
                for table_name, seq_name in sequences:
                    try:
                        # افتراض أن العمود هو 'id' (المعيار في Django)
                        column_name = 'id'
                        
                        # جلب أعلى قيمة في الجدول
                        cursor.execute(f"SELECT MAX({column_name}) FROM {table_name}")
                        max_id = cursor.fetchone()[0]
                        
                        # جلب قيمة sequence الحالية
                        cursor.execute(f"SELECT last_value FROM {seq_name}")
                        seq_value = cursor.fetchone()[0]
                        
                        if max_id is not None and seq_value <= max_id:
                            # إعادة تعيين sequence
                            cursor.execute(f"SELECT setval('{seq_name}', {max_id + 1}, false)")
                            fixed_count += 1
                            
                            if verbose:
                                self.stdout.write(
                                    self.style.SUCCESS(
                                        f'  ✓ {table_name}: {seq_value} → {max_id + 1}'
                                    )
                                )
                        elif max_id is None:
                            # الجدول فارغ، تأكد من أن sequence عند 1
                            if seq_value != 1:
                                cursor.execute(f"SELECT setval('{seq_name}', 1, false)")
                                fixed_count += 1
                                
                                if verbose:
                                    self.stdout.write(
                                        self.style.SUCCESS(
                                            f'  ✓ {table_name}: {seq_value} → 1 (جدول فارغ)'
                                        )
                                    )
                        else:
                            if verbose:
                                self.stdout.write(
                                    self.style.WARNING(
                                        f'  - {table_name}: sequence صحيح ({seq_value})'
                                    )
                                )
                                
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(
                                f'  ✗ خطأ في {table_name}: {str(e)}'
                            )
                        )
                        continue
                
                self.stdout.write('')
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ تم إصلاح {fixed_count} sequence من أصل {total_count}'
                    )
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f'✗ فشل في إصلاح التسلسلات: {str(e)}'
                )
            )
            raise
