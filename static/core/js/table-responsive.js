// تحسينات JavaScript للجداول المستجيبة
document.addEventListener('DOMContentLoaded', function() {
    // تحويل الجداول إلى بطاقات على الأجهزة المحمولة
    function createMobileCards() {
        const tables = document.querySelectorAll('.table-responsive table');
        
        tables.forEach(table => {
            const mobileContainer = createMobileContainer(table);
            
            // إخفاء الجدول وإظهار البطاقات على الشاشات الصغيرة
            if (window.innerWidth <= 576) {
                table.style.display = 'none';
                mobileContainer.style.display = 'block';
            } else {
                table.style.display = 'table';
                mobileContainer.style.display = 'none';
            }
        });
    }
    
    function createMobileContainer(table) {
        let mobileContainer = table.parentNode.querySelector('.mobile-cards');
        
        if (!mobileContainer) {
            mobileContainer = document.createElement('div');
            mobileContainer.className = 'mobile-cards';
            table.parentNode.appendChild(mobileContainer);
        }
        
        // مسح المحتوى السابق
        mobileContainer.innerHTML = '';
        
        const headers = Array.from(table.querySelectorAll('thead th')).map(th => th.textContent.trim());
        const rows = table.querySelectorAll('tbody tr');
        
        rows.forEach(row => {
            const card = createMobileCard(row, headers);
            mobileContainer.appendChild(card);
        });
        
        return mobileContainer;
    }
    
    function createMobileCard(row, headers) {
        const card = document.createElement('div');
        card.className = 'mobile-card';
        
        const cells = row.querySelectorAll('td');
        
        // إنشاء عنوان البطاقة من أول خلية
        if (cells.length > 0) {
            const header = document.createElement('div');
            header.className = 'mobile-card-header';
            header.textContent = cells[0].textContent.trim();
            card.appendChild(header);
        }
        
        // إنشاء صفوف البيانات
        cells.forEach((cell, index) => {
            if (index === 0) return; // تجاهل أول خلية لأنها في العنوان
            
            const cardRow = document.createElement('div');
            cardRow.className = 'mobile-card-row';
            
            const label = document.createElement('span');
            label.className = 'mobile-card-label';
            label.textContent = headers[index] || `العمود ${index + 1}`;
            
            const value = document.createElement('span');
            value.className = 'mobile-card-value';
            value.innerHTML = cell.innerHTML;
            
            cardRow.appendChild(label);
            cardRow.appendChild(value);
            card.appendChild(cardRow);
        });
        
        return card;
    }
    
    // تحسين أزرار الإجراءات للأجهزة المحمولة
    function optimizeActionButtons() {
        const actionCells = document.querySelectorAll('.table td:last-child');
        
        actionCells.forEach(cell => {
            const buttons = cell.querySelectorAll('.btn');
            
            if (buttons.length > 2 && window.innerWidth <= 576) {
                // إنشاء قائمة منسدلة للأزرار الكثيرة
                const dropdown = createActionDropdown(buttons);
                cell.innerHTML = '';
                cell.appendChild(dropdown);
            }
        });
    }
    
    function createActionDropdown(buttons) {
        const dropdown = document.createElement('div');
        dropdown.className = 'dropdown';
        
        const toggle = document.createElement('button');
        toggle.className = 'btn btn-outline-secondary btn-sm dropdown-toggle';
        toggle.setAttribute('data-bs-toggle', 'dropdown');
        toggle.innerHTML = '<i class="fas fa-ellipsis-v"></i>';
        
        const menu = document.createElement('div');
        menu.className = 'dropdown-menu';
        
        buttons.forEach(button => {
            const item = document.createElement('a');
            item.className = 'dropdown-item';
            item.href = button.href || '#';
            item.onclick = button.onclick;
            item.innerHTML = button.innerHTML;
            menu.appendChild(item);
        });
        
        dropdown.appendChild(toggle);
        dropdown.appendChild(menu);
        
        return dropdown;
    }
    
    // تحسين عرض البيانات الطويلة
    function truncateLongText() {
        const cells = document.querySelectorAll('.table td');
        
        cells.forEach(cell => {
            const text = cell.textContent.trim();
            
            if (text.length > 30 && window.innerWidth <= 768) {
                const shortText = text.substring(0, 27) + '...';
                const originalHtml = cell.innerHTML;
                
                cell.innerHTML = shortText;
                cell.title = text;
                
                // إضافة إمكانية النقر لإظهار النص الكامل
                cell.style.cursor = 'pointer';
                cell.addEventListener('click', function() {
                    if (cell.innerHTML === shortText) {
                        cell.innerHTML = originalHtml;
                    } else {
                        cell.innerHTML = shortText;
                    }
                });
            }
        });
    }
    
    // تحسين التمرير الأفقي للجداول
    function enhanceHorizontalScroll() {
        const tableContainers = document.querySelectorAll('.table-responsive');
        
        tableContainers.forEach(container => {
            if (container.scrollWidth > container.clientWidth) {
                // إضافة مؤشرات التمرير
                container.classList.add('has-scroll');
                
                // إضافة أحداث التمرير
                container.addEventListener('scroll', function() {
                    const scrollLeft = container.scrollLeft;
                    const maxScroll = container.scrollWidth - container.clientWidth;
                    
                    if (scrollLeft === 0) {
                        container.classList.add('scroll-at-start');
                        container.classList.remove('scroll-at-end');
                    } else if (scrollLeft >= maxScroll - 1) {
                        container.classList.add('scroll-at-end');
                        container.classList.remove('scroll-at-start');
                    } else {
                        container.classList.remove('scroll-at-start', 'scroll-at-end');
                    }
                });
                
                // تشغيل الحدث مرة واحدة لتعيين الحالة الأولية
                container.dispatchEvent(new Event('scroll'));
            }
        });
    }
    
    // تحسين فلترة الجداول
    function enhanceTableFiltering() {
        const searchInputs = document.querySelectorAll('input[data-table-search]');
        
        searchInputs.forEach(input => {
            const tableId = input.getAttribute('data-table-search');
            const table = document.getElementById(tableId) || document.querySelector(tableId);
            
            if (table) {
                input.addEventListener('input', function() {
                    const searchTerm = input.value.toLowerCase();
                    const rows = table.querySelectorAll('tbody tr');
                    
                    rows.forEach(row => {
                        const text = row.textContent.toLowerCase();
                        if (text.includes(searchTerm)) {
                            row.style.display = '';
                        } else {
                            row.style.display = 'none';
                        }
                    });
                });
            }
        });
    }
    
    // تطبيق جميع التحسينات
    function applyEnhancements() {
        createMobileCards();
        optimizeActionButtons();
        truncateLongText();
        enhanceHorizontalScroll();
        enhanceTableFiltering();
    }
    
    // تشغيل التحسينات عند تحميل الصفحة
    applyEnhancements();
    
    // إعادة تطبيق التحسينات عند تغيير حجم النافذة
    let resizeTimeout;
    window.addEventListener('resize', function() {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(applyEnhancements, 250);
    });
    
    // تحسين لمسة الأجهزة المحمولة
    if ('ontouchstart' in window) {
        document.body.classList.add('touch-device');
        
        // تحسين النقر على صفوف الجدول
        const tableRows = document.querySelectorAll('.table tbody tr');
        tableRows.forEach(row => {
            row.addEventListener('touchstart', function() {
                row.classList.add('touch-active');
            });
            
            row.addEventListener('touchend', function() {
                setTimeout(() => {
                    row.classList.remove('touch-active');
                }, 150);
            });
        });
    }
    
    // إضافة إمكانية السحب للتمرير الأفقي
    const tables = document.querySelectorAll('.table-responsive');
    tables.forEach(table => {
        let isDown = false;
        let startX;
        let scrollLeft;
        
        table.addEventListener('mousedown', (e) => {
            isDown = true;
            table.classList.add('active');
            startX = e.pageX - table.offsetLeft;
            scrollLeft = table.scrollLeft;
        });
        
        table.addEventListener('mouseleave', () => {
            isDown = false;
            table.classList.remove('active');
        });
        
        table.addEventListener('mouseup', () => {
            isDown = false;
            table.classList.remove('active');
        });
        
        table.addEventListener('mousemove', (e) => {
            if (!isDown) return;
            e.preventDefault();
            const x = e.pageX - table.offsetLeft;
            const walk = (x - startX) * 2;
            table.scrollLeft = scrollLeft - walk;
        });
    });
});

