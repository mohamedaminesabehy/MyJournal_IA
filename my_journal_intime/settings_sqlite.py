"""
Temporary settings file for local testing using SQLite.
This imports most settings from the main settings and overrides DATABASES.
"""
from .settings import *  # import base settings

# Override database for local testing to use SQLite instead of MongoDB/Djongo
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Ensure djongo is not loaded in INSTALLED_APPS for local dev (prevents pymongo/djongo
# from being used when we want to run with SQLite). This keeps the rest of the
# project's settings intact while avoiding MongoDB calls during local testing.
INSTALLED_APPS = [app for app in INSTALLED_APPS if app != 'djongo']

# Use DB-backed sessions (will use the SQLite DB above)
SESSION_ENGINE = 'django.contrib.sessions.backends.db'