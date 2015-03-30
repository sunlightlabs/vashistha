from app import application as _application
from dj_static import Cling

import os
if not os.path.exists(os.path.join(os.path.dirname(__file__), 'heroku_static')):
    # make sure collectstatic has happened
    from django.core.management import execute_from_command_line
    execute_from_command_line(['./manage.py', 'collectstatic', '--noinput'])

application = Cling(_application)