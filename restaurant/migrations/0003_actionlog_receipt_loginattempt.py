from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('restaurant', '0002_profile_maintenancelog'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [

        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                    CREATE TABLE IF NOT EXISTS restaurant_actionlog (
                        id          BIGSERIAL PRIMARY KEY,
                        user_id     INT NULL REFERENCES auth_user(id) ON DELETE SET NULL,
                        action      VARCHAR(30) NOT NULL DEFAULT 'other',
                        description TEXT NOT NULL DEFAULT '',
                        ip_address  INET NULL,
                        timestamp   TIMESTAMP NOT NULL DEFAULT NOW()
                    );
                    """,
                    reverse_sql="DROP TABLE IF EXISTS restaurant_actionlog;",
                ),
            ],
            state_operations=[
                migrations.CreateModel(
                    name='ActionLog',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True)),
                        ('action', models.CharField(max_length=30, default='other', verbose_name='Действие')),
                        ('description', models.TextField(blank=True, verbose_name='Описание')),
                        ('ip_address', models.GenericIPAddressField(null=True, blank=True, verbose_name='IP-адрес')),
                        ('timestamp', models.DateTimeField(auto_now_add=True, verbose_name='Время')),
                        ('user', models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='Пользователь')),
                    ],
                    options={'verbose_name': 'Журнал действий', 'verbose_name_plural': 'Журнал действий', 'ordering': ['-timestamp']},
                ),
            ],
        ),

        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                    CREATE TABLE IF NOT EXISTS restaurant_receipt (
                        id             BIGSERIAL PRIMARY KEY,
                        order_id       INT NOT NULL UNIQUE REFERENCES restaurant_order(id) ON DELETE CASCADE,
                        pdf_file       VARCHAR(100) NULL,
                        created_at     TIMESTAMP NOT NULL DEFAULT NOW(),
                        total          NUMERIC(10,2) NOT NULL DEFAULT 0,
                        payment_method VARCHAR(20) NOT NULL DEFAULT ''
                    );
                    """,
                    reverse_sql="DROP TABLE IF EXISTS restaurant_receipt;",
                ),
            ],
            state_operations=[
                migrations.CreateModel(
                    name='Receipt',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True)),
                        ('pdf_file', models.FileField(upload_to='receipts/', blank=True, null=True, verbose_name='PDF файл')),
                        ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создан')),
                        ('total', models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Сумма')),
                        ('payment_method', models.CharField(max_length=20, blank=True, verbose_name='Способ оплаты')),
                        ('order', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='receipt', to='restaurant.order', verbose_name='Заказ')),
                    ],
                    options={'verbose_name': 'Чек', 'verbose_name_plural': 'Чеки', 'ordering': ['-created_at']},
                ),
            ],
        ),

        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                    CREATE TABLE IF NOT EXISTS restaurant_loginattempt (
                        id             BIGSERIAL PRIMARY KEY,
                        username       VARCHAR(150) NOT NULL,
                        ip_address     INET NULL,
                        attempts       INT NOT NULL DEFAULT 0,
                        blocked_until  TIMESTAMP NULL,
                        last_attempt   TIMESTAMP NOT NULL DEFAULT NOW(),
                        UNIQUE (username, ip_address)
                    );
                    """,
                    reverse_sql="DROP TABLE IF EXISTS restaurant_loginattempt;",
                ),
            ],
            state_operations=[
                migrations.CreateModel(
                    name='LoginAttempt',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True)),
                        ('username', models.CharField(max_length=150, verbose_name='Логин')),
                        ('ip_address', models.GenericIPAddressField(null=True, blank=True, verbose_name='IP')),
                        ('attempts', models.IntegerField(default=0, verbose_name='Попыток')),
                        ('blocked_until', models.DateTimeField(null=True, blank=True, verbose_name='Заблокирован до')),
                        ('last_attempt', models.DateTimeField(auto_now=True, verbose_name='Последняя попытка')),
                    ],
                    options={'verbose_name': 'Попытка входа', 'verbose_name_plural': 'Попытки входа', 'unique_together': {('username', 'ip_address')}},
                ),
            ],
        ),
    ]
