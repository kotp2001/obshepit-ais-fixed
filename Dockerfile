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

# Теперь просто применяем миграции с флагом --fake-initial.
# Django создаст записи в django_migrations, не трогая существующие таблицы.
RUN python manage.py migrate --fake-initial --noinput

# Команда create_users и create_migrations.py – опциональны, 
# но если они есть в проекте и нужны – оставьте их здесь или перенесите в CMD.
# Для экономии времени на сборке я рекомендую перенести их в CMD:

CMD python manage.py create_users && \
    python create_migrations.py && \
    gunicorn restaurant_project.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 120
