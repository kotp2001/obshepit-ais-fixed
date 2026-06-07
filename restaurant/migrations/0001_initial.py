from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings

class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='Название')),
                ('icon', models.CharField(blank=True, max_length=50, verbose_name='Иконка')),
                ('order', models.IntegerField(default=0, verbose_name='Порядок')),
            ],
            options={'verbose_name': 'Категория', 'verbose_name_plural': 'Категории', 'ordering': ['order']},
        ),
        migrations.CreateModel(
            name='Dish',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='Название')),
                ('description', models.TextField(blank=True, verbose_name='Описание')),
                ('price', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Цена')),
                ('image_url', models.CharField(blank=True, max_length=500, verbose_name='URL фото')),
                ('is_available', models.BooleanField(default=True, verbose_name='Доступно')),
                ('weight', models.CharField(blank=True, max_length=50, verbose_name='Вес')),
                ('calories', models.IntegerField(default=0, verbose_name='Калории')),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='dishes', to='restaurant.category', verbose_name='Категория')),
            ],
            options={'verbose_name': 'Блюдо', 'verbose_name_plural': 'Блюда'},
        ),
        migrations.CreateModel(
            name='Table',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('number', models.IntegerField(unique=True, verbose_name='Номер стола')),
                ('seats', models.IntegerField(default=4, verbose_name='Количество мест')),
                ('status', models.CharField(choices=[('free','Свободен'),('occupied','Занят'),('reserved','Забронирован')], default='free', max_length=20, verbose_name='Статус')),
                ('x_position', models.IntegerField(default=0, verbose_name='X позиция')),
                ('y_position', models.IntegerField(default=0, verbose_name='Y позиция')),
            ],
            options={'verbose_name': 'Стол', 'verbose_name_plural': 'Столы'},
        ),
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создан')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Обновлён')),
                ('status', models.CharField(choices=[('new','Новый'),('cooking','Готовится'),('ready','Готов'),('served','Подано'),('paid','Оплачен'),('cancelled','Отменён')], default='new', max_length=20, verbose_name='Статус')),
                ('total_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='Сумма')),
                ('payment_method', models.CharField(blank=True, choices=[('cash','Наличные'),('card','Карта'),('qr','QR-код')], max_length=20, null=True, verbose_name='Оплата')),
                ('guest_count', models.IntegerField(default=1, verbose_name='Количество гостей')),
                ('comment', models.TextField(blank=True, verbose_name='Комментарий')),
                ('table', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='orders', to='restaurant.table', verbose_name='Стол')),
                ('waiter', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='Официант')),
            ],
            options={'verbose_name': 'Заказ', 'verbose_name_plural': 'Заказы', 'ordering': ['-created_at'], 'db_table': 'restaurant_order'},
        ),
        migrations.CreateModel(
            name='OrderItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.IntegerField(default=1, verbose_name='Количество')),
                ('price', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Цена')),
                ('status', models.CharField(choices=[('pending','В очереди'),('cooking','Готовится'),('ready','Готов'),('served','Подано')], default='pending', max_length=20, verbose_name='Статус')),
                ('comment', models.CharField(blank=True, max_length=200, verbose_name='Комментарий')),
                ('dish', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='restaurant.dish', verbose_name='Блюдо')),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='restaurant.order', verbose_name='Заказ')),
            ],
            options={'verbose_name': 'Позиция заказа', 'verbose_name_plural': 'Позиции заказа', 'db_table': 'restaurant_orderitem'},
        ),
    ]
