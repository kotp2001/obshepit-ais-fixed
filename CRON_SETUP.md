# Настройка автоматического резервного копирования через cron-job.org

## Проблема
Render.com (бесплатный тариф) не поддерживает встроенный cron.
Решение: использовать внешний сервис cron-job.org (бесплатно).

## Настройка

1. Зарегистрируйся на https://cron-job.org (бесплатно)

2. Создай новое задание:
   - URL: https://obshepit-ais-fixed.onrender.com/api/auto-backup/?key=obshepit-backup-2026
   - Расписание: Каждый день в 03:00
   - Method: GET

3. Опционально — смени секретный ключ:
   - В Render Dashboard → Environment Variables
   - Добавь: BACKUP_SECRET_KEY = ваш-секретный-ключ
   - Обнови URL в cron-job.org соответственно

## Что делает endpoint /api/auto-backup/
- Создаёт дамп PostgreSQL через pg_dump
- Удаляет копии старше 30 дней
- Записывает действие в журнал ActionLog
- Сохраняет файл в /tmp/backups/

## Проверка
Открой в браузере:
https://obshepit-ais-fixed.onrender.com/api/auto-backup/?key=obshepit-backup-2026
Должен вернуть: {"success": true, "file": "auto_backup_20260530_030000.sql"}
