"""WSGI-конфигурация проекта.
Именно через объект application веб-сервер (gunicorn) запускает Django."""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'restaurant_project.settings')
application = get_wsgi_application()
