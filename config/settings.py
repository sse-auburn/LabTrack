"""
Django settings for SSELabTrack project.

Lab Inventory Management System for the SSE Lab.
"""

from pathlib import Path
from decouple import config
from django.contrib.messages import constants as messages

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------
SECRET_KEY = config(
    'SECRET_KEY',
    default='django-insecure-sselabtrack-default-secret-key-change-in-production'
)

DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = config(
    'ALLOWED_HOSTS',
    default='localhost,127.0.0.1',
    cast=lambda v: [s.strip() for s in v.split(',')]
)

CSRF_TRUSTED_ORIGINS = config(
    'CSRF_TRUSTED_ORIGINS',
    default='http://localhost:8000,http://127.0.0.1:8000',
    cast=lambda v: [s.strip() for s in v.split(',')]
)


# ---------------------------------------------------------------------------
# Application definition
# ---------------------------------------------------------------------------
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
]

THIRD_PARTY_APPS = [
    'crispy_forms',
    'crispy_tailwind',
    'django_filters',
    'django_ckeditor_5',
]

LOCAL_APPS = [
    'apps.accounts',
    'apps.equipment',
    'apps.reservations',
    'apps.kits',
    'apps.incidents',
    'apps.notifications',
    'apps.activity',
    'apps.files',
    'apps.dashboard',
    'apps.pcard',
    'apps.public',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


# ---------------------------------------------------------------------------
# URL configuration
# ---------------------------------------------------------------------------
ROOT_URLCONF = 'config.urls'


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------
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
                'apps.notifications.context_processors.unread_notifications',
                'apps.activity.context_processors.recent_activities',
            ],
        },
    },
]


# ---------------------------------------------------------------------------
# WSGI
# ---------------------------------------------------------------------------
WSGI_APPLICATION = 'config.wsgi.application'


# ---------------------------------------------------------------------------
# Database
# MySQL is used when DB_HOST is set (e.g. in Docker / production).
# Falls back to SQLite for local development without any extra setup.
# ---------------------------------------------------------------------------
_DB_HOST = config('DB_HOST', default='')

if _DB_HOST:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': config('DB_NAME', default='labtrack'),
            'USER': config('DB_USER', default='labtrack'),
            'PASSWORD': config('DB_PASSWORD', default=''),
            'HOST': _DB_HOST,
            'PORT': config('DB_PORT', default='3306'),
            'OPTIONS': {
                'charset': 'utf8mb4',
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
                # Auburn MySQL 8.0 requires SSL. check_hostname=False allows
                # connecting without a CA certificate (self-signed / internal PKI).
                'ssl': {'check_hostname': False},
            },
        }
    }
else:
    _SQLITE_DIR = Path(config('SQLITE_DIR', default=str(BASE_DIR)))
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': _SQLITE_DIR / 'db.sqlite3',
            'OPTIONS': {
                'timeout': 20,
                'init_command': 'PRAGMA journal_mode=WAL;',
            },
        }
    }


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = 'accounts.CustomUser'

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

LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/accounts/login/'


# ---------------------------------------------------------------------------
# Internationalisation
# ---------------------------------------------------------------------------
LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# ---------------------------------------------------------------------------
# Static files (CSS, JavaScript, Images)
# ---------------------------------------------------------------------------
STATIC_URL = '/static/'

_STATIC_SRC = BASE_DIR / 'static'
STATICFILES_DIRS = [_STATIC_SRC] if _STATIC_SRC.exists() else []

STATIC_ROOT = BASE_DIR / 'staticfiles'

