from django import template
from django.contrib.admin.utils import (
    lookup_field, display_for_field, display_for_value, label_for_field,
)

register = template.Library()


@register.simple_tag
def admin_col_label(cl, field_name):
    """Корректный заголовок столбца (учитывает short_description / verbose_name)."""
    if field_name == 'id':
        return 'ID'
    try:
        label = label_for_field(field_name, cl.model, cl.model_admin)
    except Exception:
        label = field_name
    if not label:
        return field_name
    return label[:1].upper() + label[1:]


@register.simple_tag
def admin_col_value(cl, obj, field_name):
    """Значение ячейки. Работает и для полей модели, и для методов ModelAdmin,
    и для choice-полей (показывает человекочитаемое значение)."""
    try:
        f, attr, value = lookup_field(field_name, obj, cl.model_admin)
    except Exception:
        return ''
    if f is None:
        # Это метод/атрибут (например get_payment_display) — значение уже готово
        if value is None:
            return '—'
        if isinstance(value, bool):
            return 'Да' if value else 'Нет'
        return value
    # Это настоящее поле модели — форматируем через стандартный механизм админки
    try:
        return display_for_field(value, f, '—')
    except Exception:
        return display_for_value(value, '—')
