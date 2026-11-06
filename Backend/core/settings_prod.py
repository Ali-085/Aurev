"""
Django settings for core project.
"""

import os
from pathlib import Path
from decouple import config, Csv

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='', cast=Csv())

# Add localhost for development if DEBUG is True
if DEBUG:
    ALLOWED_HOSTS.extend(['localhost', '127.0.0.1', '.ngrok-free.dev'])

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_filters',
    'drf_spectacular',
    # Local apps
    'users.apps.UsersConfig',
    'servers',
    'payouts',
    'analytics',
    'subscriptions',
    'audit',
    'platform_admin',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# Database
# Always use PostgreSQL (Supabase) - Never SQLite3
import dj_database_url

DATABASES = {
    "default": dj_database_url.config(
        default=os.getenv("DATABASE_URL"),
        conn_max_age=600,
        ssl_require=not DEBUG,  # SSL required in production, optional in development
    )
}


# Custom User Model
AUTH_USER_MODEL = 'users.User'

# Password validation
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

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files
MEDIA_URL = config('MEDIA_URL', default='/media/')
MEDIA_ROOT = BASE_DIR / config('MEDIA_ROOT', default='media')

# ===================================
# CLOUDFLARE R2 STORAGE CONFIGURATION
# ===================================
USE_R2_STORAGE = config('USE_R2_STORAGE', default=False, cast=bool)
USE_R2_FOR_STATIC = config('USE_R2_FOR_STATIC', default=False, cast=bool)

if USE_R2_STORAGE:
    # Add django-storages to installed apps if not already there
    if 'storages' not in INSTALLED_APPS:
        INSTALLED_APPS.append('storages')
    
    # Cloudflare R2 credentials
    R2_ACCESS_KEY_ID = config('R2_ACCESS_KEY_ID')
    R2_SECRET_ACCESS_KEY = config('R2_SECRET_ACCESS_KEY')
    R2_BUCKET_NAME = config('R2_BUCKET_NAME')
    R2_ACCOUNT_ID = config('R2_ACCOUNT_ID')
    
    # R2 endpoint URL (format: https://<account_id>.r2.cloudflarestorage.com)
    R2_ENDPOINT_URL = f'https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com'
    
    # R2 region (auto for R2)
    R2_REGION_NAME = 'auto'
    
    # Signature version for S3-compatible storage
    R2_SIGNATURE_VERSION = 's3v4'
    
    # Custom domain (optional - for public access)
    R2_CUSTOM_DOMAIN = config('R2_CUSTOM_DOMAIN', default=None)
    
    # Signed URL expiration time (in seconds)
    R2_SIGNED_URL_EXPIRATION = config('R2_SIGNED_URL_EXPIRATION', default=3600, cast=int)  # 1 hour
    
    # Set default storage backend for media files
    DEFAULT_FILE_STORAGE = 'core.storage_backends.R2MediaStorage'
    
    # Override MEDIA_URL to use R2
    if R2_CUSTOM_DOMAIN:
        MEDIA_URL = f'https://{R2_CUSTOM_DOMAIN}/'
    else:
        MEDIA_URL = f'https://{R2_BUCKET_NAME}.{R2_ACCOUNT_ID}.r2.cloudflarestorage.com/'
    
    # Static files on R2 (optional)
    if USE_R2_FOR_STATIC:
        STATICFILES_STORAGE = 'core.storage_backends.R2StaticStorage'
        STATIC_URL = f'https://{R2_BUCKET_NAME}.{R2_ACCOUNT_ID}.r2.cloudflarestorage.com/static/'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CORS Settings
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='', cast=Csv())

# Add development origins if DEBUG is True
if DEBUG:
    CORS_ALLOWED_ORIGINS.extend([
        'http://localhost:3000',
        'http://localhost:5173',
        'http://127.0.0.1:3000',
        'http://127.0.0.1:5173',
    ])

# Allow all ngrok domains in development only
CORS_ALLOWED_ORIGIN_REGEXES = []
if DEBUG:
    CORS_ALLOWED_ORIGIN_REGEXES = [
        r"^https://.*\.ngrok-free\.dev$",
        r"^https://.*\.ngrok\.io$",
    ]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'ngrok-skip-browser-warning',
]

# Add ngrok header only in development