// CSS إضافي للتحسينات
const additionalCSS = `
.has-scroll {
    position: relative;
}

.has-scroll::before,
.has-scroll::after {
    content: '';
    position: absolute;
    top: 0;
    bottom: 0;
    width: 10px;
    pointer-events: none;
    z-index: 2;
    transition: opacity 0.3s ease;
}

.has-scroll::before {
    left: 0;
    background: linear-gradient(to right, rgba(255,255,255,1), rgba(255,255,255,0));
    opacity: 0;
}

.has-scroll::after {
    right: 0;
    background: linear-gradient(to left, rgba(255,255,255,1), rgba(255,255,255,0));
    opacity: 1;
}

.has-scroll.scroll-at-start::before {
    opacity: 0;
}

.has-scroll.scroll-at-end::after {
    opacity: 0;
}

.has-scroll:not(.scroll-at-start):not(.scroll-at-end)::before,
.has-scroll:not(.scroll-at-start):not(.scroll-at-end)::after {
    opacity: 1;
}

.touch-device .table tbody tr.touch-active {
    background-color: #e9ecef;
    transform: scale(0.98);
    transition: all 0.1s ease;
}

.table-responsive.active {
    cursor: grabbing;
    cursor: -webkit-grabbing;
}

.table-responsive {
    cursor: grab;
    cursor: -webkit-grab;
}

@media (max-width: 576px) {
    .mobile-cards {
        display: block;
    }
    
    .table-stack-mobile {
        display: none !important;
    }
}
`;

// إضافة CSS إضافي
const style = document.createElement('style');
style.textContent = additionalCSS;
document.head.appendChild(style);
