from django.shortcuts import render, redirect
from django.http import HttpResponse, Http404
from django.contrib.admin.views.decorators import staff_member_required
import os
import shutil
from datetime import datetime

@staff_member_required
def backup_list(request):
    backup_dir = 'backups'
    backups = []
    
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    if request.method == 'POST':
        db_path = 'db.sqlite3'
        if os.path.exists(db_path):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = os.path.join(backup_dir, f'db_backup_{timestamp}.sqlite3')
            shutil.copy2(db_path, backup_path)
        return redirect('/backup-list/')
    
    if os.path.exists(backup_dir):
        for file in os.listdir(backup_dir):
            if file.endswith('.sqlite3'):
                file_path = os.path.join(backup_dir, file)
                stat = os.stat(file_path)
                backups.append({
                    'name': file,
                    'date': datetime.fromtimestamp(stat.st_ctime).strftime('%Y-%m-%d %H:%M:%S'),
                    'size': round(stat.st_size / 1024, 2)
                })
        backups.sort(key=lambda x: x['date'], reverse=True)
    
    return render(request, 'backup_list.html', {'backups': backups})

@staff_member_required
def backup_download(request, filename):
    backup_dir = 'backups'
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(backup_dir, safe_filename)
    
    if not os.path.exists(file_path):
        raise Http404("Файл не найден")
    
    with open(file_path, 'rb') as f:
        response = HttpResponse(f.read(), content_type='application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename="{safe_filename}"'
        return response

@staff_member_required
def backup_restore(request, filename):
    backup_dir = 'backups'
    safe_filename = os.path.basename(filename)
    backup_path = os.path.join(backup_dir, safe_filename)
    db_path = 'db.sqlite3'
    
    if not os.path.exists(backup_path):
        raise Http404("Файл не найден")
    
    shutil.copy2(backup_path, db_path)
    return redirect('/backup-list/')

@staff_member_required
def backup_delete(request, filename):
    backup_dir = 'backups'
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(backup_dir, safe_filename)
    
    if os.path.exists(file_path):
        os.remove(file_path)
    
    return redirect('/backup-list/')
