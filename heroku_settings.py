DEBUG = False
ALLOWED_HOSTS = ['*']

import os, dj_database_url

if 'GEOS_LIBRARY_PATH' in os.environ:
    GEOS_LIBRARY_PATH = os.environ.get('GEOS_LIBRARY_PATH')
    GDAL_LIBRARY_PATH = os.environ.get('GDAL_LIBRARY_PATH')

HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'haystack_redis.RedisEngine',
        'PATH': os.environ['REDIS_URL'],
    },
}

DATABASES = {'default': dj_database_url.config()}
STATIC_ROOT = os.path.join(os.path.dirname(__file__), 'heroku_static')