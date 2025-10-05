import os
import sys
from pathlib import Path
from decouple import config, Csv
import dj_database_url

# Set UTF-8 encoding
sys.stdout.reconfigure(encoding='utf-8')
os.environ.setdefault('PYTHONIOENCODING', 'utf-8')

BASE_DIR = Path(__file__).resolve().parent.parent

# تحميل ملف .env تلقائياً
from dotenv import load_dotenv
load_dotenv(os.path.join(BASE_DIR, '.env'))

SECRET_KEY = config('SECRET_KEY', default='django-insecure-default-key-change-in-production')

# تعريف متغيرات البيئة المبكرة
IS_RENDER = config('RENDER', default=False, cast=bool)
DEBUG = config('DEBUG', default=False, cast=bool)

# Detect when running tests so we can relax some production-only settings
TESTING = len(sys.argv) > 1 and sys.argv[1] == 'test'

# السماح بالمضيفين مع قيمة افتراضية آمنة محلياً
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='127.0.0.1,localhost,192.168.2.117').split(',')

# إضافة نطاق Render تلقائياً إذا كان متاحاً في البيئة
if IS_RENDER:
    # في بيئة Render، أضف النطاق الحالي
    current_host = config('RENDER_EXTERNAL_URL', default='').replace('https://', '').replace('http://', '')
    if current_host and current_host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(current_host)

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'rest_framework',
    'corsheaders',
    'django_bootstrap5',
    'crispy_forms',
    'crispy_bootstrap5',
    
    # Custom apps
    'core',
    'accounts',
    'products',
    'customers',
    'purchases',
    'sales',
    'inventory',
    'search',
    'banks',
    'cashboxes',
    'journal',
    'reports',
    'documents',
    'users',
    'settings',
    'receipts',
    'payments',
    'revenues_expenses',
    'assets_liabilities',
    'backup',
    'hr',
    'provisions',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'core.middleware.AuditMiddleware',
    'core.middleware.POSUserMiddleware',
    'core.middleware.SessionTimeoutMiddleware',
    'core.middleware.SessionSecurityMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'finspilot.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.template.context_processors.i18n',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.currency_context',
                'core.context_processors.company_context',
                'core.context_processors.notifications_context',
                'core.context_processors.language_context',
                'core.context_processors.active_menu_context',
                # expose superadmin settings globally
                'settings.context_processors.superadmin_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'finspilot.wsgi.application'

# ===== قاعدة البيانات =====
# تهيئة مرنة: تفضيل DATABASE_URL إن وُجد (Render), ثم متغيرات PG_*, ثم PostgreSQL محلي, ثم SQLite
DATABASES = {}

DATABASE_URL = config('DATABASE_URL', default=None)
USE_LOCAL_POSTGRES = config('USE_LOCAL_POSTGRES', default=False, cast=bool)

if DATABASE_URL:
    # Render يوفر connection string مباشرة
    # امنع فرض SSL عندما يشير DATABASE_URL إلى مضيف محلي (مثلاً خلال المحاكاة المحلية)
    # لكن حافظ على فرض SSL في بيئة Render الحقيقية (IS_RENDER=True و DEBUG=False)
    from urllib.parse import urlparse

    parsed_db_url = urlparse(DATABASE_URL)
    db_host = (parsed_db_url.hostname or '').lower()
    # اعتبر هذه المضيفات محلية ولا نطلب SSL عند الاتصال بها
    local_hosts = ('localhost', '127.0.0.1', '::1', '0.0.0.0')
    is_local_db = db_host in local_hosts

    ssl_required = bool(IS_RENDER and not DEBUG and not is_local_db)

    DATABASES['default'] = dj_database_url.parse(
        DATABASE_URL,
        conn_max_age=600,
        ssl_require=ssl_required
    )
elif USE_LOCAL_POSTGRES:
    # استخدام PostgreSQL محلي للتطوير
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('LOCAL_PG_NAME', default='finspilot_local'),
        'USER': config('LOCAL_PG_USER', default='postgres'),
        'PASSWORD': config('LOCAL_PG_PASSWORD', default=''),
        'HOST': config('LOCAL_PG_HOST', default='localhost'),
        'PORT': config('LOCAL_PG_PORT', default='5432'),
    }
