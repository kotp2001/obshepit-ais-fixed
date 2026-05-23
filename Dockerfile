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

# Применяем миграции (только создаём записи в django_migrations)
RUN python manage.py migrate --fake-initial --noinput

# Временно отключаем создание пользователей и начальных данных,
# чтобы избежать ошибок с отсутствующей таблицей Profile.
# Позже, когда сайт запустится, вы сможете вернуть эти строки.
# RUN python manage.py create_users && \
#     python create_migrations.py

CMD gunicorn restaurant_project.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 120
