from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings

class Migration(migrations.Migration):
    """
    Добавляет Profile, MaintenanceLog и поле ready_at.
    Использует SeparateDatabaseAndState чтобы не падать
    если таблицы уже существуют в БД.
    """

    dependencies = [
        ('restaurant', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # --- Profile ---
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                        CREATE TABLE IF NOT EXISTS restaurant_profile (
                            id       BIGSERIAL PRIMARY KEY,
                            role     VARCHAR(20) NOT NULL DEFAULT 'waiter',
                            pin_code VARCHAR(4) NULL,
                            user_id  INT NOT NULL UNIQUE
                                REFERENCES auth_user(id) ON DELETE CASCADE
                        );
                    """,
                    reverse_sql="DROP TABLE IF EXISTS restaurant_profile;",
                ),
            ],
            state_operations=[
                migrations.CreateModel(
                    name='Profile',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('role', models.CharField(
                            choices=[('admin','Администратор'),('waiter','Официант'),('chef','Повар')],
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
            ],
        ),

        # --- MaintenanceLog ---
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                        CREATE TABLE IF NOT EXISTS restaurant_maintenancelog (
                            id             BIGSERIAL PRIMARY KEY,
                            date           DATE NOT NULL,
                            work_performed TEXT NOT NULL,
                            performed_by   VARCHAR(100) NOT NULL,
                            signature      VARCHAR(100) NOT NULL DEFAULT '',
                            created_at     TIMESTAMP NOT NULL DEFAULT NOW()
                        );
                    """,
                    reverse_sql="DROP TABLE IF EXISTS restaurant_maintenancelog;",
                ),
            ],
            state_operations=[
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
            ],
        ),

        # --- ready_at в Order ---
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="ALTER TABLE restaurant_order ADD COLUMN IF NOT EXISTS ready_at TIMESTAMP NULL;",
                    reverse_sql="ALTER TABLE restaurant_order DROP COLUMN IF EXISTS ready_at;",
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name='order',
                    name='ready_at',
                    field=models.DateTimeField(blank=True, null=True, verbose_name='Время готовности'),
                ),
            ],
        ),
    ]
