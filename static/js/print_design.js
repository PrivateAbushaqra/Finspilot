// Print Design Page JavaScript Functions
// وظائف صفحة تصميم الطباعة

let currentDocument = null;
let selectedElement = null;
let draggedElement = null;
let currentSettings = {};
let isResizing = false;

// إعداد الصفحة عند التحميل
document.addEventListener('DOMContentLoaded', function() {
    initializeDropZones();
    addCSRFToken();
    
    // تحديد المستند الأول إذا كان موجوداً
    const firstDocument = document.querySelector('.document-list-item');
    if (firstDocument) {
        firstDocument.click();
    }
});

// تهيئة مناطق الإسقاط
function initializeDropZones() {
    const dropZones = document.querySelectorAll('.drop-zone');
    
    dropZones.forEach(zone => {
        zone.addEventListener('dragover', handleDragOver);
        zone.addEventListener('dragleave', handleDragLeave);
        zone.addEventListener('drop', handleDrop);
        zone.addEventListener('click', handleZoneClick);
    });
}

// التعامل مع السحب فوق المنطقة
function handleDragOver(event) {
    event.preventDefault();
    this.classList.add('drag-over');
}

// التعامل مع ترك منطقة السحب
function handleDragLeave() {
    this.classList.remove('drag-over');
}

// التعامل مع الإسقاط
function handleDrop(event) {
    event.preventDefault();
    this.classList.remove('drag-over');
    
    if (draggedElement) {
        // نقل العنصر أو إنشاء نسخة جديدة
        if (draggedElement.closest('.drop-zone')) {
            // نقل من منطقة أخرى
            this.innerHTML = '';
            this.appendChild(draggedElement);
        } else {
            // إنشاء عنصر جديد من اللوحة
            const elementType = draggedElement.dataset.type;
            const newElement = createDraggableElement(elementType, '');
            this.innerHTML = '';
            this.appendChild(newElement);
        }
        
        draggedElement = null;
    }
}

// التعامل مع النقر على المنطقة
function handleZoneClick(event) {
    if (!this.querySelector('.draggable-element')) {
        // إظهار قائمة العناصر المتاحة
        showElementMenu(this);
    }
}

// إظهار قائمة العناصر
function showElementMenu(zone) {
    const menu = document.createElement('div');
    menu.className = 'element-menu position-absolute bg-white border rounded shadow-lg p-2';
    menu.style.zIndex = '1000';
    
    const elements = [
        {type: 'company_name', icon: 'building', text: 'اسم الشركة'},
        {type: 'logo', icon: 'image', text: 'الشعار'},
        {type: 'date', icon: 'calendar', text: 'التاريخ'},
        {type: 'page_number', icon: 'hashtag', text: 'رقم الصفحة'},
        {type: 'custom_text', icon: 'text-width', text: 'نص مخصص'}
    ];
    
    elements.forEach(el => {
        const button = document.createElement('button');
        button.className = 'btn btn-sm btn-outline-primary d-block w-100 mb-1';
        button.innerHTML = `<i class="fas fa-${el.icon} me-2"></i>${el.text}`;
        button.onclick = () => {
            const element = createDraggableElement(el.type, '');
            zone.innerHTML = '';
            zone.appendChild(element);
            menu.remove();
        };
        menu.appendChild(button);
    });
    
    // إضافة زر إلغاء
    const cancelBtn = document.createElement('button');
    cancelBtn.className = 'btn btn-sm btn-secondary d-block w-100';
    cancelBtn.innerHTML = 'إلغاء';
    cancelBtn.onclick = () => menu.remove();
    menu.appendChild(cancelBtn);
    
    // وضع القائمة في المكان المناسب
    zone.style.position = 'relative';
    zone.appendChild(menu);
    
    // إزالة القائمة عند النقر خارجها
    setTimeout(() => {
        document.addEventListener('click', function(e) {
            if (!menu.contains(e.target)) {
                menu.remove();
            }
        }, {once: true});
    }, 100);
}

