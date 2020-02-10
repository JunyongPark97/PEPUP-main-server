"""
Django settings for pepup project.

Generated by 'django-admin startproject' using Django 3.0.1.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.0/ref/settings/
"""

import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
from pepup.loader import load_credential

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_DIR = os.path.dirname(PROJECT_DIR)

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.sites',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

# apps
SECONDS_APPS = [
    'accounts',
    'api',
    'notice',
]

# package
THIRD_APPS = [
    'rest_framework',
    'rest_framework.authtoken',

    # allauth
    'allauth',
    'allauth.account',
    'allauth.socialaccount',

    'allauth.socialaccount.providers.instagram',
    'allauth.socialaccount.providers.kakao',

    # 'drf_yasg',

    'storages',

    # 'channels',

    'corsheaders',
    
    # 'toolbar'
    'debug_toolbar',

    # 'ckeditor'
    'ckeditor',
    'ckeditor_uploader',
]

INSTALLED_APPS += SECONDS_APPS + THIRD_APPS

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]

ROOT_URLCONF = 'pepup.urls'

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

WSGI_APPLICATION = 'pepup.wsgi.application'

# Password validation
# https://docs.djangoproject.com/en/3.0/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/3.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Seoul'

USE_I18N = True

USE_L10N = True

USE_TZ = False

# Default user model
AUTH_USER_MODEL = 'accounts.User'

# allauth settings
AUTHENTICATION_BACKENDS = (
    # Needed to login by username in Django admin, regardless of `allauth`
    'django.contrib.auth.backends.ModelBackend',

    # `allauth` specific authentication methods, such as login by e-mail
    'allauth.account.auth_backends.AuthenticationBackend',
)

# park 임시 사용
# ########## STATIC & MEDIA SETTINGS
#
# AWS_REGION = 'ap-northeast-2'
# AWS_STORAGE_BUCKET_NAME = 'pepup-server-storages-dev'
# AWS_QUERYSTRING_AUTH = False
# AWS_S3_HOST = 's3.%s.amazonaws.com' % AWS_REGION
# AWS_ACCESS_KEY_ID = load_credential('_AWS_ACCESS_KEY_ID', "")
# AWS_SECRET_ACCESS_KEY = load_credential('_AWS_SECRET_ACCESS_KEY', "")
# AWS_S3_CUSTOM_DOMAIN = '%s.s3.amazonaws.com' % AWS_STORAGE_BUCKET_NAME
# AWS_S3_SECURE_URLS = True  # https
#
# # Static Setting
# STATICFILES_LOCATION = 'static'
# STATIC_URL = "https://%s/%s/" % (AWS_S3_CUSTOM_DOMAIN, STATICFILES_LOCATION)
# STATICFILES_STORAGE = 'pepup.storages.StaticStorage'
#
# # Media Setting
# MEDIAFIELS_LOCATION = 'media'
# MEDIA_URL = "https://%s/%s/" % (AWS_S3_CUSTOM_DOMAIN, MEDIAFIELS_LOCATION)
# MEDIAFILES_LOCATION = 'media'
# DEFAULT_FILE_STORAGE = 'pepup.storages.MediaStorage'
#
# # See: https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#staticfiles-finders
# STATICFILES_FINDERS = [
#     'django.contrib.staticfiles.finders.FileSystemFinder',
#     'django.contrib.staticfiles.finders.AppDirectoriesFinder',
# ]
#
# # See: http://django-compressor.readthedocs.io/en/latest/
# ########## END STATIC % MEDIA CONFIGURATION


SITE_ID = 1

# drf 토큰인증처
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework_jwt.authentication.JSONWebTokenAuthentication',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 51
}

ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_AUTHENTICATION_METHOD = 'email'

########## CKEDITOR CONFIGURATION
CKEDITOR_UPLOAD_PATH = "uploads/"

CKEDITOR_IMAGE_BACKEND = "pillow"
CKEDITOR_JQUERY_URL = 'https://ajax.googleapis.com/ajax/libs/jquery/2.2.4/jquery.min.js'


CKEDITOR_CONFIGS = {
    'default': {
        'toolbar': 'Custom',
        'toolbar_Custom': [
            ['Bold', 'Italic', 'Underline', 'Source', '-', 'Image'],
            ['NumberedList', 'BulletedList', '-', 'Outdent', 'Indent', '-', 'JustifyLeft', 'JustifyCenter', 'JustifyRight', 'JustifyBlock'],
            ['Link', 'Unlink'],
            ['RemoveFormat', 'Source']
        ]
    }
}
########## END CKEDITOR CONFIGURATION


########## FCM DJANGO CONFIGURATION
FCM_DJANGO_SETTINGS = {
        "APP_VERBOSE_NAME": "pepup",
         # default: _('FCM Django')
        "FCM_SERVER_KEY": load_credential("FCM_SERVER_KEY", ""),
         # true if you want to have only one active device per registered user at a time
         # default: False
        "ONE_DEVICE_PER_USER": False,
         # devices to which notifications cannot be sent,
         # are deleted upon receiving error response from FCM
         # default: False
        "DELETE_INACTIVE_DEVICES": True,
}
########## FCM DJANGO CONFIGURATION

APPEND_SLASH = False

# toolbar
INTERNAL_IPS = ('127.0.0.1',)