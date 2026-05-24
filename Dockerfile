FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN pip install --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Создаём нужные папки
RUN mkdir -p backups staticfiles media

# Собираем статику БЕЗ подключения к БД
# Используем простое хранилище чтобы не падать на билде
RUN DJANGO_SECRET_KEY=build-only-temp-key \
    DATABASE_URL="" \
    python manage.py collectstatic --noinput --settings=restaurant_project.settings

EXPOSE 8000

# При запуске: миграции → пользователи → начальные данные → сервер
CMD sh -c "\
    python manage.py migrate --noinput && \
    python manage.py create_users && \
    python create_migrations.py && \
    gunicorn restaurant_project.wsgi:application \
        --bind 0.0.0.0:8000 \
        --workers 2 \
        --timeout 120 \
        --log-level info"
