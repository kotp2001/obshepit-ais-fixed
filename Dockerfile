FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN pip install --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p backups staticfiles
RUN python manage.py collectstatic --noinput

# Выполняем миграции (создаёт все таблицы, включая auth_user)
RUN python manage.py migrate --noinput

# Создаём суперпользователя admin/admin123, если его нет
RUN python -c "
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'restaurant_project.settings')
django.setup()
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('Admin created')
"

CMD gunicorn restaurant_project.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 120
