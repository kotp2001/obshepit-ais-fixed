"""
restaurant/backup_views.py
Функции для управления резервными копиями (бэкапами) базы данных.

Включает: список, создание, скачивание, восстановление, удаление и загрузку бэкапов.
Копии хранятся в папке backups/ внутри проекта и также загружаются в GitHub.
"""

import os
import subprocess
from datetime import datetime
from django.shortcuts import render, redirect
from django.http import HttpResponse, Http404
from django.contrib.admin.views.decorators import staff_member_required
from django.conf import settings
from django.contrib import messages

BACKUP_DIR = os.path.join(settings.BASE_DIR, 'backups')


def ensure_backup_dir():
    """Гарантирует существование папки для бэкапов."""
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)


@staff_member_required
def backup_list(request):
    """
    Отображает список всех резервных копий (файлов .sql) с датой и размером.
    """
    ensure_backup_dir()
    backups = []
    for fname in sorted(os.listdir(BACKUP_DIR), reverse=True):
        if fname.endswith('.sql'):
            fpath = os.path.join(BACKUP_DIR, fname)
            stat = os.stat(fpath)
            backups.append({
                'name': fname,
                'date': datetime.fromtimestamp(stat.st_mtime).strftime('%d.%m.%Y %H:%M'),
                'size': round(stat.st_size / 1024, 1)
            })
    return render(request, 'backup_list.html', {'backups': backups})


@staff_member_required
def backup_create(request):
    """
    Создаёт новую резервную копию базы данных через pg_dump.
    После создания загружает копию в GitHub (если настроен токен).
    """
    if request.method != 'POST':
        return redirect('backup:backup_list')

    ensure_backup_dir()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'backup_{timestamp}.sql'
    filepath = os.path.join(BACKUP_DIR, filename)

    db = settings.DATABASES['default']
    env = os.environ.copy()
    env['PGPASSWORD'] = db.get('PASSWORD', '')

    try:
        result = subprocess.run([
            'pg_dump', '-h', db['HOST'], '-p', str(db.get('PORT', 5432)),
            '-U', db['USER'], '-d', db['NAME'], '-f', filepath, '--no-password'
        ], env=env, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            # Очищаем файл от лишних мета-команд
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
            with open(filepath, 'w', encoding='utf-8') as f:
                f.writelines(l for l in lines if not l.startswith('\\'))

            # Загружаем в GitHub (если функция доступна)
            try:
                from .views import upload_backup_to_github
                upload_backup_to_github(filepath, filename)
            except ImportError:
                pass

            # messages.success(request, f'Резервная копия {filename} создана.')  # скрываем сообщение
        else:
            messages.error(request, f'Ошибка pg_dump: {result.stderr[:200]}')
    except Exception as e:
        messages.error(request, f'Ошибка: {str(e)}')
    return redirect('backup:backup_list')


@staff_member_required
def backup_download(request, filename):
    """Скачивает указанный файл резервной копии."""
    ensure_backup_dir()
    safe_name = os.path.basename(filename)
    filepath = os.path.join(BACKUP_DIR, safe_name)
    if not os.path.exists(filepath):
        raise Http404("Файл не найден")
    with open(filepath, 'rb') as f:
        response = HttpResponse(f.read(), content_type='application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename="{safe_name}"'
        return response


@staff_member_required
def backup_restore(request, filename):
    """
    Восстанавливает базу данных из указанной резервной копии (psql -f).
    ВАЖНО: текущие данные будут полностью перезаписаны.
    """
    ensure_backup_dir()
    safe_name = os.path.basename(filename)
    filepath = os.path.join(BACKUP_DIR, safe_name)
    if not os.path.exists(filepath):
        raise Http404("Файл не найден")

    db = settings.DATABASES['default']
    env = os.environ.copy()
    env['PGPASSWORD'] = db.get('PASSWORD', '')

    try:
        result = subprocess.run([
            'psql', '-h', db['HOST'], '-p', str(db.get('PORT', 5432)),
            '-U', db['USER'], '-d', db['NAME'], '-f', filepath, '--no-password'
        ], env=env, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            messages.error(request, f'Ошибка восстановления: {result.stderr[:200]}')
        else:
            messages.success(request, f'База данных восстановлена из {filename}.')
    except Exception as e:
        messages.error(request, f'Ошибка: {str(e)}')
    return redirect('backup:backup_list')


@staff_member_required
def backup_delete(request, filename):
    """Удаляет файл резервной копии (без вывода сообщения об успехе)."""
    ensure_backup_dir()
    safe_name = os.path.basename(filename)
    filepath = os.path.join(BACKUP_DIR, safe_name)
    if os.path.exists(filepath):
        os.remove(filepath)
        # Сообщение удалено, чтобы не появлялось уведомление «Стол удалён»
    return redirect('backup:backup_list')


@staff_member_required
def backup_upload(request):
    """
    Загружает файл резервной копии (например, с локального компьютера) на сервер.
    Сохраняет его в папку backups/.
    """
    if request.method == 'POST' and request.FILES.get('backup_file'):
        uploaded_file = request.FILES['backup_file']
        ensure_backup_dir()
        filepath = os.path.join(BACKUP_DIR, uploaded_file.name)
        with open(filepath, 'wb+') as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)
        messages.success(request, f'Файл {uploaded_file.name} успешно загружен.')
    else:
        messages.error(request, 'Пожалуйста, выберите файл для загрузки.')
    return redirect('backup:backup_list')
