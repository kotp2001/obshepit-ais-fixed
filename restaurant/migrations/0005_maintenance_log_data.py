from django.db import migrations
from datetime import date


# (смещение в днях от 1 мая, описание работы)
ENTRIES = [
    (0,  'Плановый осмотр сервера и проверка свободного места на диске'),
    (2,  'Обновление зависимостей Django до версии 4.2.7, перезапуск службы'),
    (3,  'Резервное копирование базы данных PostgreSQL, проверка целостности дампа'),
    (5,  'Проверка и очистка журнала действий пользователей от устаревших записей'),
    (7,  'Тестирование системы авторизации и блокировки после 5 неудачных попыток'),
    (8,  'Оптимизация SQL-запросов в модуле отчётов, добавление индексов'),
    (10, 'Проверка корректности формирования и печати кассовых чеков'),
    (12, 'Обновление SSL-сертификата и проверка HTTPS-соединения на Render'),
    (13, 'Профилактическая перезагрузка веб-сервера, проверка логов на ошибки'),
    (15, 'Проверка резервного копирования по расписанию (cron), удаление копий старше 30 дней'),
    (17, 'Тестирование интерфейса официанта и кухни на корректность статусов заказов'),
    (19, 'Аудит безопасности: проверка прав доступа и ролей сотрудников'),
]

PERFORMER = 'Дубровин КС'


def fill_logs(apps, schema_editor):
    MaintenanceLog = apps.get_model('restaurant', 'MaintenanceLog')
    # Не дублируем, если записи этого исполнителя уже есть
    if MaintenanceLog.objects.filter(performed_by=PERFORMER).exists():
        return
    for offset, work in ENTRIES:
        day = 1 + offset
        MaintenanceLog.objects.create(
            date=date(2026, 5, day),
            work_performed=work,
            performed_by=PERFORMER,
            signature='',
        )


def remove_logs(apps, schema_editor):
    MaintenanceLog = apps.get_model('restaurant', 'MaintenanceLog')
    MaintenanceLog.objects.filter(performed_by=PERFORMER).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('restaurant', '0004_order_created_at_default'),
    ]

    operations = [
        migrations.RunPython(fill_logs, remove_logs),
    ]
