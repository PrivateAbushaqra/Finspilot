/**
 * نظام إدارة الجلسة وانتهاء الصلاحية
 * يتعامل مع انتهاء الجلسة التلقائي وتحذير المستخدمين
 */

class SessionManager {
    constructor() {
        this.warningTime = 5; // تحذير قبل 5 دقائق من انتهاء الجلسة
        this.timeoutMinutes = 30; // القيمة الافتراضية
        this.enableTimeout = true;
        this.logoutOnBrowserClose = true;
        this.warningTimer = null;
        this.sessionTimer = null;
        this.warningShown = false;
        
        this.init();
    }
    
    init() {
        // تحميل إعدادات الجلسة من الخادم
        this.loadSessionSettings();
        
        // إعداد مراقبة النشاط
        this.setupActivityMonitoring();
        
        // إعداد مراقبة إغلاق المتصفح
        this.setupBrowserCloseDetection();
        
        // إعداد معالجة طلبات AJAX
        this.setupAjaxErrorHandling();
    }
    
    loadSessionSettings() {
        // محاولة تحميل الإعدادات من meta tags أو API
        const metaTimeout = document.querySelector('meta[name="session-timeout"]');
        const metaEnable = document.querySelector('meta[name="session-timeout-enabled"]');
        const metaLogoutOnClose = document.querySelector('meta[name="logout-on-browser-close"]');
        
        if (metaTimeout) {
            this.timeoutMinutes = parseInt(metaTimeout.content) || 30;
        }
        if (metaEnable) {
            this.enableTimeout = metaEnable.content === 'true';
        }
        if (metaLogoutOnClose) {
            this.logoutOnBrowserClose = metaLogoutOnClose.content === 'true';
        }
        
        if (this.enableTimeout) {
            this.startSessionTimer();
        }
    }
    
    startSessionTimer() {
        this.clearTimers();
        
        // تحذير قبل انتهاء الجلسة
        const warningTimeMs = (this.timeoutMinutes - this.warningTime) * 60 * 1000;
        this.warningTimer = setTimeout(() => {
            this.showSessionWarning();
        }, warningTimeMs);
        
        // انتهاء الجلسة الفعلي
        const sessionTimeMs = this.timeoutMinutes * 60 * 1000;
        this.sessionTimer = setTimeout(() => {
            this.handleSessionExpired();
        }, sessionTimeMs);
    }
    
    clearTimers() {
        if (this.warningTimer) {
            clearTimeout(this.warningTimer);
            this.warningTimer = null;
        }
        if (this.sessionTimer) {
            clearTimeout(this.sessionTimer);
            this.sessionTimer = null;
        }
        this.warningShown = false;
    }
    
    resetSessionTimer() {
        if (this.enableTimeout) {
            this.startSessionTimer();
        }
    }
    
    setupActivityMonitoring() {
        // الأحداث التي تعتبر نشاطاً من المستخدم
        const events = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart', 'click'];
        
        let lastActivity = Date.now();
        const throttleTime = 30000; // تحديث كل 30 ثانية كحد أقصى
        
        const updateActivity = () => {
            const now = Date.now();
            if (now - lastActivity > throttleTime) {
                lastActivity = now;
                this.resetSessionTimer();
                this.hideSessionWarning();
            }
        };
        
        events.forEach(event => {
            document.addEventListener(event, updateActivity, true);
        });
    }
    
    setupBrowserCloseDetection() {
        if (this.logoutOnBrowserClose) {
            window.addEventListener('beforeunload', (e) => {
                // إرسال طلب تسجيل خروج عند إغلاق المتصفح
                try {
                    const lang = (document.documentElement.getAttribute('lang') || 'ar').split('-')[0];
                    const url = `/${lang}/auth/logout/`;
                    navigator.sendBeacon(url, new FormData());
                } catch (err) {
                    navigator.sendBeacon('/logout/', new FormData());
                }
            });
            
            // معالجة إغلاق التبويب
            document.addEventListener('visibilitychange', () => {
                if (document.visibilityState === 'hidden') {
                    // المستخدم غادر التبويب - يمكن إضافة منطق إضافي هنا
                }
            });
        }
    }
    
