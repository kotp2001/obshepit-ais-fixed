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

# Применяем миграции (только недостающие таблицы)
RUN python manage.py migrate --fake-initial --noinput

# Создаём пользователей (если их нет)
RUN python manage.py create_users

CMD gunicorn restaurant_project.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 120