// تحميل المستند
function loadDocument(documentType) {
    currentDocument = documentType;
    
    // تحديث القائمة الجانبية
    document.querySelectorAll('.document-list-item').forEach(item => {
        item.classList.remove('active');
    });
    document.querySelector(`[data-document-type="${documentType}"]`).classList.add('active');
    
    // إظهار معاينة المستند
    document.getElementById('noDocumentMessage').style.display = 'none';
    document.getElementById('headerSection').style.display = 'grid';
    document.getElementById('contentSection').style.display = 'block';
    document.getElementById('footerSection').style.display = 'grid';
    
    // تحميل إعدادات المستند
    loadDocumentSettings(documentType);
}

// تحميل إعدادات المستند من الخادم
function loadDocumentSettings(documentType) {
    fetch(`/ar/settings/api/document-settings/${documentType}/`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                currentSettings = data.settings;
                renderDocumentElements();
                updatePaperSize(currentSettings.paper_size || 'A4');
            } else {
                // إنشاء إعدادات افتراضية
                currentSettings = {
                    document_type: documentType,
                    paper_size: 'A4',
                    header_left_content: '',
                    header_center_content: '',
                    header_right_content: '',
                    footer_left_content: '',
                    footer_center_content: '',
                    footer_right_content: '',
                    show_logo: true,
                    logo_position: 'center'
                };
                renderDocumentElements();
            }
        })
        .catch(error => {
            console.error('خطأ في تحميل إعدادات المستند:', error);
            // إنشاء إعدادات افتراضية
            currentSettings = {
                document_type: documentType,
                paper_size: 'A4',
                show_logo: true,
                logo_position: 'center'
            };
            renderDocumentElements();
        });
}

// رسم عناصر المستند
function renderDocumentElements() {
    // مسح العناصر الحالية
    clearAllDropZones();
    
    // تحديث حجم واتجاه الورقة
    if (currentSettings.paper_size) {
        setPaperSize(currentSettings.paper_size);
    }
    if (currentSettings.orientation) {
        setPaperOrientation(currentSettings.orientation);
    }
    
    // رسم عناصر الرأس
    if (currentSettings.header_left_content) {
        addElementToZone('headerLeft', 'custom_text', currentSettings.header_left_content);
    }
    if (currentSettings.header_center_content) {
        addElementToZone('headerCenter', 'custom_text', currentSettings.header_center_content);
    }
    if (currentSettings.header_right_content) {
        addElementToZone('headerRight', 'custom_text', currentSettings.header_right_content);
    }
    
    // رسم عناصر التذييل
    if (currentSettings.footer_left_content) {
        addElementToZone('footerLeft', 'custom_text', currentSettings.footer_left_content);
    }
    if (currentSettings.footer_center_content) {
        addElementToZone('footerCenter', 'custom_text', currentSettings.footer_center_content);
    }
    if (currentSettings.footer_right_content) {
        addElementToZone('footerRight', 'custom_text', currentSettings.footer_right_content);
    }
    
    // إضافة الشعار إذا كان مفعلاً
    if (currentSettings.show_logo) {
        const logoPosition = currentSettings.logo_position || 'center';
        const zoneId = `header${logoPosition.charAt(0).toUpperCase() + logoPosition.slice(1)}`;
        addElementToZone(zoneId, 'logo', '');
    }
}

// إضافة عنصر إلى منطقة محددة
function addElementToZone(zoneId, elementType, content) {
    const zone = document.getElementById(zoneId);
    if (zone) {
        const element = createDraggableElement(elementType, content);
        zone.innerHTML = '';
        zone.appendChild(element);
    }
}

// مسح جميع مناطق الإسقاط
function clearAllDropZones() {
    const zones = ['headerLeft', 'headerCenter', 'headerRight', 'footerLeft', 'footerCenter', 'footerRight'];
    zones.forEach(zoneId => {
        const zone = document.getElementById(zoneId);
        if (zone) {
            const position = zone.dataset.position;
            const section = zone.closest('.preview-header') ? 'الرأس' : 'التذييل';
            const positionText = position === 'left' ? 'يسار' : position === 'center' ? 'وسط' : 'يمين';
            zone.innerHTML = `<span class="text-muted">${positionText} ${section}</span>`;
        }
    });
}

