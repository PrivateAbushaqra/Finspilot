import os
from pathlib import Path
from decouple import config
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY')

DEBUG = config('DEBUG', default=False, cast=bool)

# السماح بالمضيفين مع قيمة افتراضية آمنة محلياً
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='127.0.0.1,localhost').split(',')

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
    'users',
    'settings',
    'receipts',
    'payments',
    'revenues_expenses',
    'assets_liabilities',
    'backup',
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
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.currency_context',
                'core.context_processors.company_context',
                'core.context_processors.notifications_context',
                'core.context_processors.language_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'finspilot.wsgi.application'

# ===== قاعدة البيانات =====
# تهيئة مرنة: تفضيل DATABASE_URL إن وُجد (Render), ثم متغيرات PG_*, ثم DB_*
DATABASES = {}

DATABASE_URL = config('DATABASE_URL', default=None)
IS_RENDER = config('RENDER', default=False, cast=bool)

if DATABASE_URL:
    # Render يوفر connection string مباشرة
    DATABASES['default'] = dj_database_url.parse(
        DATABASE_URL,
        conn_max_age=600,
        ssl_require=(IS_RENDER and not DEBUG)
    )
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
# PG_NAME=اسم_قاعدة_البيانات
# PG_USER=اسم_المستخدم
# PG_PASSWORD=كلمة_المرور
# PG_HOST=العنوان
# PG_PORT=المنفذ

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
if not DEBUG:
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
