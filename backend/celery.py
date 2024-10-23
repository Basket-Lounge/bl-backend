"""
https://docs.celeryq.dev/en/stable/django/first-steps-with-django.html
"""
import os

from celery import Celery
from kombu import Queue

from django.conf import settings


# this code copied from manage.py
# set the default Django settings module for the 'celery' app.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

# you can change the name here
app = Celery("backend")

# read config from Django settings, the CELERY namespace would make celery
# config keys has `CELERY` prefix
app.config_from_object('django.conf:settings', namespace='CELERY')

# discover and load tasks.py from from all registered Django apps
# app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
app.autodiscover_tasks()

# define the default queue
app.conf.task_queues = (
    Queue('default', routing_key='default'),
    Queue('high_priority', routing_key='high_priority'),
    Queue('low_priority', routing_key='low_priority'),
    Queue('today_game_update', routing_key='today_game_update'),
)