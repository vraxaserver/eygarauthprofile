from pathlib import Path
import os
from dotenv import load_dotenv
load_dotenv()


ENV = os.getenv('ENV', default='dev')
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('SECRET_KEY', default='67f79f54a85671dce02e3d8c3fc5e0b2')

STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY', default='your-secret-key-here')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', default=True)


ALLOWED_HOSTS = ['*']

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'whitenoise.runserver_nostatic',
    'django.contrib.staticfiles',

    # === 3rd party apps ===
    'rest_framework',
    'drf_spectacular',
    'corsheaders',
    'rest_framework_simplejwt.token_blacklist',
    'storages',

    # === Local apps ===
    'accounts',
    'eygarprofile',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'conf.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'conf.wsgi.application'

# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME", "mydb"),
        "USER": os.getenv("DB_USER", "myuser"),
        "PASSWORD": os.getenv("DB_PASSWORD", "mypassword"),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
    }
}

AUTH_USER_MODEL = "accounts.User"

# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

STATIC_URL = 'static/'

STATIC_ROOT = os.getenv('STATIC_ROOT', default=BASE_DIR / 'staticfiles') 

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

MEDIA_URL = "/media/"

MEDIA_ROOT = os.getenv('MEDIA_ROOT', default=BASE_DIR / 'media')


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# DRF + Simple JWT
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.AllowAny',
    ),
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.MultiPartParser',
        'rest_framework.parsers.FormParser',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': True,
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# CORS Configuration
CORS_ALLOWED_ORIGINS = [
    "https://eygar.org",
    "https://admin.eygar.org",
    "http://localhost:3000",  # Next.js default
    "http://127.0.0.1:3000",
]

CORS_ALLOW_CREDENTIALS = True

# File Upload Settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024  # 5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB

# Email: dev uses console backend. For production configure SMTP settings.


EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = os.getenv('EMAIL_PORT', default=587)
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', default=True)
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', default='vraxa.server@gmail.com')


# AWS Configuration
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_REGION_NAME = os.getenv('AWS_REGION_NAME', 'me-central-1')
AWS_SQS_QUEUE_URL = os.getenv('AWS_SQS_QUEUE_URL', 'https://sqs.ap-south-1.amazonaws.com/637423303507/eygar-queues')
AWS_S3_BUCKET_NAME = os.getenv("AWS_S3_BUCKET_NAME")
AWS_S3_REGION_NAME = AWS_REGION_NAME
AWS_S3_FILE_OVERWRITE = True
AWS_S3_CUSTOM_DOMAIN = f"{AWS_S3_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com"
AWS_SQS_EMAIL_QUEUE_URL = os.getenv("AWS_SQS_EMAIL_QUEUE_URL")

MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/'


TWILIO_AUTH_TOKEN=os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_ACCOUNT_SID=os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_PHONE_NUMBER=os.getenv('TWILIO_PHONE_NUMBER')


# DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"

STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3.S3Storage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Document Verification Settings
DOCUMENT_VERIFICATION_ENABLED = os.getenv('DOCUMENT_VERIFICATION_ENABLED', default=True)
DOCUMENT_VERIFICATION_API_KEY = os.getenv('DOCUMENT_VERIFICATION_API_KEY', default='')
DOCUMENT_VERIFICATION_API_URL = os.getenv('DOCUMENT_VERIFICATION_API_URL', default='')

# Frontend URL
FRONTEND_URL = os.getenv('SITE_URL', default='http://localhost:3000')
SITE_URL = FRONTEND_URL
ADMIN_URL = '/admin/'

# Verification Settings
VERIFICATION_CODE_LENGTH = 6
VERIFICATION_CODE_EXPIRY_MINUTES = 10

# Social Auth
SOCIAL_AUTH_GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '')
SOCIAL_AUTH_GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET', '')
SOCIAL_AUTH_FACEBOOK_APP_ID = os.getenv('FACEBOOK_APP_ID', '')
SOCIAL_AUTH_FACEBOOK_APP_SECRET = os.getenv('FACEBOOK_APP_SECRET', '')

# Stripe (optional, can be disabled)
STRIPE_ENABLED = os.getenv('STRIPE_ENABLED', 'true').lower() == 'true'

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'host_profile.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'host_profile': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}

# API Documentation (Swagger)
SPECTACULAR_SETTINGS = {
    'TITLE': 'Host Profile API',
    'DESCRIPTION': 'API for managing host profiles and verification',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
}

# Security Settings
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin-allow-popups"
SECURE_REFERRER_POLICY = "same-origin"

# Custom Settings
HOST_PROFILE_SETTINGS = {
    'BUSINESS_LICENSE_MAX_SIZE': 5 * 1024 * 1024,  # 5MB
    'BUSINESS_LOGO_MAX_SIZE': 2 * 1024 * 1024,     # 2MB
    'IDENTITY_DOCUMENT_MAX_SIZE': 5 * 1024 * 1024,  # 5MB
    'MOBILE_VERIFICATION_CODE_EXPIRY': 600,  # 10 minutes
    'EMAIL_VERIFICATION_TOKEN_EXPIRY': 86400,  # 24 hours
    'ALLOWED_DOCUMENT_FORMATS': ['pdf', 'jpg', 'jpeg', 'png'],
    'ALLOWED_IMAGE_FORMATS': ['jpg', 'jpeg', 'png', 'gif'],
    'AUTO_APPROVE_VERIFIED_PROFILES': False,
    'REQUIRE_MANUAL_REVIEW': True,
}
