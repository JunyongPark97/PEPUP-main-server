from .base import *

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '^#cq1k#!!rqqa0x7z$7sz%qo$!r6naggu=)tjijn%agaopq!_g'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['127.0.0.1', 'localhost']

# Database
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}