// إنشاء عنصر قابل للسحب
function createDraggableElement(type, content) {
    const element = document.createElement('div');
    element.className = 'draggable-element';
    element.draggable = true;
    element.dataset.type = type;
    element.dataset.content = content || '';
    
    let elementContent = '';
    switch(type) {
        case 'company_name':
            elementContent = `<i class="fas fa-building me-2"></i>اسم الشركة`;
            break;
        case 'logo':
            elementContent = `<i class="fas fa-image me-2"></i>الشعار`;
            break;
        case 'date':
            elementContent = `<i class="fas fa-calendar me-2"></i>${new Date().toLocaleDateString('ar-EG')}`;
            break;
        case 'page_number':
            elementContent = `<i class="fas fa-hashtag me-2"></i>صفحة 1`;
            break;
        case 'custom_text':
            elementContent = content || 'نص مخصص';
            element.dataset.content = content || 'نص مخصص';
            break;
    }
    
    element.innerHTML = elementContent;
    
    // إضافة أحداث
    element.addEventListener('dragstart', handleDragStart);
    element.addEventListener('click', selectElement);
    
    // إضافة أدوات التحكم
    addElementControls(element);
    
    return element;
}

// بداية السحب
function handleDragStart(event) {
    draggedElement = this;
    event.dataTransfer.effectAllowed = 'move';
}

// اختيار عنصر
function selectElement(event) {
    event.stopPropagation();
    
    // إزالة التحديد من العناصر الأخرى
    document.querySelectorAll('.draggable-element').forEach(el => {
        el.classList.remove('selected');
    });
    
    // تحديد العنصر الحالي
    this.classList.add('selected');
    selectedElement = this;
    showElementProperties(this);
}

// إظهار خصائص العنصر
function showElementProperties(element) {
    const panel = document.getElementById('propertiesPanel');
    const properties = document.getElementById('elementProperties');
    
    const type = element.dataset.type;
    const content = element.dataset.content;
    
    let propertiesHTML = '';
    
    switch(type) {
        case 'custom_text':
            propertiesHTML = `
                <div class="mb-3">
                    <label class="form-label">النص</label>
                    <textarea class="form-control" rows="3" onchange="updateElementContent(this.value)" oninput="updateElementContent(this.value)">${content || 'نص مخصص'}</textarea>
                </div>
                <div class="mb-3">
                    <label class="form-label">حجم الخط</label>
                    <select class="form-select" onchange="updateElementStyle('fontSize', this.value)">
                        <option value="12px">صغير</option>
                        <option value="14px" selected>متوسط</option>
                        <option value="16px">كبير</option>
                        <option value="18px">كبير جداً</option>
                    </select>
                </div>
                <div class="mb-3">
                    <label class="form-label">محاذاة النص</label>
                    <select class="form-select" onchange="updateElementStyle('textAlign', this.value)">
                        <option value="right">يمين</option>
                        <option value="center">وسط</option>
                        <option value="left">يسار</option>
                    </select>
                </div>
                <div class="mb-3">
                    <label class="form-label">لون النص</label>
                    <input type="color" class="form-control form-control-color" value="#000000" onchange="updateElementStyle('color', this.value)">
                </div>
            `;
            break;
        case 'logo':
            propertiesHTML = `
                <div class="mb-3">
                    <label class="form-label">حجم الشعار</label>
                    <select class="form-select" onchange="updateElementStyle('width', this.value)">
                        <option value="60px">صغير جداً</option>
                        <option value="80px">صغير</option>
                        <option value="120px" selected>متوسط</option>
                        <option value="160px">كبير</option>
                        <option value="200px">كبير جداً</option>
                    </select>
                </div>
                <div class="mb-3">
                    <label class="form-label">محاذاة الشعار</label>
                    <select class="form-select" onchange="updateElementStyle('textAlign', this.value)">
                        <option value="right">يمين</option>
                        <option value="center" selected>وسط</option>
                        <option value="left">يسار</option>
                    </select>
                </div>
            `;
            break;
        default:
            propertiesHTML = `
                <div class="mb-3">
                    <label class="form-label">حجم الخط</label>
                    <select class="form-select" onchange="updateElementStyle('fontSize', this.value)">
                        <option value="12px">صغير</option>
                        <option value="14px" selected>متوسط</option>
                        <option value="16px">كبير</option>
                        <option value="18px">كبير جداً</option>
                    </select>
                </div>
                <div class="mb-3">
                    <label class="form-label">محاذاة النص</label>
                    <select class="form-select" onchange="updateElementStyle('textAlign', this.value)">
                        <option value="right">يمين</option>
                        <option value="center">وسط</option>
                        <option value="left">يسار</option>
                    </select>
                </div>
            `;
    }
    
    properties.innerHTML = propertiesHTML;
    panel.classList.add('active');
}

