from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils.dateparse import parse_datetime
from datetime import datetime, timedelta
import json, os, shutil, subprocess
from decimal import Decimal
from .models import Category, Dish, Table, Order, OrderItem, MaintenanceLog, Profile

# ==================== СТРАНИЦЫ ====================

def landing(request):
    return render(request, 'landing.html')

def admin_panel(request):
    return render(request, 'admin_panel.html')

def waiter_hall(request):
    return render(request, 'waiter_hall.html')

def kitchen_view(request):
    return render(request, 'kitchen.html')

def reports_view(request):
    return render(request, 'reports.html')

def help_page(request):
    return render(request, 'help.html')

def docs_page(request):
    return render(request, 'docs.html')

def maintenance_log_page(request):
    return render(request, 'maintenance_log.html')

# ==================== API АВТОРИЗАЦИИ ====================

@csrf_exempt
@require_http_methods(["POST"])
def api_login(request):
    try:
        body = json.loads(request.body)
        username = body.get('username', '').strip()
        password = body.get('password', '').strip()

        from django.contrib.auth import authenticate, login
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            role = 'staff'
            if user.is_superuser:
                role = 'admin'
            elif hasattr(user, 'profile') and user.profile.role:
                role = user.profile.role
            return JsonResponse({'success': True, 'role': role, 'username': user.username})
        else:
            return JsonResponse({'success': False, 'error': 'Неверный логин или пароль'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

# ==================== API БЛЮДА / КАТЕГОРИИ / СТОЛЫ ====================

@require_http_methods(["GET"])
def api_dishes(request):
    dishes = Dish.objects.filter(is_available=True).select_related('category')
    data = [{
        'id': d.id, 'name': d.name, 'description': d.description,
        'price': float(d.price), 'category': d.category.name,
        'category_id': d.category.id,
    } for d in dishes]
    return JsonResponse({'success': True, 'data': data})

@require_http_methods(["GET"])
def api_categories(request):
    cats = Category.objects.all().order_by('order')
    return JsonResponse({'success': True, 'data': [{'id': c.id, 'name': c.name, 'icon': c.icon} for c in cats]})

@require_http_methods(["GET"])
def api_tables(request):
    tables = Table.objects.all().order_by('number')
    data = [{'id': t.id, 'number': t.number, 'seats': t.seats, 'status': t.status} for t in tables]
    return JsonResponse({'success': True, 'data': data})

# ==================== API ЗАКАЗЫ ====================

@csrf_exempt
@require_http_methods(["POST"])
def api_create_order(request):
    try:
        body = json.loads(request.body)
        table_id  = body.get('table_id')
        items     = body.get('items', [])
        guest_count = body.get('guest_count', 1)
        client_time = body.get('client_time')

        table = Table.objects.get(id=table_id)

        # Время: берём локальное от браузера, избегаем UTC-сдвига
        if client_time:
            parsed = parse_datetime(client_time)
            if parsed is not None:
                current_time = parsed.astimezone().replace(tzinfo=None) if parsed.tzinfo else parsed
            else:
                current_time = datetime.now()
        else:
            current_time = datetime.now()

        order = Order.objects.create(
            table=table, status='new',
            guest_count=guest_count,
            created_at=current_time, updated_at=current_time
        )
        # auto_now_add игнорирует значение при create — обновляем явно
        Order.objects.filter(pk=order.pk).update(created_at=current_time)

        total = Decimal('0')
        for item in items:
            dish = Dish.objects.get(id=item['dish_id'])
            OrderItem.objects.create(
                order=order, dish=dish,
                quantity=item['quantity'],
                price=dish.price, status='pending'
            )
            total += dish.price * item['quantity']

        order.total_amount = total
        order.save()
        table.status = 'occupied'
        table.save()

        return JsonResponse({'success': True, 'order_id': order.id, 'total': float(total)})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@require_http_methods(["GET"])
def api_active_orders(request):
    orders = Order.objects.filter(
        status__in=['new', 'cooking', 'ready']
    ).select_related('table').prefetch_related('items__dish')
    data = []
    for order in orders:
        items = [{
            'id': item.id,
            'dish_name': item.dish.name,
            'quantity': item.quantity,
            'status': item.status,
        } for item in order.items.all()]
        data.append({
            'id': order.id,
            'table_number': order.table.number,
            'created_at': order.created_at.strftime('%H:%M') if order.created_at else '',
            'status': order.status,
            'items': items,
        })
    return JsonResponse({'success': True, 'data': data})

@csrf_exempt
@require_http_methods(["POST"])
def api_update_item_status(request):
    try:
        body   = json.loads(request.body)
        item   = OrderItem.objects.get(id=body.get('item_id'))
        item.status = body.get('status')
        item.save()

        order = item.order
        all_items = order.items.all()
        if all(i.status == 'ready' for i in all_items):
            order.status = 'ready'
        elif any(i.status in ['pending', 'cooking'] for i in all_items):
            order.status = 'cooking'
        order.save()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@csrf_exempt
@require_http_methods(["POST"])
def api_mark_order_ready(request):
    try:
        body  = json.loads(request.body)
        order = Order.objects.get(id=body.get('order_id'))
        order.status   = 'ready'
        order.ready_at = datetime.now()
        order.save()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@csrf_exempt
@require_http_methods(["POST"])
def api_take_order(request):
    try:
        body  = json.loads(request.body)
        order = Order.objects.get(id=body.get('order_id'))
        order.status = 'served'
        order.save()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@csrf_exempt
@require_http_methods(["POST"])
def api_pay_order(request):
    try:
        body   = json.loads(request.body)
        order  = Order.objects.get(id=body.get('order_id'))
        order.status         = 'paid'
        order.payment_method = body.get('payment_method')
        order.save()
        order.table.status = 'free'
        order.table.save()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@require_http_methods(["GET"])
def api_order_receipt(request, order_id):
    try:
        order = Order.objects.get(id=order_id)
        items = [{
            'name': i.dish.name, 'quantity': i.quantity,
            'price': float(i.price), 'total': float(i.price * i.quantity)
        } for i in order.items.all()]

        payment_label = {'cash': 'Наличные', 'card': 'Карта', 'qr': 'QR-код'}.get(
            order.payment_method, 'Не оплачен'
        )
        return JsonResponse({'success': True, 'data': {
            'order_id':     order.id,
            'table_number': order.table.number,
            'created_at':   order.created_at.strftime('%d.%m.%Y %H:%M') if order.created_at else '',
            'items':        items,
            'total':        float(order.total_amount),
            'payment_method': payment_label,
        }})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

# ==================== API ОТЧЁТОВ ====================

@require_http_methods(["GET"])
def api_reports(request):
    period = request.GET.get('period', 'week')
    today  = datetime.now().date()

    if period == 'day':
        start_date = end_date = today
    elif period == 'month':
        start_date = today - timedelta(days=30); end_date = today
    elif period == 'custom':
        df = request.GET.get('date_from'); dt = request.GET.get('date_to')
        start_date = datetime.strptime(df, '%Y-%m-%d').date() if df else today - timedelta(days=7)
        end_date   = datetime.strptime(dt, '%Y-%m-%d').date() if dt else today
    else:
        start_date = today - timedelta(days=7); end_date = today

    orders = Order.objects.filter(
        status='paid',
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    ).prefetch_related('items__dish').order_by('created_at')

    total_revenue = sum(float(o.total_amount) for o in orders)
    total_orders  = orders.count()
    avg_check     = total_revenue / total_orders if total_orders else 0

    dish_data = {}
    for order in orders:
        for item in order.items.all():
            n = item.dish.name
            if n not in dish_data:
                dish_data[n] = {'count': 0, 'price': float(item.price)}
            dish_data[n]['count'] += item.quantity

    popular = sorted(dish_data.items(), key=lambda x: -x[1]['count'])
    popular_dishes = [{'name': n, 'count': d['count'], 'price': d['price']} for n, d in popular[:5]]

    daily_data = []
    for i in range((end_date - start_date).days + 1):
        day = start_date + timedelta(days=i)
        day_orders = orders.filter(created_at__date=day)
        daily_data.append({
            'date':    day.strftime('%d.%m'),
            'revenue': sum(float(o.total_amount) for o in day_orders),
            'orders':  day_orders.count(),
        })

    return JsonResponse({'success': True, 'data': {
        'total_revenue': total_revenue, 'total_orders': total_orders,
        'avg_check': avg_check, 'popular_dishes': popular_dishes,
        'daily_data': daily_data,
    }})

# ==================== API ЖУРНАЛА ТО ====================

@require_http_methods(["GET"])
def api_maintenance_logs(request):
    logs = MaintenanceLog.objects.all().order_by('-date')
    data = [{
        'id': l.id, 'date': l.date.strftime('%Y-%m-%d'),
        'work_performed': l.work_performed,
        'performed_by': l.performed_by, 'signature': l.signature
    } for l in logs]
    return JsonResponse({'success': True, 'data': data})

@csrf_exempt
@require_http_methods(["POST"])
def api_maintenance_logs_add(request):
    try:
        body = json.loads(request.body)
        log  = MaintenanceLog.objects.create(
            date=body.get('date'),
            work_performed=body.get('work_performed'),
            performed_by=body.get('performed_by'),
            signature=body.get('signature', '')
        )
        return JsonResponse({'success': True, 'id': log.id})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

# ==================== РЕЗЕРВНОЕ КОПИРОВАНИЕ (PostgreSQL) ====================

@login_required(login_url="/")
def admin_backup(request):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('/')

    backup_dir = '/tmp/backups'
    os.makedirs(backup_dir, exist_ok=True)
    message = None
    error   = None

    if request.method == 'POST':
        try:
            import urllib.parse
            from django.conf import settings as djsettings
            db = djsettings.DATABASES['default']

            # Поддержка DATABASE_URL и обычного конфига
            if 'HOST' in db and db['HOST']:
                host     = db['HOST']
                port     = db.get('PORT') or '5432'
                dbname   = db['NAME']
                user     = db['USER']
                password = db.get('PASSWORD', '')
            else:
                raise Exception('Настройки БД не найдены')

            timestamp   = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = os.path.join(backup_dir, f'backup_{timestamp}.sql')

            env = os.environ.copy()
            env['PGPASSWORD'] = password

            result = subprocess.run([
                'pg_dump', '-h', host, '-p', str(port),
                '-U', user, '-d', dbname, '-f', backup_file,
                '--no-password'
            ], env=env, capture_output=True, text=True, timeout=60)

            if result.returncode == 0:
                # Убираем psql-специфичные команды (\unrestrict, \connect и др.)
                # чтобы файл можно было вставить в DBeaver без ошибок
                with open(backup_file, 'r', encoding='utf-8', errors='replace') as f:
                    lines = f.readlines()
                clean_lines = [l for l in lines if not l.startswith('\\')]
                with open(backup_file, 'w', encoding='utf-8') as f:
                    f.writelines(clean_lines)
                message = f'Резервная копия создана: backup_{timestamp}.sql'
            else:
                error = f'Ошибка pg_dump: {result.stderr[:300]}'
        except Exception as e:
            error = f'Ошибка: {str(e)}'

        return redirect('/backup/')

    # Список копий
    backups = []
    for fname in sorted(os.listdir(backup_dir), reverse=True):
        fpath = os.path.join(backup_dir, fname)
        if os.path.isfile(fpath) and (fname.endswith('.sql') or fname.endswith('.sqlite3')):
            stat = os.stat(fpath)
            backups.append({
                'name': fname,
                'date': datetime.fromtimestamp(stat.st_mtime).strftime('%d.%m.%Y %H:%M'),
                'size': round(stat.st_size / 1024, 1)
            })

    return render(request, 'backup.html', {'backups': backups, 'message': message, 'error': error})

@login_required(login_url="/")
def admin_backup_download(request, filename):
    backup_dir  = '/tmp/backups'
    safe_name   = os.path.basename(filename)
    file_path   = os.path.join(backup_dir, safe_name)
    if not os.path.exists(file_path):
        raise Http404("Файл не найден")
    with open(file_path, 'rb') as f:
        resp = HttpResponse(f.read(), content_type='application/octet-stream')
        resp['Content-Disposition'] = f'attachment; filename="{safe_name}"'
        return resp

@login_required(login_url="/")
def admin_backup_delete(request, filename):
    backup_dir = '/tmp/backups'
    safe_name  = os.path.basename(filename)
    file_path  = os.path.join(backup_dir, safe_name)
    if os.path.exists(file_path):
        os.remove(file_path)
    return redirect('/backup/')

@login_required(login_url="/")
def admin_backup_restore(request, filename):
    # Восстановление из SQL дампа в PostgreSQL
    backup_dir = '/tmp/backups'
    safe_name  = os.path.basename(filename)
    file_path  = os.path.join(backup_dir, safe_name)
    if not os.path.exists(file_path):
        raise Http404("Файл не найден")

    try:
        from django.conf import settings as djsettings
        db       = djsettings.DATABASES['default']
        host     = db['HOST']
        port     = db.get('PORT') or '5432'
        dbname   = db['NAME']
        user     = db['USER']
        password = db.get('PASSWORD', '')

        env = os.environ.copy()
        env['PGPASSWORD'] = password

        result = subprocess.run([
            'psql', '-h', host, '-p', str(port),
            '-U', user, '-d', dbname, '-f', file_path, '--no-password'
        ], env=env, capture_output=True, text=True, timeout=120)

        if result.returncode != 0:
            return HttpResponse(f'Ошибка восстановления: {result.stderr[:500]}', status=500)
    except Exception as e:
        return HttpResponse(f'Ошибка: {str(e)}', status=500)

    return redirect('/backup/')
