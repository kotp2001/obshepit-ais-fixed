FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN pip install --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Создаём папки для бэкапов и статических файлов
RUN mkdir -p backups staticfiles

# Собираем статику (эта команда не требует подключения к БД)
RUN python manage.py migrate --fake-initial --noinput

# Запускаем: применяем миграции (с флагом --fake-initial),
# создаём пользователей, заполняем начальными данными и запускаем сервер
CMD python manage.py migrate --fake-initial --noinput && \
    python manage.py create_users && \
    python create_migrations.py && \
    gunicorn restaurant_project.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 120
