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

RUN python manage.py migrate --fake-initial --noinput

# Создаём суперпользователя (если не существует) с правильным паролем
RUN python -c "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'restaurant_project.settings'); import django; django.setup(); from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(username='admin').exists() or User.objects.create_superuser('admin', 'admin@example.com', 'admin123')"

CMD gunicorn restaurant_project.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 120
