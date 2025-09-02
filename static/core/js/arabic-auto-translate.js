
// ترجمة تلقائية للنصوص الإنجليزية في الصفحة العربية
// Auto translation for English texts in Arabic page

document.addEventListener('DOMContentLoaded', function() {
    console.log('بدء الترجمة التلقائية للنصوص الإنجليزية...');
    
    // قاموس الترجمة
    const ENGLISH_TO_ARABIC = {'Dashboard': 'لوحة التحكم', 'Menu': 'القائمة', 'Settings': 'الإعدادات', 'Search': 'البحث', 'Reports': 'التقارير', 'Print': 'طباعة', 'Add': 'إضافة', 'Save': 'حفظ', 'Edit': 'تعديل', 'Delete': 'حذف', 'View': 'عرض', 'Cancel': 'إلغاء', 'Submit': 'إرسال', 'Back': 'رجوع', 'Next': 'التالي', 'Previous': 'السابق', 'Close': 'إغلاق', 'Table': 'جدول', 'New': 'جديد', 'Actions': 'الإجراءات', 'Accounts': 'الحسابات', 'Balance': 'الرصيد', 'Company': 'الشركة', 'Contact': 'الاتصال', 'Create': 'إنشاء', 'Customer': 'العميل', 'Invoice': 'الفاتورة', 'Payment': 'الدفع', 'Product': 'المنتج', 'Employee': 'الموظف', 'Activate': 'تفعيل', 'Active': 'نشط', 'Admin': 'المدير', 'Advanced': 'متقدم', 'Alert': 'تنبيه', 'All': 'الكل', 'Always': 'دائماً', 'Analytics': 'التحليلات', 'Assets': 'الأصول', 'Auto': 'تلقائي', 'Background': 'الخلفية', 'Bank': 'البنك', 'Banks': 'البنوك', 'Cards': 'البطاقات', 'Case': 'الحالة', 'Cashbox': 'الصندوق', 'Cashboxes': 'الصناديق', 'Categories': 'الفئات', 'Change': 'تغيير', 'Chart': 'مخطط', 'Charts': 'المخططات', 'Check': 'فحص', 'Checks': 'الشيكات', 'Color': 'اللون', 'Copy': 'نسخ', 'Currency': 'العملة', 'Current': 'الحالي', 'Customers': 'العملاء', 'Departments': 'الأقسام', 'HR Reports': 'تقارير الموارد البشرية', 'Upload Attendance': 'رفع الحضور', 'Statistics': 'الإحصائيات', 'Position': 'المنصب', 'Salary': 'الراتب', 'Attendance': 'الحضور', 'Leave': 'إجازة', 'Overtime': 'العمل الإضافي', 'Products': 'المنتجات', 'Inventory': 'المخزون', 'Stock': 'المخزون', 'Warehouse': 'المستودع', 'Warehouses': 'المستودعات', 'Supplier': 'المورد', 'Suppliers': 'الموردون', 'Purchase': 'الشراء', 'Sale': 'البيع', 'Sales': 'المبيعات', 'Order': 'الطلب', 'Orders': 'الطلبات', 'Report': 'التقرير', 'Summary': 'الملخص', 'Details': 'التفاصيل', 'Graph': 'الرسم البياني', 'List': 'القائمة', 'Preview': 'معاينة', 'Configuration': 'التكوين', 'Preferences': 'التفضيلات', 'Options': 'الخيارات', 'Properties': 'الخصائص', 'Tools': 'الأدوات', 'Security': 'الأمان', 'Login': 'تسجيل الدخول', 'Logout': 'تسجيل الخروج', 'User': 'المستخدم', 'Users': 'المستخدمون', 'Role': 'الدور', 'Roles': 'الأدوار', 'Permission': 'الصلاحية', 'Permissions': 'الصلاحيات', 'Access': 'الوصول', 'Update': 'تحديث', 'Remove': 'إزالة', 'Send': 'إرسال', 'Receive': 'استقبال', 'Process': 'معالجة', 'Generate': 'توليد', 'Calculate': 'حساب', 'Validate': 'التحقق', 'Confirm': 'تأكيد', 'Approve': 'موافقة', 'Reject': 'رفض', 'Accept': 'قبول', 'Inactive': 'غير نشط', 'Enabled': 'مفعل', 'Disabled': 'معطل', 'Available': 'متاح', 'Online': 'متصل', 'Offline': 'غير متصل', 'Open': 'مفتوح', 'Closed': 'مغلق', 'Pending': 'معلق', 'Completed': 'مكتمل', 'Draft': 'مسودة', 'Published': 'منشور', 'Archived': 'مؤرشف', 'Date': 'التاريخ', 'Time': 'الوقت', 'Today': 'اليوم', 'Yesterday': 'أمس', 'Tomorrow': 'غداً', 'Week': 'الأسبوع', 'Month': 'الشهر', 'Year': 'السنة', 'Number': 'الرقم', 'Count': 'العدد', 'Total': 'الإجمالي', 'Sum': 'المجموع', 'Average': 'المتوسط', 'Maximum': 'الحد الأقصى', 'Minimum': 'الحد الأدنى', 'Percentage': 'النسبة المئوية', 'Export': 'تصدير', 'Import': 'استيراد', 'Download': 'تحميل', 'Upload': 'رفع', 'Backup': 'نسخ احتياطي', 'Restore': 'استعادة', 'Sync': 'مزامنة', 'Share': 'مشاركة', 'File': 'الملف', 'Files': 'الملفات', 'Folder': 'المجلد', 'Document': 'الوثيقة', 'Find': 'العثور', 'Filter': 'فلتر', 'Sort': 'ترتيب', 'Group': 'تجميع', 'Select': 'تحديد', 'Choose': 'اختيار', 'Message': 'الرسالة', 'Messages': 'الرسائل', 'Notification': 'الإشعار', 'Error': 'خطأ', 'Success': 'نجح', 'Warning': 'تحذير', 'Info': 'معلومات', 'Home': 'الرئيسية', 'Page': 'الصفحة', 'Section': 'القسم', 'Tab': 'التبويب', 'Link': 'الرابط', 'Button': 'الزر', 'Icon': 'الأيقونة', 'Help': 'المساعدة', 'Support': 'الدعم', 'About': 'حول', 'Version': 'الإصدار', 'Language': 'اللغة', 'Translation': 'الترجمة', 'Loading': 'جاري التحميل', 'Please wait': 'يرجى الانتظار', 'Yes': 'نعم', 'No': 'لا'};
    
    // دالة ترجمة النص
    function translateText(text) {
        // إزالة المسافات الزائدة
        const cleanText = text.trim();
        
        // البحث عن ترجمة مباشرة
        if (ENGLISH_TO_ARABIC[cleanText]) {
            return ENGLISH_TO_ARABIC[cleanText];
        }
        
        // البحث عن ترجمة جزئية للكلمات الفردية
        const words = cleanText.split(/\s+/);
        let translated = false;
        let result = words.map(word => {
            // إزالة علامات الترقيم من بداية ونهاية الكلمة
            const cleanWord = word.replace(/^[^\w]+|[^\w]+$/g, '');
            const prefix = word.substring(0, word.indexOf(cleanWord));
            const suffix = word.substring(word.indexOf(cleanWord) + cleanWord.length);
            
            if (ENGLISH_TO_ARABIC[cleanWord]) {
                translated = true;
                return prefix + ENGLISH_TO_ARABIC[cleanWord] + suffix;
            }
            return word;
        }).join(' ');
        
        return translated ? result : text;
    }
    
    // دالة معالجة العقد النصية
    function processTextNode(node) {
        const originalText = node.textContent;
        const translatedText = translateText(originalText);
        
        if (translatedText !== originalText) {
            node.textContent = translatedText;
            console.log(`ترجم: "${originalText}" -> "${translatedText}"`);
        }
    }
    
    // دالة معالجة العناصر
    function processElement(element) {
        // تجنب معالجة العناصر التقنية
        const skipTags = ['SCRIPT', 'STYLE', 'NOSCRIPT', 'IFRAME'];
        if (skipTags.includes(element.tagName)) {
            return;
        }
        
        // معالجة النصوص في الخصائص
        const attributes = ['title', 'alt', 'placeholder', 'aria-label'];
        attributes.forEach(attr => {
            if (element.hasAttribute(attr)) {
                const originalValue = element.getAttribute(attr);
                const translatedValue = translateText(originalValue);
                if (translatedValue !== originalValue) {
                    element.setAttribute(attr, translatedValue);
                    console.log(`ترجم خاصية ${attr}: "${originalValue}" -> "${translatedValue}"`);
                }
            }
        });
        
        // معالجة النصوص المباشرة (TextNodes)
        for (let i = 0; i < element.childNodes.length; i++) {
            const child = element.childNodes[i];
            if (child.nodeType === Node.TEXT_NODE) {
                processTextNode(child);
            } else if (child.nodeType === Node.ELEMENT_NODE) {
                processElement(child);
            }
        }
    }
    
    // بدء المعالجة من body
    processElement(document.body);
    
    // مراقبة التغييرات الديناميكية
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            mutation.addedNodes.forEach(function(node) {
                if (node.nodeType === Node.ELEMENT_NODE) {
                    processElement(node);
                } else if (node.nodeType === Node.TEXT_NODE) {
                    processTextNode(node);
                }
            });
        });
    });
    
    // بدء مراقبة التغييرات
    observer.observe(document.body, {
        childList: true,
        subtree: true,
        characterData: true
    });
    
    console.log('تم تفعيل الترجمة التلقائية للنصوص الإنجليزية');
});
