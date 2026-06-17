from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):
    """
    Добавляет модели Profile (профиль с ролью) и MaintenanceLog (журнал ТО),
    поле ready_at в заказ и делает created_at редактируемым в админке.

    ВАЖНО: используются обычные операции Django (CreateModel/AddField), а не
    «сырой» SQL. Это делает миграцию переносимой между СУБД — она одинаково
    выполняется и на PostgreSQL (Render), и на SQLite (локальный запуск).
    """

    dependencies = [
        ('restaurant', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # --- Профиль пользователя (роль + пин-код) ---
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(
                    choices=[('admin', 'Администратор'), ('waiter', 'Официант'), ('chef', 'Повар')],
                    default='waiter', max_length=20, verbose_name='Роль',
                )),
                ('pin_code', models.CharField(blank=True, max_length=4, null=True, verbose_name='Пин-код')),
                ('user', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='profile',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={'verbose_name': 'Профиль', 'verbose_name_plural': 'Профили'},
        ),

        # --- Журнал технического обслуживания ---
        migrations.CreateModel(
            name='MaintenanceLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(verbose_name='Дата')),
                ('work_performed', models.TextField(verbose_name='Проведенная работа')),
                ('performed_by', models.CharField(max_length=100, verbose_name='Выполнил')),
                ('signature', models.CharField(blank=True, max_length=100, verbose_name='Подпись')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')),
            ],
            options={'verbose_name': 'Журнал ТО', 'verbose_name_plural': 'Журналы ТО', 'ordering': ['-date']},
        ),

        # --- Время готовности заказа ---
        migrations.AddField(
            model_name='order',
            name='ready_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Время готовности'),
        ),

        # --- created_at: убираем auto_now_add (только на уровне состояния Django),
        #     чтобы поле можно было редактировать в админке. Схему БД это не меняет. ---
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AlterField(
                    model_name='order',
                    name='created_at',
                    field=models.DateTimeField(blank=True, null=True, verbose_name='Создан'),
                ),
            ],
        ),
    ]