CORS_EXPOSE_HEADERS = ['Content-Type', 'X-CSRFToken']

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'core.authentication.CookieJWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',  # Require authentication by default
        'users.permissions.IsEmailVerified',  # Global email verification enforcement
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'core.pagination.StandardResultsPagination',
    'PAGE_SIZE': 20,  # Fallback if pagination class doesn't specify
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# JWT Settings
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_COOKIE': 'access_token',  # Cookie name for access token
    'AUTH_COOKIE_REFRESH': 'refresh_token',  # Cookie name for refresh token
    'AUTH_COOKIE_SECURE': not DEBUG,  # HTTPS only in production
    'AUTH_COOKIE_HTTP_ONLY': True,  # Prevent XSS
    'AUTH_COOKIE_SAMESITE': 'Lax',  # CSRF protection
}

# Rate Limiting
REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'] = [
    'rest_framework.throttling.AnonRateThrottle',
    'rest_framework.throttling.UserRateThrottle'
]
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
    'anon': '100/hour',
    'user': '1000/hour',
    'login': '5/hour',  # Strict limit for login attempts
    'register': '3/hour',  # Prevent spam registrations
    'refresh': '10/minute',  # Limit token refresh
}

# Spectacular Settings (API Documentation)
SPECTACULAR_SETTINGS = {
    'TITLE': 'Trading Communities Platform API',
    'DESCRIPTION': 'API for verified trading communities and payout tracking',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

# Stripe Settings
STRIPE_SECRET_KEY = config('STRIPE_SECRET_KEY', default='')
STRIPE_PUBLISHABLE_KEY = config('STRIPE_PUBLISHABLE_KEY', default='')
STRIPE_WEBHOOK_SECRET = config('STRIPE_WEBHOOK_SECRET', default='')
STRIPE_API_VERSION = '2024-11-20.acacia'  # Pin API version

# Frontend URL (for Stripe redirect URLs - never trust frontend)
FRONTEND_URL = config('FRONTEND_URL', default='http://localhost:3000')

# ===================================
# PRODUCTION SECURITY SETTINGS
# ===================================
if not DEBUG:
    # HTTPS/SSL Settings
    SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=True, cast=bool)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    
    # HSTS Settings (HTTP Strict Transport Security)
    SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', default=31536000, cast=int)  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    
    # Proxy/Load Balancer Settings
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    USE_X_FORWARDED_HOST = True
    USE_X_FORWARDED_PORT = True
    
    # Session Security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    CSRF_COOKIE_HTTPONLY = True
    CSRF_COOKIE_SAMESITE = 'Lax'
    
    # Static files handling (use WhiteNoise or CDN)
    MIDDLEWARE.insert(1, 'django.middleware.security.SecurityMiddleware')
    # Uncomment if using WhiteNoise for static files
    # MIDDLEWARE.insert(2, 'whitenoise.middleware.WhiteNoiseMiddleware')
    # STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ===================================
# LOGGING CONFIGURATION
# ===================================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'maxBytes': 1024 * 1024 * 15,  # 15MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file', 'mail_admins'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['file', 'mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['file', 'mail_admins'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# Create logs directory if it doesn't exist
import os
os.makedirs(BASE_DIR / 'logs', exist_ok=True)

# Email Configuration (for error notifications and user emails)
if not DEBUG:
    # SMTP is optional - only configure if credentials provided
    EMAIL_HOST_USER = config('EMAIL_HOST_USER', default=None)
    EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default=None)
    
    if EMAIL_HOST_USER and EMAIL_HOST_PASSWORD:
        # SMTP configured - enable email notifications
        EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
        EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
        EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
        EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
        DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default=EMAIL_HOST_USER)
        SERVER_EMAIL = config('SERVER_EMAIL', default=EMAIL_HOST_USER)
        ADMINS = [('Admin', EMAIL_HOST_USER)]
    else:
        # No SMTP configured - disable email notifications
        EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    # Development - Console backend
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Resend API Configuration (for email verification)
# Get your API key from: https://resend.com/api-keys
RESEND_API_KEY = config('RESEND_API_KEY', default=None)

# Frontend URL (for verification links)
FRONTEND_URL = config('FRONTEND_URL', default='http://localhost:5173' if DEBUG else None)

# From Email (for Resend)
FROM_EMAIL = config('FROM_EMAIL', default='Aurevia <abc@xyz.com>')
