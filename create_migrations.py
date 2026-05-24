"""
Скрипт начального заполнения БД.
Запускается при старте контейнера ПОСЛЕ manage.py migrate.
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'restaurant_project.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.contrib.auth import get_user_model
from restaurant.models import Category, Dish, Table

User = get_user_model()

print("Заполняем начальные данные...")

# Категории
if Category.objects.count() == 0:
    categories = [
        {'name': 'Салаты',        'icon': 'salad', 'order': 1},
        {'name': 'Горячие блюда', 'icon': 'hot',   'order': 2},
        {'name': 'Гарниры',       'icon': 'fries',  'order': 3},
        {'name': 'Напитки',       'icon': 'drink',  'order': 4},
        {'name': 'Десерты',       'icon': 'cake',   'order': 5},
    ]
    for cat in categories:
        Category.objects.create(**cat)
    print("  Категории добавлены")
else:
    print("  Категории уже есть")

# Блюда
if Dish.objects.count() == 0:
    dishes = [
        {'name': 'Цезарь с курицей',    'price': 450, 'category_id': 1, 'description': 'Курица, салат, сухарики, соус цезарь'},
        {'name': 'Греческий салат',      'price': 380, 'category_id': 1, 'description': 'Сыр фета, маслины, огурцы, помидоры'},
        {'name': 'Стейк из говядины',   'price': 890, 'category_id': 2, 'description': 'Мраморная говядина 250г, соус на выбор'},
        {'name': 'Свиная отбивная',     'price': 590, 'category_id': 2, 'description': 'Свинина на кости, картофель фри'},
        {'name': 'Картофель фри',       'price': 150, 'category_id': 3, 'description': 'Хрустящий картофель с солью'},
        {'name': 'Рис отварной',        'price': 120, 'category_id': 3, 'description': 'С маслом и зеленью'},
        {'name': 'Пюре картофельное',   'price': 130, 'category_id': 3, 'description': 'Нежное пюре со сливками'},
        {'name': 'Чай чёрный',          'price': 80,  'category_id': 4, 'description': 'Цейлонский чай'},
        {'name': 'Чай зелёный',         'price': 80,  'category_id': 4, 'description': 'Зелёный чай'},
        {'name': 'Кофе американо',      'price': 120, 'category_id': 4, 'description': 'Свежесваренный кофе'},
        {'name': 'Капучино',            'price': 150, 'category_id': 4, 'description': 'Кофе с молочной пенкой'},
        {'name': 'Латте',               'price': 160, 'category_id': 4, 'description': 'Кофе с большим количеством молока'},
        {'name': 'Чизкейк',             'price': 250, 'category_id': 5, 'description': 'Классический чизкейк с ягодным соусом'},
        {'name': 'Тирамису',            'price': 280, 'category_id': 5, 'description': 'Кофейный десерт маскарпоне'},
        {'name': 'Мороженое',           'price': 120, 'category_id': 5, 'description': 'Пломбир с шоколадной крошкой'},
    ]
    for dish in dishes:
        Dish.objects.create(**dish)
    print("  Блюда добавлены")
else:
    print("  Блюда уже есть")

# Столы
if Table.objects.count() == 0:
    tables = [
        {'number': 1, 'seats': 2, 'status': 'free'},
        {'number': 2, 'seats': 2, 'status': 'free'},
        {'number': 3, 'seats': 4, 'status': 'free'},
        {'number': 4, 'seats': 4, 'status': 'free'},
        {'number': 5, 'seats': 4, 'status': 'free'},
        {'number': 6, 'seats': 6, 'status': 'free'},
        {'number': 7, 'seats': 6, 'status': 'free'},
        {'number': 8, 'seats': 8, 'status': 'free'},
    ]
    for table in tables:
        Table.objects.create(**table)
    print("  Столы добавлены")
else:
    print("  Столы уже есть")

print("Начальные данные готовы.")