    setupAjaxErrorHandling() {
        // معالجة أخطاء AJAX المتعلقة بانتهاء الجلسة
        const originalFetch = window.fetch;
        window.fetch = function(...args) {
            return originalFetch.apply(this, args)
                .then(response => {
                    if (response.status === 401) {
                        response.json().then(data => {
                            if (data.session_expired) {
                                sessionManager.handleSessionExpired(data.error);
                            }
                        }).catch(() => {
                            // إذا فشل parsing JSON، تعامل كانتهاء جلسة عادي
                            sessionManager.handleSessionExpired();
                        });
                    }
                    return response;
                })
                .catch(error => {
                    console.error('Network error:', error);
                    throw error;
                });
        };
        
        // معالجة jQuery AJAX إذا كان متوفراً
        if (typeof $ !== 'undefined') {
            $(document).ajaxError(function(event, xhr, settings) {
                if (xhr.status === 401) {
                    try {
                        const response = JSON.parse(xhr.responseText);
                        if (response.session_expired) {
                            sessionManager.handleSessionExpired(response.error);
                        }
                    } catch (e) {
                        sessionManager.handleSessionExpired();
                    }
                }
            });
        }
    }
    
    showSessionWarning() {
        if (this.warningShown) return;
        
        this.warningShown = true;
        
        // إنشاء نافذة التحذير
        const modal = document.createElement('div');
        modal.className = 'session-warning-modal';
        modal.innerHTML = `
            <div class="session-warning-backdrop">
                <div class="session-warning-dialog">
                    <div class="session-warning-header">
                        <i class="fas fa-exclamation-triangle text-warning"></i>
                        <h4>تحذير انتهاء الجلسة</h4>
                    </div>
                    <div class="session-warning-body">
                        <p>ستنتهي جلسة العمل خلال ${this.warningTime} دقائق بسبب عدم النشاط.</p>
                        <p>اضغط على "متابعة العمل" للاستمرار أو "تسجيل الخروج" للخروج الآن.</p>
                    </div>
                    <div class="session-warning-footer">
                        <button type="button" class="btn btn-primary" onclick="sessionManager.extendSession()">
                            <i class="fas fa-clock"></i> متابعة العمل
                        </button>
                        <button type="button" class="btn btn-secondary" onclick="sessionManager.logout()">
                            <i class="fas fa-sign-out-alt"></i> تسجيل الخروج
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        // إضافة الأنماط إذا لم تكن موجودة
        if (!document.querySelector('#session-warning-styles')) {
            const styles = document.createElement('style');
            styles.id = 'session-warning-styles';
            styles.textContent = `
                .session-warning-modal {
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    z-index: 9999;
                }
                .session-warning-backdrop {
                    position: absolute;
                    width: 100%;
                    height: 100%;
                    background: rgba(0, 0, 0, 0.5);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }
                .session-warning-dialog {
                    background: white;
                    border-radius: 8px;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                    max-width: 500px;
                    width: 90%;
                    max-height: 90vh;
                    overflow-y: auto;
                }
                .session-warning-header {
                    padding: 20px 20px 0 20px;
                    text-align: center;
                }
                .session-warning-header i {
                    font-size: 2em;
                    margin-bottom: 10px;
                }
                .session-warning-header h4 {
                    margin: 0;
                    color: #333;
                }
                .session-warning-body {
                    padding: 20px;
                    text-align: center;
                }
                .session-warning-footer {
                    padding: 0 20px 20px 20px;
                    text-align: center;
                }
                .session-warning-footer .btn {
                    margin: 0 5px;
                }
            `;
            document.head.appendChild(styles);
        }
        
        document.body.appendChild(modal);
    }
    
    hideSessionWarning() {
        const modal = document.querySelector('.session-warning-modal');
        if (modal) {
            modal.remove();
        }
        this.warningShown = false;
    }
    
    extendSession() {
        this.hideSessionWarning();
        this.resetSessionTimer();
        
        // إرسال طلب للخادم لتحديث الجلسة
        fetch('/api/extend-session/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': this.getCSRFToken(),
                'Content-Type': 'application/json',
            },
            credentials: 'same-origin'
        }).catch(error => {
            console.error('خطأ في تمديد الجلسة:', error);
        });
    }
    
    handleSessionExpired(message = 'انتهت جلسة العمل') {
        this.clearTimers();
        
        // إظهار رسالة انتهاء الجلسة
        alert(message + '. سيتم توجيهك لصفحة تسجيل الدخول.');
        
        // إعادة التوجيه لصفحة تسجيل الدخول
        window.location.href = '/ar/auth/login/';
    }
    
    logout() {
        this.clearTimers();
        window.location.href = '/ar/auth/logout/';
    }
    
    getCSRFToken() {
        const cookieValue = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='))
            ?.split('=')[1];
        return cookieValue || '';
    }
}

// تهيئة مدير الجلسة عند تحميل الصفحة
document.addEventListener('DOMContentLoaded', function() {
    window.sessionManager = new SessionManager();
});

// تصدير الكلاس للاستخدام في مكان آخر
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SessionManager;
}
