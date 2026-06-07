from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse, Http404, FileResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils.dateparse import parse_datetime
from datetime import datetime, timedelta
import json, os, subprocess
from decimal import Decimal
from .models import (Category, Dish, Table, Order, OrderItem,
                     MaintenanceLog, Profile, ActionLog, Receipt, LoginAttempt)

# ── ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ─────────────────────────────────────

def get_client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    return xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR', '127.0.0.1')

def log_action(request, action, description=''):
    try:
        user = request.user if request.user.is_authenticated else None
        ActionLog.objects.create(
            user=user, action=action,
            description=description, ip_address=get_client_ip(request)
        )
    except Exception:
        pass

def generate_receipt_pdf(order):
    """Генерация простого HTML-based чека (сохраняем как текстовый файл)"""
    try:
        payment_labels = {'cash': 'Наличные', 'card': 'Карта', 'qr': 'QR-код'}
        items_text = '\n'.join(
            f"  {item.dish.name} x{item.quantity} = {float(item.price * item.quantity):.2f} руб."
            for item in order.items.all()
        )
        content = f"""АИС «Общепит» — Кассовый чек
=====================================
Чек № {order.id}
Стол: {order.table.number}
Дата: {order.created_at.strftime('%d.%m.%Y %H:%M') if order.created_at else '—'}
=====================================
{items_text}
=====================================
ИТОГО: {float(order.total_amount):.2f} руб.
Оплата: {payment_labels.get(order.payment_method, '—')}
=====================================
Спасибо за визит!
"""
        os.makedirs('media/receipts', exist_ok=True)
        fname = f'receipt_{order.id}.txt'
        fpath = f'media/receipts/{fname}'
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(content)

        receipt, _ = Receipt.objects.get_or_create(order=order)
        receipt.pdf_file       = f'receipts/{fname}'
        receipt.total          = order.total_amount
        receipt.payment_method = order.payment_method or ''
        receipt.save()
        return receipt
    except Exception as e:
        print(f'Receipt error: {e}')
        return None

# ── СТРАНИЦЫ ────────────────────────────────────────────────────

def landing(request):         return render(request, 'landing.html')
def admin_panel(request):     return render(request, 'admin_panel.html')
def waiter_hall(request):     return render(request, 'waiter_hall.html')
def kitchen_view(request):    return render(request, 'kitchen.html')
def reports_view(request):    return render(request, 'reports.html')
def help_page(request):       return render(request, 'help.html')
def docs_page(request):       return render(request, 'docs.html')
def maintenance_log_page(request): return render(request, 'maintenance_log.html')

# ── АВТОРИЗАЦИЯ ─────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(["POST"])
def api_login(request):
    try:
        body     = json.loads(request.body)
        username = body.get('username', '').strip()
        password = body.get('password', '').strip()
        ip       = get_client_ip(request)

        try:
            attempt = LoginAttempt.objects.get(username=username, ip_address=ip)
            if attempt.blocked_until and datetime.now() < attempt.blocked_until:
                remaining = int((attempt.blocked_until - datetime.now()).total_seconds() / 60) + 1
                return JsonResponse({
                    'success': False,
                    'error': f'Слишком много попыток. Попробуйте через {remaining} мин.',
                    'blocked': True
                })
        except LoginAttempt.DoesNotExist:
            attempt = None

        from django.contrib.auth import authenticate, login
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            if attempt:
                attempt.attempts = 0
                attempt.blocked_until = None
                attempt.save()
            role = 'staff'
            if user.is_superuser:
                role = 'admin'
            elif hasattr(user, 'profile') and user.profile.role:
                role = user.profile.role
            log_action(request, 'login', f'Вход: {username} (роль: {role})')
            return JsonResponse({'success': True, 'role': role, 'username': user.username})
        else:
            MAX_ATTEMPTS = 5
            BLOCK_MINUTES = 15
            if attempt:
                attempt.attempts += 1
                if attempt.attempts >= MAX_ATTEMPTS:
                    attempt.blocked_until = datetime.now() + timedelta(minutes=BLOCK_MINUTES)
                attempt.save()
            else:
                LoginAttempt.objects.create(username=username, ip_address=ip, attempts=1)
            remaining_attempts = MAX_ATTEMPTS - (attempt.attempts if attempt else 1)
            msg = 'Неверный логин или пароль.'
            if remaining_attempts > 0:
                msg += f' Осталось попыток: {remaining_attempts}'
            return JsonResponse({'success': False, 'error': msg})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

