FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN pip install --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Создаём папку для бэкапов и статики
RUN mkdir -p backups staticfiles

# Собираем статику (не требует БД)
RUN python manage.py collectstatic --noinput

EXPOSE 8000

# Запускаем: миграции + пользователи + данные + сервер
CMD python manage.py migrate --noinput && \
    python manage.py create_users && \
    python create_migrations.py && \
    gunicorn restaurant_project.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 120
