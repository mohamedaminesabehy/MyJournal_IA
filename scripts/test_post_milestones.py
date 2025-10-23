import os, sys, json
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'my_journal_intime.settings_sqlite')
import django
django.setup()
from django.test import Client
from django.contrib.auth.models import User
from journal.models import Goal

c = Client()
# ensure test user exists
user, created = User.objects.get_or_create(username='test_milestones')
if created:
    user.set_password('TestPass123!')
    user.save()
logged = c.login(username='test_milestones', password='TestPass123!')
print('logged', logged)

milestones = [
    {"title": "Tâche A", "due": "2025-10-30", "done": False},
    {"title": "Tâche B", "due": None, "done": False}
]

post = {
    'title': 'Test milestones POST',
    'description': 'desc',
    'start_date': '2025-10-01',
    'end_date': '2025-11-01',
    'status': 'ongoing',
    'motivation_level': '5',
    'priority': '2',
    'difficulty': '3',
    'reward': '',
    'recurrence': '',
    'milestones': json.dumps(milestones),
}
resp = c.post('/goals/create/', data=post, HTTP_HOST='localhost', follow=True)
print('status', resp.status_code)
print('redirect_chain', resp.redirect_chain)

g = Goal.objects.filter(user=user, title__icontains='Test milestones POST').first()
print('goal', bool(g))
if g:
    print('milestones stored:', g.milestones)
else:
    print('response content:', resp.content[:400])
