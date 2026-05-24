"""
Скрипт начального заполнения БД.
Запускается при старте контейнера ПОСЛЕ manage.py migrate и create_users.
"""
import os, sys, django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'restaurant_project.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from restaurant.models import Category, Dish, Table

print("Заполняем начальные данные...")

# Категории
if Category.objects.count() == 0:
    for cat in [
        {'name': 'Салаты',        'icon': 'salad', 'order': 1},
        {'name': 'Горячие блюда', 'icon': 'hot',   'order': 2},
        {'name': 'Гарниры',       'icon': 'fries',  'order': 3},
        {'name': 'Напитки',       'icon': 'drink',  'order': 4},
        {'name': 'Десерты',       'icon': 'cake',   'order': 5},
    ]:
        Category.objects.create(**cat)
    print("  Категории добавлены")
else:
    print("  Категории уже есть")

# Блюда
if Dish.objects.count() == 0:
    dishes = [
        ('Цезарь с курицей',   450, 1, 'Курица, салат, сухарики, соус цезарь'),
        ('Греческий салат',    380, 1, 'Сыр фета, маслины, огурцы, помидоры'),
        ('Стейк из говядины',  890, 2, 'Мраморная говядина 250г, соус на выбор'),
        ('Свиная отбивная',    590, 2, 'Свинина на кости, картофель фри'),
        ('Картофель фри',      150, 3, 'Хрустящий картофель с солью'),
        ('Рис отварной',       120, 3, 'С маслом и зеленью'),
        ('Пюре картофельное',  130, 3, 'Нежное пюре со сливками'),
        ('Чай чёрный',          80, 4, 'Цейлонский чай'),
        ('Чай зелёный',         80, 4, 'Зелёный чай'),
        ('Кофе американо',     120, 4, 'Свежесваренный кофе'),
        ('Капучино',           150, 4, 'Кофе с молочной пенкой'),
        ('Чизкейк',            250, 5, 'Классический чизкейк с ягодным соусом'),
        ('Тирамису',           280, 5, 'Кофейный десерт маскарпоне'),
        ('Мороженое',          120, 5, 'Пломбир с шоколадной крошкой'),
    ]
    cats = {c.order: c for c in Category.objects.all()}
    for name, price, cat_order, desc in dishes:
        Dish.objects.create(name=name, price=price, category=cats[cat_order], description=desc)
    print("  Блюда добавлены")
else:
    print("  Блюда уже есть")

# Столы
if Table.objects.count() == 0:
    for num, seats in [(1,2),(2,2),(3,4),(4,4),(5,4),(6,6),(7,6),(8,8)]:
        Table.objects.create(number=num, seats=seats, status='free')
    print("  Столы добавлены")
else:
    print("  Столы уже есть")

print("Готово!")