// تحديث محتوى العنصر
function updateElementContent(newContent) {
    if (selectedElement) {
        selectedElement.dataset.content = newContent;
        const icon = selectedElement.querySelector('i');
        const iconHTML = icon ? icon.outerHTML : '';
        selectedElement.innerHTML = `${iconHTML} ${newContent}`;
        
        // إعادة إضافة أحداث العنصر
        selectedElement.addEventListener('dragstart', handleDragStart);
        selectedElement.addEventListener('click', selectElement);
        
        // إعادة إضافة أدوات التحكم
        addElementControls(selectedElement);
    }
}

// تحديث تنسيق العنصر
function updateElementStyle(property, value) {
    if (selectedElement) {
        selectedElement.style[property] = value;
    }
}

// إضافة أدوات التحكم للعنصر
function addElementControls(element) {
    // إزالة الأدوات القديمة
    const oldControls = element.querySelector('.element-controls');
    const oldResize = element.querySelector('.resize-handle');
    if (oldControls) oldControls.remove();
    if (oldResize) oldResize.remove();
    
    // إضافة أدوات جديدة
    const controls = document.createElement('div');
    controls.className = 'element-controls';
    controls.innerHTML = `
        <button class="control-btn bg-warning text-dark" onclick="editElement(this.parentElement.parentElement)" title="تعديل">
            <i class="fas fa-edit"></i>
        </button>
        <button class="control-btn bg-danger text-white" onclick="removeElement(this.parentElement.parentElement)" title="حذف">
            <i class="fas fa-times"></i>
        </button>
    `;
    element.appendChild(controls);
    
    // إضافة مقبض تغيير الحجم
    const resizeHandle = document.createElement('div');
    resizeHandle.className = 'resize-handle';
    resizeHandle.addEventListener('mousedown', initResize);
    element.appendChild(resizeHandle);
}

// حذف عنصر
function removeElement(element) {
    if (confirm('هل أنت متأكد من حذف هذا العنصر؟')) {
        const parent = element.parentElement;
        element.remove();
        
        // إعادة النص الافتراضي للمنطقة
        if (parent.children.length === 0) {
            const position = parent.dataset.position;
            const section = parent.closest('.preview-header') ? 'الرأس' : 'التذييل';
            const positionText = position === 'left' ? 'يسار' : position === 'center' ? 'وسط' : 'يمين';
            parent.innerHTML = `<span class="text-muted">${positionText} ${section}</span>`;
        }
        
        // إخفاء لوحة الخصائص
        document.getElementById('propertiesPanel').classList.remove('active');
        selectedElement = null;
    }
}

// تعديل عنصر
function editElement(element) {
    selectedElement = element;
    showElementProperties(element);
}

// تغيير حجم الورقة
function setPaperSize(size) {
    const preview = document.getElementById('documentPreview');
    const currentOrientation = preview.classList.contains('landscape') ? 'landscape' : 'portrait';
    preview.className = preview.className.replace(/paper-\w+/, `paper-${size.toLowerCase()}`);
    
    // الاحتفاظ بالاتجاه الحالي
    if (currentOrientation === 'landscape') {
        preview.classList.add('landscape');
    }
    
    // تحديث الأزرار
    document.querySelectorAll('[id$="Btn"]').forEach(btn => {
        if (btn.id.includes('portrait') || btn.id.includes('landscape')) return;
        btn.classList.remove('btn-primary');
        btn.classList.add('btn-outline-primary');
    });
    document.getElementById(`${size.toLowerCase()}Btn`).classList.remove('btn-outline-primary');
    document.getElementById(`${size.toLowerCase()}Btn`).classList.add('btn-primary');
    
    if (currentSettings) {
        currentSettings.paper_size = size;
    }
}

