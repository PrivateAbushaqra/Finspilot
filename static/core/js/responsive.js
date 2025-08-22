/* JavaScript لتحسين الاستجابة */
/* JavaScript for Responsive Enhancements */

document.addEventListener('DOMContentLoaded', function() {
    
    // إضافة فئات CSS حسب حجم الشاشة
    function updateScreenSizeClasses() {
        const body = document.body;
        const width = window.innerWidth;
        
        // إزالة الفئات السابقة
        body.classList.remove('screen-xs', 'screen-sm', 'screen-md', 'screen-lg', 'screen-xl');
        
        // إضافة الفئة المناسبة
        if (width < 576) {
            body.classList.add('screen-xs');
        } else if (width < 768) {
            body.classList.add('screen-sm');
        } else if (width < 992) {
            body.classList.add('screen-md');
        } else if (width < 1200) {
            body.classList.add('screen-lg');
        } else {
            body.classList.add('screen-xl');
        }
    }
    
    // تطبيق الفئات عند التحميل وعند تغيير حجم النافذة
    updateScreenSizeClasses();
    window.addEventListener('resize', updateScreenSizeClasses);
    
    // تحسين الجداول للشاشات الصغيرة
    function enhanceTablesForMobile() {
        const tables = document.querySelectorAll('.table-responsive table');
        
        tables.forEach(table => {
            if (window.innerWidth < 768) {
                // إضافة scroll أفقي سلس
                table.parentElement.style.overflowX = 'auto';
                table.parentElement.style.webkitOverflowScrolling = 'touch';
                
                // إخفاء أعمدة غير مهمة
                const headers = table.querySelectorAll('th');
                const rows = table.querySelectorAll('tbody tr');
                
                headers.forEach((header, index) => {
                    if (header.classList.contains('d-none-mobile')) {
                        header.style.display = 'none';
                        rows.forEach(row => {
                            const cell = row.cells[index];
                            if (cell) cell.style.display = 'none';
                        });
                    }
                });
            }
        });
    }
    
    // تحسين القوائم المنسدلة للشاشات الصغيرة
    function enhanceDropdownsForMobile() {
        const dropdowns = document.querySelectorAll('.dropdown');
        
        dropdowns.forEach(dropdown => {
            const toggle = dropdown.querySelector('.dropdown-toggle');
            const menu = dropdown.querySelector('.dropdown-menu');
            
            if (toggle && menu && window.innerWidth < 768) {
                // تحويل القائمة المنسدلة إلى قائمة مكشوفة على الشاشات الصغيرة
                toggle.addEventListener('click', function(e) {
                    e.preventDefault();
                    menu.classList.toggle('show');
                    menu.style.position = 'static';
                    menu.style.transform = 'none';
                });
            }
        });
    }
    
    // تحسين النماذج للشاشات الصغيرة
    function enhanceFormsForMobile() {
        if (window.innerWidth < 768) {
            const formRows = document.querySelectorAll('.row:has(.form-control, .form-select)');
            
            formRows.forEach(row => {
                const cols = row.querySelectorAll('[class*="col-"]');
                cols.forEach(col => {
                    col.classList.add('col-12');
                    col.classList.remove('col-md-6', 'col-lg-4', 'col-xl-3');
                });
            });
        }
    }
    
    // إضافة زر القائمة الجانبية للشاشات الصغيرة
    function addMobileSidebarToggle() {
        const sidebar = document.querySelector('.sidebar');
        const navbar = document.querySelector('.navbar');
        
        if (sidebar && navbar && window.innerWidth < 992) {
            // البحث عن زر القائمة الموجود أو إنشاء واحد جديد
            let toggleBtn = navbar.querySelector('.sidebar-toggle');
            
            if (!toggleBtn) {
                toggleBtn = document.createElement('button');
                toggleBtn.className = 'btn btn-outline-light sidebar-toggle d-lg-none';
                toggleBtn.innerHTML = '<i class="fas fa-bars"></i>';
                
                // إضافة الزر في بداية navbar
                const navbarBrand = navbar.querySelector('.navbar-brand');
                if (navbarBrand) {
                    navbarBrand.parentNode.insertBefore(toggleBtn, navbarBrand);
                }
            }
            
            // إضافة وظيفة التبديل
            toggleBtn.addEventListener('click', function() {
                sidebar.classList.toggle('show');
                
                // إضافة overlay
                let overlay = document.querySelector('.sidebar-overlay');
                if (!overlay) {
                    overlay = document.createElement('div');
                    overlay.className = 'sidebar-overlay';
                    overlay.style.cssText = `
                        position: fixed;
                        top: 0;
                        left: 0;
                        width: 100%;
                        height: 100%;
                        background: rgba(0,0,0,0.5);
                        z-index: 999;
                        display: none;
                    `;
                    document.body.appendChild(overlay);
                }
                
                if (sidebar.classList.contains('show')) {
                    overlay.style.display = 'block';
                } else {
                    overlay.style.display = 'none';
                }
                
                // إغلاق القائمة عند النقر على overlay
                overlay.addEventListener('click', function() {
                    sidebar.classList.remove('show');
                    overlay.style.display = 'none';
                });
            });
        }
    }
    
    // تحسين الرسوم البيانية للشاشات الصغيرة
    function enhanceChartsForMobile() {
        const chartContainers = document.querySelectorAll('.chart-container, [id*="chart"]');
        
        chartContainers.forEach(container => {
            if (window.innerWidth < 768) {
                container.style.height = '250px';
                
                // إذا كان يحتوي على رسم بياني Chart.js
                const canvas = container.querySelector('canvas');
                if (canvas && canvas.chart) {
                    canvas.chart.resize();
                }
            }
        });
    }
    
    // تحسين الأزرار للشاشات الصغيرة
    function enhanceButtonsForMobile() {
        if (window.innerWidth < 576) {
            const btnGroups = document.querySelectorAll('.btn-group');
            
            btnGroups.forEach(group => {
                group.classList.add('btn-group-vertical');
                group.classList.remove('btn-group');
                
                // تحسين المسافات
                const buttons = group.querySelectorAll('.btn');
                buttons.forEach((btn, index) => {
                    if (index > 0) {
                        btn.style.marginTop = '0.25rem';
                    }
                });
            });
        }
    }
    
    // تحسين التنبيهات للشاشات الصغيرة
    function enhanceAlertsForMobile() {
        const alerts = document.querySelectorAll('.alert');
        
        alerts.forEach(alert => {
            if (window.innerWidth < 576) {
                alert.style.borderRadius = '0';
                alert.style.marginLeft = '-15px';
                alert.style.marginRight = '-15px';
            }
        });
    }
    
    // إضافة إيماءات اللمس للجداول
    function addTouchGestures() {
        const tables = document.querySelectorAll('.table-responsive');
        
        tables.forEach(table => {
            let startX = 0;
            let scrollLeft = 0;
            
            table.addEventListener('touchstart', function(e) {
                startX = e.touches[0].pageX - table.offsetLeft;
                scrollLeft = table.scrollLeft;
            });
            
            table.addEventListener('touchmove', function(e) {
                e.preventDefault();
                const x = e.touches[0].pageX - table.offsetLeft;
                const walk = (x - startX) * 2;
                table.scrollLeft = scrollLeft - walk;
            });
        });
    }
    
    // تطبيق جميع التحسينات
    function applyAllEnhancements() {
        enhanceTablesForMobile();
        enhanceDropdownsForMobile();
        enhanceFormsForMobile();
        addMobileSidebarToggle();
        enhanceChartsForMobile();
        enhanceButtonsForMobile();
        enhanceAlertsForMobile();
        addTouchGestures();
    }
    
    // تطبيق التحسينات عند التحميل وعند تغيير حجم النافذة
    applyAllEnhancements();
    
    let resizeTimer;
    window.addEventListener('resize', function() {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(function() {
            applyAllEnhancements();
        }, 250);
    });
    
    // تحسين الأداء: lazy loading للصور
    function enableLazyLoading() {
        const images = document.querySelectorAll('img[data-src]');
        
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.classList.remove('lazy');
                    imageObserver.unobserve(img);
                }
            });
        });
        
        images.forEach(img => imageObserver.observe(img));
    }
    
    // تفعيل lazy loading إذا كان متاحاً
    if ('IntersectionObserver' in window) {
        enableLazyLoading();
    }
    
    // إضافة مؤشر تحميل للعمليات الطويلة
    function addLoadingIndicators() {
        const forms = document.querySelectorAll('form');
        
        forms.forEach(form => {
            form.addEventListener('submit', function() {
                const submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
                
                if (submitBtn) {
                    submitBtn.disabled = true;
                    const originalText = submitBtn.innerHTML;
                    submitBtn.innerHTML = `<i class="fas fa-spinner fa-spin me-2"></i>جاري التحميل...`;
                    
                    // إعادة تفعيل الزر بعد 5 ثوانٍ (تجنباً للحالات الاستثنائية)
                    setTimeout(() => {
                        submitBtn.disabled = false;
                        submitBtn.innerHTML = originalText;
                    }, 5000);
                }
            });
        });
    }
    
    addLoadingIndicators();
    
    // إضافة دعم للوضع المظلم (حسب تفضيل النظام)
    function handleDarkMode() {
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            document.body.classList.add('dark-mode');
        }
        
        // مراقبة تغيير تفضيل الوضع المظلم
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
            if (e.matches) {
                document.body.classList.add('dark-mode');
            } else {
                document.body.classList.remove('dark-mode');
            }
        });
    }
    
    handleDarkMode();
});

// دوال مساعدة عامة للاستجابة
window.ResponsiveUtils = {
    
    // التحقق من نوع الجهاز
    isMobile: () => window.innerWidth < 768,
    isTablet: () => window.innerWidth >= 768 && window.innerWidth < 992,
    isDesktop: () => window.innerWidth >= 992,
    
    // إخفاء/إظهار العناصر حسب حجم الشاشة
    hideOnMobile: (selector) => {
        const elements = document.querySelectorAll(selector);
        elements.forEach(el => {
            if (window.innerWidth < 768) {
                el.style.display = 'none';
            } else {
                el.style.display = '';
            }
        });
    },
    
    // تحسين الجداول للطباعة على الأجهزة المحمولة
    optimizeTableForPrint: (tableSelector) => {
        const table = document.querySelector(tableSelector);
        if (table && window.innerWidth < 768) {
            table.style.fontSize = '8px';
            table.style.lineHeight = '1.2';
            
            const cells = table.querySelectorAll('th, td');
            cells.forEach(cell => {
                cell.style.padding = '2px';
                cell.style.wordBreak = 'break-word';
            });
        }
    }
};
