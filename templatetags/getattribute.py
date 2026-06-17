"""Шаблонный фильтр getattribute.

Позволяет в шаблоне получить значение атрибута объекта по имени, заданному
переменной: {{ obj|getattribute:field_name }}. Используется в кастомных
таблицах админки для динамического вывода полей из list_display.
"""
from django import template

register = template.Library()

@register.filter
def getattribute(value, arg):
    """Возвращает атрибут объекта по имени."""
    return getattr(value, arg, '')
