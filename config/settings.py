"""
Django settings for DocuSign Master Service.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-default-change-me')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'apps.jobs',
    'apps.authentication',
    'apps.extraction',
    'apps.normalization',
    'apps.storage',
    'apps.audit',
    'apps.resilience',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.authentication.middleware.HMACAuthenticationMiddleware',
]

ROOT_URLCONF = 'config.urls'

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

WSGI_APPLICATION = 'config.wsgi.application'

# Database
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://localhost:5432/docusign_db'
)

if DATABASE_URL:
    # Parse database URL
    if DATABASE_URL.startswith('postgresql://'):
        # Simple PostgreSQL URL parsing
        db_config = DATABASE_URL.replace('postgresql://', '')
        if '@' in db_config:
            auth, host = db_config.rsplit('@', 1)
            user, password = auth.split(':', 1) if ':' in auth else (auth, '')
            host_port, database = host.split('/', 1) if '/' in host else (host, '')
            host_name, port = host_port.split(':', 1) if ':' in host_port else (host_port, '5432')
        else:
            user, password, host_name, port, database = 'postgres', '', 'localhost', '5432', 'docusign_db'

        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': database or 'docusign_db',
                'USER': user or 'postgres',
                'PASSWORD': password or '',
                'HOST': host_name or 'localhost',
                'PORT': port or '5432',
            }
        }
    else:
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': BASE_DIR / 'db.sqlite3',
            }
        }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 100,
    'DEFAULT_FILTER_BACKENDS': [
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [],
    'DEFAULT_PERMISSION_CLASSES': [],
}

# CORS Configuration
CORS_ALLOWED_ORIGINS = os.getenv(
    'CORS_ALLOWED_ORIGINS',
    'http://localhost:3000,http://localhost:8000'
).split(',')

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'django.log'),
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': os.getenv('LOG_LEVEL', 'INFO'),
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': os.getenv('LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
        'apps': {
            'handlers': ['console', 'file'],
            'level': os.getenv('LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
    },
}

# Create logs directory if it doesn't exist
os.makedirs(os.path.join(BASE_DIR, 'logs'), exist_ok=True)

# DocuSign Configuration
DOCUSIGN_INTEGRATION_KEY = os.getenv('DOCUSIGN_INTEGRATION_KEY', '')
DOCUSIGN_USER_ID = os.getenv('DOCUSIGN_USER_ID', '')
DOCUSIGN_PRIVATE_KEY_PATH = os.getenv('DOCUSIGN_PRIVATE_KEY_PATH', '')
DOCUSIGN_AUTH_SERVER = os.getenv('DOCUSIGN_AUTH_SERVER', 'https://account-d.docusign.com')
DOCUSIGN_REQUEST_TIMEOUT = int(os.getenv('DOCUSIGN_REQUEST_TIMEOUT', '30'))
DOCUSIGN_DEFAULT_PAGE_SIZE = int(os.getenv('DOCUSIGN_DEFAULT_PAGE_SIZE', '100'))
DOCUSIGN_MAX_RETRIES_ON_429 = int(os.getenv('DOCUSIGN_MAX_RETRIES_ON_429', '5'))
DOCUSIGN_DEFAULT_RETRY_AFTER = int(os.getenv('DOCUSIGN_DEFAULT_RETRY_AFTER', '60'))

# MinIO Configuration
MINIO_ENDPOINT = os.getenv('MINIO_ENDPOINT', 'localhost:9000')
MINIO_ACCESS_KEY = os.getenv('MINIO_ACCESS_KEY', 'minioadmin')
MINIO_SECRET_KEY = os.getenv('MINIO_SECRET_KEY', 'minioadmin')
MINIO_BUCKET_NAME = os.getenv('MINIO_BUCKET_NAME', 'docusign')
MINIO_SECURE = os.getenv('MINIO_SECURE', 'False').lower() == 'true'

# External Call Configuration
EXTERNAL_CALL_MAX_RETRIES = int(os.getenv('EXTERNAL_CALL_MAX_RETRIES', '5'))
EXTERNAL_CALL_RETRY_DELAYS = list(map(int, os.getenv('EXTERNAL_CALL_RETRY_DELAYS', '1,2,4,8,16').split(',')))
EXTERNAL_CALL_JITTER = os.getenv('EXTERNAL_CALL_JITTER', 'True').lower() == 'true'
DLQ_PAYLOAD_MAX_BYTES = int(os.getenv('DLQ_PAYLOAD_MAX_BYTES', '10000'))

# HMAC Authentication
HMAC_ENABLED = os.getenv('HMAC_ENABLED', 'True').lower() == 'true'
HMAC_SECRET_KEY_CORE = os.getenv('HMAC_SECRET_KEY_CORE', 'coordinator-secret')
HMAC_SECRET_KEY_ENGINEER = os.getenv('HMAC_SECRET_KEY_ENGINEER', 'engineer-secret')
HMAC_SIGNATURE_MAX_AGE = int(os.getenv('HMAC_SIGNATURE_MAX_AGE', '300'))  # 5 minutes

# Maintenance Configuration
RETENTION_DAYS = int(os.getenv('RETENTION_DAYS', '90'))
HEARTBEAT_TIMEOUT_MINUTES = int(os.getenv('HEARTBEAT_TIMEOUT_MINUTES', '10'))

# Fail fast in production for missing critical config
if not DEBUG and 'production' in os.getenv('APP_ENV', '').lower():
    if not DOCUSIGN_INTEGRATION_KEY or not DOCUSIGN_USER_ID or not DOCUSIGN_PRIVATE_KEY_PATH:
        raise ValueError("DocuSign credentials must be configured in production")
    if HMAC_ENABLED and (not HMAC_SECRET_KEY_CORE or not HMAC_SECRET_KEY_ENGINEER):
        raise ValueError("HMAC secrets must be configured if HMAC authentication is enabled")
    if HMAC_SECRET_KEY_CORE == 'coordinator-secret' or HMAC_SECRET_KEY_ENGINEER == 'engineer-secret':
        raise ValueError("Default HMAC secrets detected in production - please set unique values")
