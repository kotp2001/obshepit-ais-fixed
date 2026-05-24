from django.db import models
from django.contrib.auth.models import User

class Category(models.Model):
    name  = models.CharField(max_length=100, verbose_name='Название')
    icon  = models.CharField(max_length=50, blank=True, verbose_name='Иконка')
    order = models.IntegerField(default=0, verbose_name='Порядок')

    class Meta:
        verbose_name        = 'Категория'
        verbose_name_plural = 'Категории'
        ordering            = ['order']

    def __str__(self):
        return self.name

class Dish(models.Model):
    name        = models.CharField(max_length=200, verbose_name='Название')
    description = models.TextField(blank=True, verbose_name='Описание')
    price       = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена')
    category    = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='dishes', verbose_name='Категория')
    image_url   = models.CharField(max_length=500, blank=True, verbose_name='URL фото')
    is_available= models.BooleanField(default=True, verbose_name='Доступно')
    weight      = models.CharField(max_length=50, blank=True, verbose_name='Вес')
    calories    = models.IntegerField(default=0, verbose_name='Калории')

    class Meta:
        verbose_name        = 'Блюдо'
        verbose_name_plural = 'Блюда'

    def __str__(self):
        return f'{self.name} - {self.price} ₽'

class Table(models.Model):
    STATUS_CHOICES = [('free','Свободен'),('occupied','Занят'),('reserved','Забронирован')]
    number     = models.IntegerField(unique=True, verbose_name='Номер стола')
    seats      = models.IntegerField(default=4, verbose_name='Количество мест')
    status     = models.CharField(max_length=20, choices=STATUS_CHOICES, default='free', verbose_name='Статус')
    x_position = models.IntegerField(default=0, verbose_name='X позиция')
    y_position = models.IntegerField(default=0, verbose_name='Y позиция')

    class Meta:
        verbose_name        = 'Стол'
        verbose_name_plural = 'Столы'

    def __str__(self):
        return f'Стол {self.number} ({self.seats} мест)'

class Order(models.Model):
    STATUS_CHOICES = [
        ('new','Новый'),('cooking','Готовится'),('ready','Готов'),
        ('served','Подано'),('paid','Оплачен'),('cancelled','Отменён'),
    ]
    PAYMENT_CHOICES = [('cash','Наличные'),('card','Карта'),('qr','QR-код')]

    table          = models.ForeignKey(Table, on_delete=models.CASCADE, related_name='orders', verbose_name='Стол')
    waiter         = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Официант')
    created_at     = models.DateTimeField(auto_now_add=True, verbose_name='Создан')
    updated_at     = models.DateTimeField(auto_now=True, verbose_name='Обновлён')
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new', verbose_name='Статус')
    total_amount   = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Сумма')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES, blank=True, null=True, verbose_name='Оплата')
    guest_count    = models.IntegerField(default=1, verbose_name='Количество гостей')
    comment        = models.TextField(blank=True, verbose_name='Комментарий')
    ready_at       = models.DateTimeField(null=True, blank=True, verbose_name='Время готовности')

    class Meta:
        db_table            = 'restaurant_order'
        verbose_name        = 'Заказ'
        verbose_name_plural = 'Заказы'
        db_table            = 'restaurant_order'
        ordering            = ['-created_at']

    def __str__(self):
        return f'Заказ #{self.id} - Стол {self.table.number}'

class OrderItem(models.Model):
    STATUS_CHOICES = [
        ('pending','В очереди'),('cooking','Готовится'),
        ('ready','Готов'),('served','Подано'),
    ]
    order    = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items', verbose_name='Заказ')
    dish     = models.ForeignKey(Dish, on_delete=models.PROTECT, verbose_name='Блюдо')
    quantity = models.IntegerField(default=1, verbose_name='Количество')
    price    = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена')
    status   = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='Статус')
    comment  = models.CharField(max_length=200, blank=True, verbose_name='Комментарий')

    class Meta:
        db_table            = 'restaurant_orderitem'
        db_table            = 'restaurant_orderitem'
        verbose_name        = 'Позиция заказа'
        verbose_name_plural = 'Позиции заказа'

    def __str__(self):
        return f'{self.dish.name} x{self.quantity}'

class MaintenanceLog(models.Model):
    date           = models.DateField(verbose_name='Дата')
    work_performed = models.TextField(verbose_name='Проведенная работа')
    performed_by   = models.CharField(max_length=100, verbose_name='Выполнил')
    signature      = models.CharField(max_length=100, blank=True, verbose_name='Подпись')
    created_at     = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    class Meta:
        verbose_name        = 'Журнал ТО'
        verbose_name_plural = 'Журналы ТО'
        ordering            = ['-date']

    def __str__(self):
        return f'{self.date} - {self.work_performed[:50]}'

class Profile(models.Model):
    ROLE_CHOICES = [('admin','Администратор'),('waiter','Официант'),('chef','Повар')]
    user     = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role     = models.CharField(max_length=20, choices=ROLE_CHOICES, default='waiter', verbose_name='Роль')
    pin_code = models.CharField(max_length=4, blank=True, null=True, verbose_name='Пин-код')

    class Meta:
        verbose_name        = 'Профиль'
        verbose_name_plural = 'Профили'

    def __str__(self):
        return f'{self.user.username} - {self.get_role_display()}'
