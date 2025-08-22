// FinsPilot Accounting System JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Auto-dismiss alerts after 5 seconds
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);

    // Format numbers with thousand separators
    function formatNumber(num) {
        return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    }

    // Format currency
    function formatCurrency(amount, currency = 'JOD') {
        return `${formatNumber(amount.toFixed(3))} ${currency}`;
    }

    // Confirm delete actions
    const deleteButtons = document.querySelectorAll('.btn-delete');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            if (confirm('هل أنت متأكد من الحذف؟')) {
                window.location.href = this.href;
            }
        });
    });

    // Form validation
    const forms = document.querySelectorAll('.needs-validation');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!form.checkValidity()) {
                e.preventDefault();
                e.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });

    // Calculate totals in forms
    function calculateTotals() {
        let subtotal = 0;
        let totalTax = 0;
        
        const rows = document.querySelectorAll('.item-row');
        rows.forEach(row => {
            const quantity = parseFloat(row.querySelector('.quantity')?.value || 0);
            const price = parseFloat(row.querySelector('.price')?.value || 0);
            const taxRate = parseFloat(row.querySelector('.tax-rate')?.value || 0);
            
            const lineTotal = quantity * price;
            const lineTax = lineTotal * (taxRate / 100);
            
            subtotal += lineTotal;
            totalTax += lineTax;
            
            // Update line total display
            const lineTotalElement = row.querySelector('.line-total');
            if (lineTotalElement) {
                lineTotalElement.textContent = formatCurrency(lineTotal + lineTax);
            }
        });
        
        // Update totals
        const subtotalElement = document.getElementById('subtotal');
        const taxElement = document.getElementById('total-tax');
        const totalElement = document.getElementById('total');
        const discountElement = document.getElementById('discount');
        
        if (subtotalElement) subtotalElement.textContent = formatCurrency(subtotal);
        if (taxElement) taxElement.textContent = formatCurrency(totalTax);
        
        const discount = parseFloat(discountElement?.value || 0);
        const total = subtotal + totalTax - discount;
        
        if (totalElement) totalElement.textContent = formatCurrency(total);
    }

    // Add event listeners for calculation
    document.addEventListener('input', function(e) {
        if (e.target.classList.contains('quantity') || 
            e.target.classList.contains('price') || 
            e.target.classList.contains('tax-rate') ||
            e.target.id === 'discount') {
            calculateTotals();
        }
    });

    // Add new item row
    window.addItemRow = function() {
        const template = document.getElementById('item-row-template');
        if (template) {
            const newRow = template.cloneNode(true);
            newRow.style.display = 'table-row';
            newRow.id = '';
            document.querySelector('#items-table tbody').appendChild(newRow);
        }
    };

    // Remove item row
    window.removeItemRow = function(button) {
        button.closest('tr').remove();
        calculateTotals();
    };

    // Search functionality
    const searchInput = document.getElementById('search');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            const tableRows = document.querySelectorAll('tbody tr');
            
            tableRows.forEach(row => {
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(searchTerm) ? '' : 'none';
            });
        });
    }

    // Print functionality
    window.printPage = function() {
        window.print();
    };

    // Export functionality
    window.exportData = function(format) {
        // Implementation for data export
        console.log(`Exporting data in ${format} format`);
    };

    // Sidebar toggle for mobile
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const sidebar = document.querySelector('.sidebar');
    
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', function() {
            sidebar.classList.toggle('show');
        });
    }

    // Close sidebar when clicking outside on mobile
    document.addEventListener('click', function(e) {
        if (window.innerWidth <= 768) {
            const sidebar = document.querySelector('.sidebar');
            const sidebarToggle = document.getElementById('sidebar-toggle');
            
            if (sidebar && !sidebar.contains(e.target) && e.target !== sidebarToggle) {
                sidebar.classList.remove('show');
            }
        }
    });

    // Loading state management
    window.showLoading = function() {
        document.querySelector('.loading').style.display = 'block';
    };

    window.hideLoading = function() {
        document.querySelector('.loading').style.display = 'none';
    };

    // AJAX form submission
    window.submitForm = function(form, callback) {
        showLoading();
        
        const formData = new FormData(form);
        
        fetch(form.action, {
            method: form.method,
            body: formData,
            headers: {
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            }
        })
        .then(response => response.json())
        .then(data => {
            hideLoading();
            if (callback) callback(data);
        })
        .catch(error => {
            hideLoading();
            console.error('Error:', error);
            alert('حدث خطأ أثناء معالجة الطلب');
        });
    };

    // Auto-save functionality
    let autoSaveTimer;
    window.enableAutoSave = function(form, interval = 30000) {
        autoSaveTimer = setInterval(() => {
            const formData = new FormData(form);
            
            fetch(form.action + '?auto_save=1', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                }
            });
        }, interval);
    };

    window.disableAutoSave = function() {
        if (autoSaveTimer) {
            clearInterval(autoSaveTimer);
        }
    };
});

// Global utility functions
window.FinsPilot = {
    formatNumber: function(num) {
        return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    },
    
    formatCurrency: function(amount, currency = 'JOD') {
        return `${this.formatNumber(amount.toFixed(3))} ${currency}`;
    },
    
    showAlert: function(message, type = 'info') {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        const container = document.querySelector('.main-content');
        container.insertBefore(alertDiv, container.firstChild);
        
        setTimeout(() => {
            alertDiv.remove();
        }, 5000);
    },
    
    confirm: function(message, callback) {
        if (confirm(message)) {
            callback();
        }
    }
};
