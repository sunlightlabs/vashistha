ALLOWED_HOSTS = ['*']

import os, dj_database_url, dj_haystack_url, django_cache_url

DEBUG = {'False': False, 'True': True}[os.environ.get('DEBUG', 'False')]

HAYSTACK_CONNECTIONS = {'default': dj_haystack_url.config()}
DATABASES = {'default': dj_database_url.config()}
STATIC_ROOT = os.path.join(os.path.dirname(__file__), 'heroku_static')
CACHES = {'default': django_cache_url.config()}