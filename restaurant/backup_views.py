"""
Резервное копирование операционных данных.

Копии хранятся ПРЯМО В БАЗЕ ДАННЫХ (модель DatabaseBackup), а не в файловой
системе. На Render файловая система эфемерная — при каждом передеплое/перезапуске
файлы из папки backups/ стираются, поэтому раньше копии и «пропадали». БД на Render
постоянна, значит копии теперь хранятся вечно и всегда видны в списке.

Восстановление работает корректно: оно полностью заменяет текущие операционные
данные снимком из копии (старые записи удаляются, загружаются записи из копии).
Поэтому заказ, добавленный ПОСЛЕ создания копии, после восстановления исчезает —
ровно как и ожидается.
"""
import json
from datetime import datetime
from itertools import chain

from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.core import serializers
from django.db import transaction
from django.contrib.auth.models import User

from .models import (
    Category, Dish, Table, Order, OrderItem, Receipt,
    MaintenanceLog, ActionLog, DatabaseBackup,
)

# Порядок ВАЖЕН: родительские модели идут раньше дочерних, чтобы при загрузке
# внешние ключи всегда находили свои объекты.
BACKUP_MODELS = [Category, Dish, Table, Order, OrderItem, Receipt, MaintenanceLog, ActionLog]
# Для удаления — в обратном порядке (сначала дочерние).
DELETE_MODELS = [Receipt, OrderItem, Order, Dish, Table, Category, MaintenanceLog, ActionLog]


def _serialize_all():
    objs = list(chain.from_iterable(m.objects.all() for m in BACKUP_MODELS))
    data = serializers.serialize('json', objs, indent=2, ensure_ascii=False)
    return data, len(objs)


def _log(request, text):
    try:
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        ip = xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR', '127.0.0.1')
        ActionLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            action='create_backup', description=text, ip_address=ip,
        )
    except Exception:
        pass


@staff_member_required
def backup_list(request):
    backups = DatabaseBackup.objects.all()
    return render(request, 'backup_list.html', {'backups': backups})


@staff_member_required
def backup_create(request):
    if request.method != 'POST':
        return redirect('backup:backup_list')
    try:
        data, count = _serialize_all()
        timestamp = datetime.now().strftime('%d.%m.%Y %H:%M:%S')
        backup = DatabaseBackup.objects.create(
            name=f'Копия от {timestamp}',
            data=data,
            size=len(data.encode('utf-8')),
            records_count=count,
            fmt='json',
            note=request.POST.get('note', '').strip()[:300],
        )
        _log(request, f'Создана резервная копия #{backup.id} ({count} записей)')
        messages.success(request, f'Резервная копия создана: {count} записей.')
    except Exception as e:
        messages.error(request, f'Ошибка создания копии: {e}')
    return redirect('backup:backup_list')


@staff_member_required
def backup_download(request, pk):
    backup = get_object_or_404(DatabaseBackup, pk=pk)
    ext = 'json' if backup.fmt == 'json' else 'sql'
    fname = f'backup_{backup.id}.{ext}'
    response = HttpResponse(backup.data, content_type='application/json' if ext == 'json' else 'text/plain')
    response['Content-Disposition'] = f'attachment; filename="{fname}"'
    return response


@staff_member_required
def backup_restore(request, pk):
    backup = get_object_or_404(DatabaseBackup, pk=pk)
    if backup.fmt != 'json':
        messages.error(
            request,
            'Эта копия в старом формате (.sql) и не может быть восстановлена новой системой. '
            'Восстанавливаются только копии, созданные текущей системой (формат .json).'
        )
        return redirect('backup:backup_list')
    try:
        existing_users = set(User.objects.values_list('pk', flat=True))
        with transaction.atomic():
            # 1. Полностью очищаем текущие операционные данные
            for model in DELETE_MODELS:
                model.objects.all().delete()
            # 2. Загружаем снимок из копии
            for d in serializers.deserialize('json', backup.data):
                obj = d.object
                # Подстраховка по внешним ключам на пользователей (вдруг кого-то удалили)
                for fk in ('user_id', 'waiter_id'):
                    if getattr(obj, fk, None) and getattr(obj, fk) not in existing_users:
                        setattr(obj, fk, None)
                d.save()
        _log(request, f'Восстановление из копии #{backup.id}')
        messages.success(request, f'База восстановлена из копии «{backup.name}». Текущие данные заменены снимком.')
    except Exception as e:
        messages.error(request, f'Ошибка восстановления: {e}')
    return redirect('backup:backup_list')


@staff_member_required
def backup_delete(request, pk):
    backup = get_object_or_404(DatabaseBackup, pk=pk)
    name = backup.name
    backup.delete()
    messages.success(request, f'Копия «{name}» удалена.')
    return redirect('backup:backup_list')


@staff_member_required
def backup_upload(request):
    if request.method == 'POST' and request.FILES.get('backup_file'):
        f = request.FILES['backup_file']
        raw = f.read()
        try:
            content = raw.decode('utf-8')
        except UnicodeDecodeError:
            content = raw.decode('utf-8', errors='replace')
        name = f.name
        fmt = 'json' if name.lower().endswith('.json') else 'sql'
        count = 0
        if fmt == 'json':
            try:
                count = len(json.loads(content))
            except Exception:
                fmt = 'sql'  # не наш формат — пометим как невосстанавливаемый
        DatabaseBackup.objects.create(
            name=f'Загружено: {name}',
            data=content,
            size=len(raw),
            records_count=count,
            fmt=fmt,
            note='Загружено вручную',
        )
        if fmt == 'json':
            messages.success(request, f'Файл «{name}» загружен и доступен для восстановления.')
        else:
            messages.success(request, f'Файл «{name}» сохранён (старый формат — только для скачивания).')
    else:
        messages.error(request, 'Выберите файл резервной копии (.json).')
    return redirect('backup:backup_list')