STORAGES = {
    'default': {
        'BACKEND': 'apps.files.storage.DatabaseStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}


# ---------------------------------------------------------------------------
# Media files (user uploads)
# ---------------------------------------------------------------------------
MEDIA_URL = '/media/'

MEDIA_ROOT = BASE_DIR / 'media'




# ---------------------------------------------------------------------------
# CKEditor 5
# ---------------------------------------------------------------------------
customColorPalette = [
    {"color": "hsl(4, 90%, 58%)", "label": "Red"},
    {"color": "hsl(340, 82%, 52%)", "label": "Pink"},
    {"color": "hsl(291, 64%, 42%)", "label": "Purple"},
    {"color": "hsl(262, 52%, 47%)", "label": "Deep Purple"},
    {"color": "hsl(231, 48%, 48%)", "label": "Indigo"},
    {"color": "hsl(207, 90%, 54%)", "label": "Blue"},
    {"color": "hsl(199, 98%, 48%)", "label": "Light Blue"},
    {"color": "hsl(174, 63%, 40%)", "label": "Teal"},
    {"color": "hsl(145, 63%, 42%)", "label": "Green"},
    {"color": "hsl(88, 50%, 53%)", "label": "Light Green"},
    {"color": "hsl(54, 100%, 62%)", "label": "Lime"},
    {"color": "hsl(45, 100%, 51%)", "label": "Yellow"},
    {"color": "hsl(36, 100%, 50%)", "label": "Orange"},
    {"color": "hsl(0, 0%, 0%)", "label": "Black"},
    {"color": "hsl(0, 0%, 100%)", "label": "White"},
]

CKEDITOR_5_CONFIGS = {
    "default": {
        "toolbar": [
            "heading",
            "|",
            "bold",
            "italic",
            "link",
            "bulletedList",
            "numberedList",
            "|",
            "blockQuote",
            "imageUpload",
            "insertImage",
            "|",
            "undo",
            "redo",
        ],
        "image": {
            "toolbar": [
                "imageTextAlternative",
                "|",
                "imageStyle:alignLeft",
                "imageStyle:alignRight",
                "imageStyle:alignCenter",
                "imageStyle:side",
                "|",
                "toggleImageCaption",
                "imageTextAlternative",
            ],
            "styles": [
                "full",
                "side",
                "alignLeft",
                "alignRight",
                "alignCenter",
            ],
        },
    },
    "extends": {
        "blockToolbar": [
            "paragraph",
            "heading1",
            "heading2",
            "heading3",
            "|",
            "bulletedList",
            "numberedList",
            "|",
            "blockQuote",
        ],
        "toolbar": [
            "heading",
            "|",
            "outdent",
            "indent",
            "|",
            "bold",
            "italic",
            "link",
            "underline",
            "strikethrough",
            "code",
            "subscript",
            "superscript",
            "highlight",
            "|",
            "codeBlock",
            "sourceEditing",
            "insertImage",
            "bulletedList",
            "numberedList",
            "todoList",
            "|",
            "blockQuote",
            "imageUpload",
            "|",
            "fontSize",
            "fontFamily",
            "fontColor",
            "fontBackgroundColor",
            "mediaEmbed",
            "removeFormat",
            "insertTable",
            "|",
            "undo",
            "redo",
        ],
        "image": {
            "toolbar": [
                "imageTextAlternative",
                "|",
                "imageStyle:alignLeft",
                "imageStyle:alignRight",
                "imageStyle:alignCenter",
                "imageStyle:side",
                "|",
            ],
            "styles": [
                "full",
                "side",
                "alignLeft",
                "alignRight",
                "alignCenter",
            ],
        },
        "table": {
            "contentToolbar": [
                "tableColumn",
                "tableRow",
                "mergeTableCells",
                "tableProperties",
                "tableCellProperties",
            ],
            "tableProperties": {"borderColors": customColorPalette, "backgroundColors": customColorPalette},
            "tableCellProperties": {"borderColors": customColorPalette, "backgroundColors": customColorPalette},
        },
        "heading": {
            "options": [
                {"model": "paragraph", "title": "Paragraph", "class": "ck-heading_paragraph"},
                {"model": "heading1", "view": "h1", "title": "Heading 1", "class": "ck-heading_heading1"},
                {"model": "heading2", "view": "h2", "title": "Heading 2", "class": "ck-heading_heading2"},
                {"model": "heading3", "view": "h3", "title": "Heading 3", "class": "ck-heading_heading3"},
            ]
        },
    },
}

CKEDITOR_5_UPLOAD_PATH = "uploads/"
CKEDITOR_5_ALLOW_ALL_FILE_TYPES = True
CKEDITOR_5_IMAGE_FILE_TYPES = ["jpg", "jpeg", "png", "gif", "webp"]
CKEDITOR_5_FILE_UPLOAD_PERMISSION = "authenticated"


# ---------------------------------------------------------------------------
# Default primary key field type
# ---------------------------------------------------------------------------
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ---------------------------------------------------------------------------
# Crispy Forms
# ---------------------------------------------------------------------------
CRISPY_ALLOWED_TEMPLATE_PACKS = 'tailwind'
CRISPY_TEMPLATE_PACK = 'tailwind'


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_USE_SSL = config('EMAIL_USE_SSL', default=False, cast=bool)
DEFAULT_FROM_EMAIL = config(
    'DEFAULT_FROM_EMAIL',
    default=EMAIL_HOST_USER or 'noreply@labtrack.local',
)

# Base URL used in email notification links (no trailing slash).
SITE_URL = config('SITE_URL', default='http://localhost')

# Email backend selection:
#   - Explicit EMAIL_BACKEND env var overrides everything.
#   - "auto" (default) uses SMTP when credentials are present, console otherwise.
#   - For relays without auth (e.g. campus relay on port 25), set
#     EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend explicitly.
_email_backend = config('EMAIL_BACKEND', default='auto')
if _email_backend == 'auto':
    if EMAIL_HOST_USER and EMAIL_HOST_PASSWORD:
        EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    else:
        EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    EMAIL_BACKEND = _email_backend


# ---------------------------------------------------------------------------
# Redis / Celery (optional — configure when ready to enable background tasks)
# ---------------------------------------------------------------------------
REDIS_URL = config('REDIS_URL', default='redis://localhost:6379/0')

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE


# ---------------------------------------------------------------------------
# Django Messages framework
# ---------------------------------------------------------------------------
MESSAGE_TAGS = {
    messages.DEBUG: 'debug',
    messages.INFO: 'info',
    messages.SUCCESS: 'success',
    messages.WARNING: 'warning',
    messages.ERROR: 'error',
}


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
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
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': config('DJANGO_LOG_LEVEL', default='INFO'),
            'propagate': False,
        },
    },
}