// تغيير اتجاه الورقة
function setPaperOrientation(orientation) {
    const preview = document.getElementById('documentPreview');
    
    if (orientation === 'landscape') {
        preview.classList.add('landscape');
    } else {
        preview.classList.remove('landscape');
    }
    
    // تحديث الأزرار
    document.getElementById('portraitBtn').classList.remove('btn-success');
    document.getElementById('portraitBtn').classList.add('btn-outline-success');
    document.getElementById('landscapeBtn').classList.remove('btn-success');
    document.getElementById('landscapeBtn').classList.add('btn-outline-success');
    
    document.getElementById(`${orientation}Btn`).classList.remove('btn-outline-success');
    document.getElementById(`${orientation}Btn`).classList.add('btn-success');
    
    if (currentSettings) {
        currentSettings.orientation = orientation;
    }
}

// حفظ التصميم الحالي
function saveCurrentDesign() {
    if (!currentDocument) {
        alert('لا يوجد مستند محدد للحفظ');
        return;
    }
    
    // جمع بيانات العناصر
    const headerLeft = document.getElementById('headerLeft').querySelector('.draggable-element');
    const headerCenter = document.getElementById('headerCenter').querySelector('.draggable-element');
    const headerRight = document.getElementById('headerRight').querySelector('.draggable-element');
    const footerLeft = document.getElementById('footerLeft').querySelector('.draggable-element');
    const footerCenter = document.getElementById('footerCenter').querySelector('.draggable-element');
    const footerRight = document.getElementById('footerRight').querySelector('.draggable-element');
    
    const data = {
        action: 'save_settings',
        document_type: currentDocument,
        paper_size: currentSettings.paper_size || 'A4',
        orientation: currentSettings.orientation || 'portrait',
        margins: currentSettings.margins || 20,
        header_left_content: headerLeft ? headerLeft.dataset.content : '',
        header_center_content: headerCenter ? headerCenter.dataset.content : '',
        header_right_content: headerRight ? headerRight.dataset.content : '',
        footer_left_content: footerLeft ? footerLeft.dataset.content : '',
        footer_center_content: footerCenter ? footerCenter.dataset.content : '',
        footer_right_content: footerRight ? footerRight.dataset.content : '',
        show_logo: document.querySelector('[data-type="logo"]') ? 'true' : 'false',
        logo_position: getLogoPosition()
    };
    
    // إرسال البيانات للخادم
    fetch('/ar/settings/print-design/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        },
        body: new URLSearchParams(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('تم حفظ التصميم بنجاح');
        } else {
            alert('حدث خطأ في حفظ التصميم: ' + (data.error || 'خطأ غير معروف'));
        }
    })
    .catch(error => {
        console.error('خطأ في حفظ التصميم:', error);
        alert('حدث خطأ في حفظ التصميم');
    });
}

// الحصول على موقع الشعار
function getLogoPosition() {
    const logoElement = document.querySelector('[data-type="logo"]');
    if (!logoElement) return 'center';
    
    const parent = logoElement.parentElement;
    if (parent.id === 'headerLeft' || parent.id === 'footerLeft') return 'left';
    if (parent.id === 'headerRight' || parent.id === 'footerRight') return 'right';
    return 'center';
}

// إضافة عنصر جديد من اللوحة
function addElement(type) {
    if (!currentDocument) {
        alert('يرجى اختيار مستند أولاً');
        return;
    }
    
    const element = createDraggableElement(type, '');
    element.style.position = 'fixed';
    element.style.top = '50%';
    element.style.left = '50%';
    element.style.transform = 'translate(-50%, -50%)';
    element.style.zIndex = '1000';
    element.style.background = 'white';
    element.style.border = '2px solid #007bff';
    
    document.body.appendChild(element);
    selectElement.call(element, new Event('click'));
    
    // إزالة العنصر بعد ثانيتين إذا لم يتم سحبه
    setTimeout(() => {
        if (element.parentElement === document.body) {
            element.remove();
        }
    }, 3000);
}

// إضافة مستند جديد
function addNewDocument() {
    const modal = new bootstrap.Modal(document.getElementById('addDocumentModal'));
    modal.show();
}

