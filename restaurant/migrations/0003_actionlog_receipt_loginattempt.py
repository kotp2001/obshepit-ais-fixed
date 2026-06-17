from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):
    """
    Добавляет модели:
      * ActionLog    — журнал действий пользователей (вход, заказы, оплата...);
      * Receipt      — кассовый чек (PDF + сумма + способ оплаты);
      * LoginAttempt — учёт попыток входа для блокировки после 5 неудач.

    Как и 0002, используем обычные операции Django вместо «сырого» SQL —
    для совместимости с SQLite (локально) и PostgreSQL (Render).
    """

    dependencies = [
        ('restaurant', '0002_profile_maintenancelog'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # --- Журнал действий ---
        migrations.CreateModel(
            name='ActionLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(max_length=30, default='other', verbose_name='Действие')),
                ('description', models.TextField(blank=True, verbose_name='Описание')),
                ('ip_address', models.GenericIPAddressField(null=True, blank=True, verbose_name='IP-адрес')),
                ('timestamp', models.DateTimeField(auto_now_add=True, verbose_name='Время')),
                ('user', models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='Пользователь')),
            ],
            options={'verbose_name': 'Журнал действий', 'verbose_name_plural': 'Журнал действий', 'ordering': ['-timestamp']},
        ),

        # --- Кассовый чек ---
        migrations.CreateModel(
            name='Receipt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pdf_file', models.FileField(upload_to='receipts/', blank=True, null=True, verbose_name='PDF файл')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создан')),
                ('total', models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Сумма')),
                ('payment_method', models.CharField(max_length=20, blank=True, verbose_name='Способ оплаты')),
                ('order', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='receipt', to='restaurant.order', verbose_name='Заказ')),
            ],
            options={'verbose_name': 'Чек', 'verbose_name_plural': 'Чеки', 'ordering': ['-created_at']},
        ),

        # --- Попытки входа (для блокировки) ---
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
    ]
