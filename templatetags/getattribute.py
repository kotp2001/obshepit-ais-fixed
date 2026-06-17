from django import template

register = template.Library()

@register.filter
def getattribute(value, arg):
    """Возвращает атрибут объекта по имени."""
    return getattr(value, arg, '')
