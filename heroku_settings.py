DEBUG = False
ALLOWED_HOSTS = ['*']

import os, dj_database_url

HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'haystack_redis.RedisEngine',
        'PATH': os.environ['REDIS_URL'],
    },
}

DATABASES = {'default': dj_database_url.config()}
STATIC_ROOT = os.path.join(os.path.dirname(__file__), 'heroku_static')