# ── ДАННЫЕ ──────────────────────────────────────────────────────

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
    try:
        tables = Table.objects.all().order_by('number')
        data = [{'id': t.id, 'number': t.number, 'seats': t.seats, 'status': t.status} for t in tables]
        return JsonResponse({'success': True, 'data': data})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@require_http_methods(["GET"])
def api_staff(request):
    from django.contrib.auth.models import User
    count = User.objects.filter(is_active=True).count()
    return JsonResponse({'success': True, 'count': count})

# ── ЗАКАЗЫ ──────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(["POST"])
def api_create_order(request):
    try:
        body        = json.loads(request.body)
        table_id    = body.get('table_id')
        items       = body.get('items', [])
        guest_count = body.get('guest_count', 1)
        client_time = body.get('client_time')

        table = Table.objects.get(id=table_id)

        if client_time:
            parsed = parse_datetime(client_time)
            if parsed is not None:
                current_time = parsed.astimezone().replace(tzinfo=None) if parsed.tzinfo else parsed
            else:
                current_time = datetime.now()
        else:
            current_time = datetime.now()

        order = Order(table=table, status='new', guest_count=guest_count, created_at=current_time)
        order.save()

        total = Decimal('0')
        for item in items:
            dish = Dish.objects.get(id=item['dish_id'])
            OrderItem.objects.create(
                order=order, dish=dish,
                quantity=item['quantity'], price=dish.price, status='pending'
            )
            total += dish.price * item['quantity']

        order.total_amount = total
        order.save()
        table.status = 'occupied'
        table.save()

        log_action(request, 'create_order',
                   f'Заказ #{order.id}, стол {table.number}, сумма {float(total):.2f} руб.')
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
        items = [{'id': i.id, 'dish_name': i.dish.name, 'quantity': i.quantity, 'status': i.status}
                 for i in order.items.all()]
        waiter_name = 'Не указан'
        if order.waiter:
            try:
                waiter_name = order.waiter.first_name or order.waiter.username
            except Exception:
                waiter_name = order.waiter.username
        data.append({
            'id': order.id,
            'table_number': order.table.number,
            'created_at': (order.created_at + timedelta(hours=0)).strftime('%H:%M') if order.created_at else '',
            'status': order.status,
            'items': items,
            'waiter_name': waiter_name,
        })
    return JsonResponse({'success': True, 'data': data})

@csrf_exempt
@require_http_methods(["POST"])
def api_update_item_status(request):
    try:
        body  = json.loads(request.body)
        item  = OrderItem.objects.get(id=body.get('item_id'))
        item.status = body.get('status')
        item.save()
        order = item.order
        all_items = order.items.all()
        if all(i.status == 'ready' for i in all_items):
            order.status = 'ready'
        elif any(i.status in ['pending', 'cooking'] for i in all_items):
            order.status = 'cooking'
        order.save()
        log_action(request, 'update_item',
                   f'Блюдо {item.dish.name} → {item.status}, заказ #{order.id}')
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
        log_action(request, 'mark_ready', f'Заказ #{order.id} готов')
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@csrf_exempt
@require_http_methods(["POST"])
def api_take_order(request):
    try:
        body  = json.loads(request.body)
        order = Order.objects.get(id=body.get('order_id'))
        order.status = 'ready'
        order.save()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

