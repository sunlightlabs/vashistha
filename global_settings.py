import os

INSTALLED_APPS = ('opencivicdata', 'django.contrib.staticfiles', 'django.contrib.humanize', 'dryrub', 'haystack')
STATIC_URL = '/static/'
STATICFILES_DIRS = (os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static'),)
TEMPLATE_CONTEXT_PROCESSORS = ("django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.static",
    "django.core.context_processors.tz",
    "django.contrib.messages.context_processors.messages",
    'dryrub.context_processors.custom_context',
)