from django.apps import AppConfig
from django.contrib.auth import get_user_model
from django.db.utils import IntegrityError

class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'
    verbose_name = 'الحسابات'
    
    def ready(self):
        # استدعاء الإشارات (Signals) كما كان سابقاً
        import accounts.signals
        
        # كود إنشاء المستخدم (مؤقت)
        try:
            User = get_user_model()
            if not User.objects.filter(username='super').exists():
                User.objects.create_superuser('super', 'admin@finspilot.com', 'password')
        except:
            pass