// إنشاء مستند جديد
function createDocument() {
    const type = document.getElementById('newDocumentType').value;
    const nameAr = document.getElementById('newDocumentNameAr').value;
    const nameEn = document.getElementById('newDocumentNameEn').value;
    const paperSize = document.getElementById('newPaperSize').value;
    
    if (!type || !nameAr || !nameEn) {
        alert('يرجى ملء جميع الحقول المطلوبة');
        return;
    }
    
    // إرسال البيانات للخادم
    const data = {
        action: 'save_settings',
        document_type: type,
        document_name_ar: nameAr,
        document_name_en: nameEn,
        paper_size: paperSize,
        orientation: 'portrait',
        margins: 20
    };
    
    fetch('/ar/settings/print-design/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        },
        body: new URLSearchParams(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            location.reload();
        } else {
            alert('حدث خطأ في إنشاء المستند: ' + (data.error || 'خطأ غير معروف'));
        }
    })
    .catch(error => {
        console.error('خطأ في إنشاء المستند:', error);
        alert('حدث خطأ في إنشاء المستند');
    });
}

// حذف مستند
function deleteDocument(event, documentId, documentName) {
    event.stopPropagation();
    
    if (confirm(`هل أنت متأكد من حذف إعدادات طباعة "${documentName}"؟`)) {
        fetch('/ar/settings/print-design/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            },
            body: new URLSearchParams({
                action: 'delete_settings',
                document_id: documentId
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                location.reload();
            } else {
                alert('حدث خطأ في حذف المستند: ' + (data.error || 'خطأ غير معروف'));
            }
        })
        .catch(error => {
            console.error('خطأ في حذف المستند:', error);
            alert('حدث خطأ في حذف المستند');
        });
    }
}

// إنشاء مستند جديد من القائمة
function createNewDocument(type, nameAr, nameEn) {
    document.getElementById('newDocumentType').value = type;
    document.getElementById('newDocumentNameAr').value = nameAr;
    document.getElementById('newDocumentNameEn').value = nameEn;
    addNewDocument();
}

// تهيئة تغيير الحجم
function initResize(event) {
    if (isResizing) return;
    
    event.preventDefault();
    event.stopPropagation();
    isResizing = true;
    
    const element = event.target.parentElement;
    const startX = event.clientX;
    const startY = event.clientY;
    const startWidth = parseInt(document.defaultView.getComputedStyle(element).width, 10);
    const startHeight = parseInt(document.defaultView.getComputedStyle(element).height, 10);
    
    function doResize(e) {
        const newWidth = Math.max(50, startWidth + e.clientX - startX);
        const newHeight = Math.max(30, startHeight + e.clientY - startY);
        element.style.width = newWidth + 'px';
        element.style.height = newHeight + 'px';
    }
    
    function stopResize() {
        isResizing = false;
        document.removeEventListener('mousemove', doResize);
        document.removeEventListener('mouseup', stopResize);
    }
    
    document.addEventListener('mousemove', doResize);
    document.addEventListener('mouseup', stopResize);
}

// إضافة CSRF token
function addCSRFToken() {
    if (!document.querySelector('[name=csrfmiddlewaretoken]')) {
        const csrfInput = document.createElement('input');
        csrfInput.type = 'hidden';
        csrfInput.name = 'csrfmiddlewaretoken';
        csrfInput.value = document.querySelector('[name=csrfmiddlewaretoken]')?.value || getCookie('csrftoken');
        document.body.appendChild(csrfInput);
    }
}

// الحصول على cookie
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// تصدير البيانات (للاستخدام المستقبلي)
function exportDesign() {
    if (!currentDocument) {
        alert('لا يوجد مستند محدد للتصدير');
        return;
    }
    
    const designData = {
        document_type: currentDocument,
        settings: currentSettings,
        elements: []
    };
    
    // جمع العناصر
    document.querySelectorAll('.draggable-element').forEach(element => {
        const rect = element.getBoundingClientRect();
        const parent = element.parentElement;
        
        designData.elements.push({
            type: element.dataset.type,
            content: element.dataset.content,
            position: parent.dataset.position,
            section: parent.dataset.section,
            styles: {
                width: element.style.width,
                height: element.style.height,
                fontSize: element.style.fontSize,
                color: element.style.color,
                textAlign: element.style.textAlign
            }
        });
    });
    
    // تحويل إلى JSON وتنزيل
    const dataStr = JSON.stringify(designData, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
    
    const exportFileDefaultName = `${currentDocument}_design.json`;
    
    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();
}
