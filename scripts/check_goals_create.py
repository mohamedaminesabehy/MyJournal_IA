import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'my_journal_intime.settings_sqlite')
import django
django.setup()
from django.test import Client
c = Client()
# Use a logged in user if exists
from django.contrib.auth.models import User
u = User.objects.first()
if u:
    logged = c.login(username=u.username, password='TestPass123!')
else:
    logged = False
print('Logged:', logged)
resp = c.get('/goals/create/', HTTP_HOST='localhost')
print('Status:', resp.status_code)
print(resp.content[:400])