else:
    pg_name = config('PG_NAME', default=config('DB_NAME', default=None))
    pg_user = config('PG_USER', default=config('DB_USER', default=None))
    pg_password = config('PG_PASSWORD', default=config('DB_PASSWORD', default=None))
    pg_host = config('PG_HOST', default=config('DB_HOST', default=None))
    pg_port = config('PG_PORT', default=config('DB_PORT', default=None))

    if all([pg_name, pg_user, pg_password, pg_host, pg_port]):
        db_conf = {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': pg_name,
            'USER': pg_user,
            'PASSWORD': pg_password,
            'HOST': pg_host,
            'PORT': pg_port,
        }
        # SSL: عند استخدام متغيرات PG_* نعتمد 'prefer' لضمان عمل البيئة المحلية بدون SSL
        db_conf['OPTIONS'] = {'sslmode': 'prefer'}
        DATABASES['default'] = db_conf
    else:
        # كحل أخير (للتطوير فقط)، يمكن استخدام SQLite إذا لم تُعرّف البيئة
        # هذا لا يؤثر على الإنتاج لأنه يعتمد على متغيرات البيئة
        DATABASES['default'] = {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
# المتغيرات المطلوبة في ملف .env:
# للإنتاج على Render:
# PG_NAME=اسم_قاعدة_البيانات
# PG_USER=اسم_المستخدم
# PG_PASSWORD=كلمة_المرور
# PG_HOST=العنوان
# PG_PORT=المنفذ
#
# للتطوير المحلي مع PostgreSQL:
# USE_LOCAL_POSTGRES=True
# LOCAL_PG_NAME=finspilot_local
# LOCAL_PG_USER=postgres
# LOCAL_PG_PASSWORD=كلمة_مرور_PostgreSQL
# LOCAL_PG_HOST=localhost
# LOCAL_PG_PORT=5432

# ===== كلمات المرور =====
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# ===== اللغة والتوقيت =====
# اللغات المدعومة
LANGUAGES = [
    ('en', 'English'),
    ('ar', 'العربية'),
]

# ===== الملفات الثابتة =====
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# تحسين تقديم الملفات الثابتة في الإنتاج فقط
if not DEBUG and not TESTING:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ===== البريد =====
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default=None)
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default=None)

# اجعل Backend للبريد يعمل عبر SMTP فقط عند توفر الاعتمادات، وإلا استخدم console لتجنب فشل التشغيل
if EMAIL_HOST_USER and EMAIL_HOST_PASSWORD:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# ===== العملة الافتراضية =====
DEFAULT_CURRENCY = config('DEFAULT_CURRENCY', default='JOD')

# ===== إعدادات إضافية =====
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20
}

# CORS settings
# السماح بالأصول من العناوين المحلية بشكل افتراضي، مع إضافة نطاق Render تلقائياً إن وُجد
_DEFAULT_CORS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]
CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default=','.join(_DEFAULT_CORS)
).split(',')

# إضافة أصول نطاق Render (https) إن تم تحديدها ضمن ALLOWED_HOSTS
for host in ALLOWED_HOSTS:
    host = host.strip()
    if host and host.endswith('onrender.com'):
        origin = f"https://{host}"
        if origin not in CORS_ALLOWED_ORIGINS:
            CORS_ALLOWED_ORIGINS.append(origin)

# CSRF
CSRF_TRUSTED_ORIGINS = [f"https://{h.strip()}" for h in ALLOWED_HOSTS if h.strip()]

# Crispy Forms
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# Internationalization
LANGUAGE_CODE = 'ar'
TIME_ZONE = 'Asia/Amman'
USE_I18N = True
USE_L10N = True
USE_TZ = True

LANGUAGES = [
    ('ar', 'العربية'),
    ('en', 'English'),
]

LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

# Session settings
SESSION_COOKIE_AGE = 3600  # 1 hour
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# Custom User Model
AUTH_USER_MODEL = 'users.User'

# Login URLs
LOGIN_URL = '/ar/auth/login/'
LOGIN_REDIRECT_URL = '/ar/'
LOGOUT_REDIRECT_URL = '/ar/auth/login/'


# ===== إعدادات أمنية للإنتاج فقط =====
# تُفعّل فقط عندما DEBUG=False لضمان أن بيئة التطوير المحلية لا تتأثر
if not DEBUG and not TESTING:
    # إعادة التوجيه إلى HTTPS
    SECURE_SSL_REDIRECT = True

    # اجعل الكوكيز آمنة (تنقل فقط مع HTTPS)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    # HSTS: ابدأ بقيمة صغيرة ثم زدها تدريجياً عند التأكد
    SECURE_HSTS_SECONDS = int(config('SECURE_HSTS_SECONDS', default=3600))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = config('SECURE_HSTS_INCLUDE_SUBDOMAINS', default=True, cast=bool)
    SECURE_HSTS_PRELOAD = config('SECURE_HSTS_PRELOAD', default=False, cast=bool)

    # إذا كان التطبيق خلف Proxy أو Load Balancer الذي يحدد X-Forwarded-Proto
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