# ========== ФУНКЦИЯ ОПЛАТЫ (ТОЛЬКО ОДНА, ИСПРАВЛЕННАЯ) ==========
@csrf_exempt
def api_pay_fixed(request):
    """Оплата заказа – принимает POST: {order_id, payment_method}"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Only POST allowed'}, status=405)
    try:
        data = json.loads(request.body)
        order_id = data.get('order_id')
        payment_method = data.get('payment_method')
        if not order_id:
            return JsonResponse({'success': False, 'error': 'Не указан ID заказа'})

        allowed_methods = ['cash', 'card', 'qr']
        if payment_method not in allowed_methods:
            return JsonResponse({'success': False, 'error': 'Неверный способ оплаты'}, status=400)

        order = Order.objects.get(id=order_id)
        if order.status == 'paid':
            return JsonResponse({'success': False, 'error': 'Заказ уже оплачен'})

        order.status = 'paid'
        order.payment_method = payment_method
        order.save()
        order.table.status = 'free'
        order.table.save()

        log_action(request, 'pay_order', f'Заказ #{order.id}, {order.payment_method}')
        try:
            generate_receipt_pdf(order)
        except:
            pass

        return JsonResponse({'success': True, 'order_id': order.id})

    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Заказ не найден'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@require_http_methods(["GET"])
def api_order_receipt(request, order_id):
    try:
        order = Order.objects.get(id=order_id)
        items = [{'name': i.dish.name, 'quantity': i.quantity,
                  'price': float(i.price), 'total': float(i.price * i.quantity)}
                 for i in order.items.all()]
        payment_label = {'cash': 'Наличные', 'card': 'Карта', 'qr': 'QR-код'}.get(
            order.payment_method, 'Не оплачен')
        receipt_url = None
        try:
            receipt_url = f'/receipts/{order.receipt.id}/download/'
        except Exception:
            pass
        return JsonResponse({'success': True, 'data': {
            'order_id':       order.id,
            'table_number':   order.table.number,
            'created_at':     order.created_at.strftime('%d.%m.%Y %H:%M') if order.created_at else '',
            'items':          items,
            'total':          float(order.total_amount),
            'payment_method': payment_label,
            'receipt_url':    receipt_url,
        }})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@require_http_methods(["GET"])
def download_receipt(request, receipt_id):
    try:
        receipt = Receipt.objects.get(id=receipt_id)
        if receipt.pdf_file:
            fpath = os.path.join('media', receipt.pdf_file.name)
            if os.path.exists(fpath):
                return FileResponse(open(fpath, 'rb'), as_attachment=True,
                                    filename=f'receipt_{receipt.order.id}.txt')
        raise Http404("Чек не найден")
    except Receipt.DoesNotExist:
        raise Http404("Чек не найден")

# ── ОТЧЁТЫ ──────────────────────────────────────────────────────

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

    popular_dishes = [{'name': n, 'count': d['count'], 'price': d['price']}
                      for n, d in sorted(dish_data.items(), key=lambda x: -x[1]['count'])[:5]]

    daily_data = []
    for i in range((end_date - start_date).days + 1):
        day = start_date + timedelta(days=i)
        day_orders = orders.filter(created_at__date=day)
        daily_data.append({
            'date':    day.strftime('%d.%m'),
            'revenue': sum(float(o.total_amount) for o in day_orders),
            'orders':  day_orders.count(),
        })

    log_action(request, 'view_report', f'Период: {period} ({start_date} – {end_date})')
    return JsonResponse({'success': True, 'data': {
        'total_revenue': total_revenue, 'total_orders': total_orders,
        'avg_check': avg_check, 'popular_dishes': popular_dishes,
        'daily_data': daily_data,
    }})

# ── ЖУРНАЛ ТО ───────────────────────────────────────────────────

@require_http_methods(["GET"])
def api_maintenance_logs(request):
    logs = MaintenanceLog.objects.all().order_by('-date')
    data = [{'id': l.id, 'date': l.date.strftime('%Y-%m-%d'),
             'work_performed': l.work_performed,
             'performed_by': l.performed_by, 'signature': l.signature}
            for l in logs]
    return JsonResponse({'success': True, 'data': data})

@csrf_exempt
@require_http_methods(["POST"])
def api_maintenance_logs_add(request):
    try:
        body = json.loads(request.body)
        log  = MaintenanceLog.objects.create(
            date=body.get('date'), work_performed=body.get('work_performed'),
            performed_by=body.get('performed_by'), signature=body.get('signature', '')
        )
        return JsonResponse({'success': True, 'id': log.id})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

# ── ЖУРНАЛ ДЕЙСТВИЙ (API) ───────────────────────────────────────

@require_http_methods(["GET"])
def api_action_logs(request):
    logs = ActionLog.objects.select_related('user').order_by('-timestamp')[:50]
    data = [{
        'id': l.id,
        'user': l.user.username if l.user else 'Аноним',
        'action': l.get_action_display(),
        'description': l.description,
        'ip': l.ip_address or '',
        'timestamp': l.timestamp.strftime('%d.%m.%Y %H:%M:%S'),
    } for l in logs]
    return JsonResponse({'success': True, 'data': data})

# ── АВТО-БЭКАП ENDPOINT ─────────────────────────────────────────

@require_http_methods(["GET", "POST"])
def auto_backup_trigger(request):
    secret = os.environ.get('BACKUP_SECRET_KEY', 'obshepit-backup-2026')
    if request.GET.get('key') != secret:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)

    try:
        from django.conf import settings as djsettings
        db = djsettings.DATABASES['default']
        if 'HOST' not in db or not db.get('HOST'):
            return JsonResponse({'success': False, 'error': 'PostgreSQL не настроен'})

        backup_dir = '/tmp/backups'
        os.makedirs(backup_dir, exist_ok=True)
        cutoff = datetime.now() - timedelta(days=30)
        for fname in os.listdir(backup_dir):
            fpath = os.path.join(backup_dir, fname)
            if os.path.isfile(fpath):
                mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
                if mtime < cutoff:
                    os.remove(fpath)

        timestamp   = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(backup_dir, f'auto_backup_{timestamp}.sql')
        env         = os.environ.copy()
        env['PGPASSWORD'] = db.get('PASSWORD', '')

        result = subprocess.run([
            'pg_dump', '-h', db['HOST'], '-p', str(db.get('PORT') or '5432'),
            '-U', db['USER'], '-d', db['NAME'], '-f', backup_file, '--no-password'
        ], env=env, capture_output=True, text=True, timeout=60)

        if result.returncode == 0:
            with open(backup_file, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
            with open(backup_file, 'w', encoding='utf-8') as f:
                f.writelines(l for l in lines if not l.startswith('\\'))
            log_action(request, 'create_backup', f'Авто-бэкап: auto_backup_{timestamp}.sql')
            return JsonResponse({'success': True, 'file': f'auto_backup_{timestamp}.sql'})
        else:
            return JsonResponse({'success': False, 'error': result.stderr[:300]})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

# ── РАЗБЛОКИРОВКА И СМЕНА ПАРОЛЯ ────────────────────────────────

@csrf_exempt
@require_http_methods(["POST"])
def api_unblock_user(request):
    try:
        if not request.user.is_authenticated or not request.user.is_superuser:
            return JsonResponse({'success': False, 'error': 'Нет прав'}, status=403)
        body    = json.loads(request.body)
        username = body.get('username', '').strip()
        LoginAttempt.objects.filter(username=username).update(attempts=0, blocked_until=None)
        log_action(request, 'other', f'Разблокирован пользователь: {username}')
        return JsonResponse({'success': True, 'message': f'Пользователь {username} разблокирован'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@csrf_exempt
@require_http_methods(["POST"])
def api_change_password(request):
    try:
        body     = json.loads(request.body)
        username = body.get('username', '').strip()
        old_pass = body.get('old_password', '').strip()
        new_pass = body.get('new_password', '').strip()

        if len(new_pass) < 6:
            return JsonResponse({'success': False, 'error': 'Пароль должен быть не менее 6 символов'})

        from django.contrib.auth import authenticate
        user = authenticate(request, username=username, password=old_pass)
        if not user:
            return JsonResponse({'success': False, 'error': 'Неверный текущий пароль'})

        user.set_password(new_pass)
        user.save()
        from django.contrib.auth import update_session_auth_hash
        update_session_auth_hash(request, user)
        log_action(request, 'other', f'Смена пароля: {username}')
        return JsonResponse({'success': True, 'message': 'Пароль успешно изменён'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@require_http_methods(["GET"])
def api_blocked_users(request):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Нет прав'}, status=403)
    from datetime import datetime
    now = datetime.now()
    blocked = LoginAttempt.objects.filter(blocked_until__gt=now)
    data = [{
        'username': b.username,
        'attempts': b.attempts,
        'blocked_until': b.blocked_until.strftime('%H:%M:%S') if b.blocked_until else '',
        'ip': b.ip_address or '',
    } for b in blocked]
    return JsonResponse({'success': True, 'data': data})

# ── РЕЗЕРВНОЕ КОПИРОВАНИЕ (VIEWS) ───────────────────────────────

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
            from django.conf import settings as djsettings
            db = djsettings.DATABASES['default']
            if 'HOST' not in db or not db.get('HOST'):
                raise Exception('Настройки БД не найдены')
            timestamp   = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = os.path.join(backup_dir, f'backup_{timestamp}.sql')
            env = os.environ.copy()
            env['PGPASSWORD'] = db.get('PASSWORD', '')
            result = subprocess.run([
                'pg_dump', '-h', db['HOST'], '-p', str(db.get('PORT') or '5432'),
                '-U', db['USER'], '-d', db['NAME'], '-f', backup_file, '--no-password'
            ], env=env, capture_output=True, text=True, timeout=60)
            if result.returncode == 0:
                with open(backup_file, 'r', encoding='utf-8', errors='replace') as f:
                    lines = f.readlines()
                with open(backup_file, 'w', encoding='utf-8') as f:
                    f.writelines(l for l in lines if not l.startswith('\\'))
                log_action(request, 'create_backup', f'backup_{timestamp}.sql')
                message = f'Резервная копия создана: backup_{timestamp}.sql'
            else:
                error = f'Ошибка pg_dump: {result.stderr[:300]}'
        except Exception as e:
            error = f'Ошибка: {str(e)}'
        return redirect('/backup/')
    backups = []
    for fname in sorted(os.listdir(backup_dir), reverse=True):
        fpath = os.path.join(backup_dir, fname)
        if os.path.isfile(fpath) and fname.endswith('.sql'):
            stat = os.stat(fpath)
            backups.append({
                'name': fname,
                'date': datetime.fromtimestamp(stat.st_mtime).strftime('%d.%m.%Y %H:%M'),
                'size': round(stat.st_size / 1024, 1)
            })
    return render(request, 'backup.html', {'backups': backups, 'message': message, 'error': error})

@login_required(login_url="/")
def admin_backup_download(request, filename):
    backup_dir = '/tmp/backups'
    safe_name  = os.path.basename(filename)
    file_path  = os.path.join(backup_dir, safe_name)
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
    backup_dir = '/tmp/backups'
    safe_name  = os.path.basename(filename)
    file_path  = os.path.join(backup_dir, safe_name)
    if not os.path.exists(file_path):
        raise Http404("Файл не найден")
    try:
        from django.conf import settings as djsettings
        db  = djsettings.DATABASES['default']
        env = os.environ.copy()
        env['PGPASSWORD'] = db.get('PASSWORD', '')
        result = subprocess.run([
            'psql', '-h', db['HOST'], '-p', str(db.get('PORT') or '5432'),
            '-U', db['USER'], '-d', db['NAME'], '-f', file_path, '--no-password'
        ], env=env, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            return HttpResponse(f'Ошибка: {result.stderr[:500]}', status=500)
    except Exception as e:
        return HttpResponse(f'Ошибка: {str(e)}', status=500)
    return redirect('/backup/')
