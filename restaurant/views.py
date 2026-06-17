"""
restaurant/views.py
Все функции-обработчики (контроллеры) АИС «Общепит».

Здесь описаны:
- страницы для рендеринга HTML (landing, waiter_hall, kitchen, reports, admin_panel, документация)
- API-эндпоинты, возвращающие JSON (авторизация, данные меню, заказы, отчёты, журналы)
- вспомогательные функции (логгирование, генерация чеков, загрузка бэкапов в GitHub)
"""

import os
import base64
import subprocess
from datetime import datetime, timedelta
from decimal import Decimal
import json
from github import Github
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse, Http404, FileResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, update_session_auth_hash
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from django.conf import settings

from .models import (
    Category, Dish, Table, Order, OrderItem, MaintenanceLog,
    Profile, ActionLog, Receipt, LoginAttempt
)


# ================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ================================================================

def get_client_ip(request):
    """Получает реальный IP-адрес клиента, даже за прокси."""
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '127.0.0.1')


def log_action(request, action, description=''):
    """
    Записывает действие пользователя в журнал (ActionLog).
    Используется для аудита.
    """
    try:
        user = request.user if request.user.is_authenticated else None
        ActionLog.objects.create(
            user=user,
            action=action,
            description=description,
            ip_address=get_client_ip(request)
        )
    except Exception:
        pass


def generate_receipt_pdf(order):
    """
    Генерирует текстовый файл чека и сохраняет его в модели Receipt.
    В реальном проекте здесь может быть генерация PDF через ReportLab.
    """
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
        receipt.pdf_file = f'receipts/{fname}'
        receipt.total = order.total_amount
        receipt.payment_method = order.payment_method or ''
        receipt.save()
        return receipt
    except Exception as e:
        print(f'Receipt error: {e}')
        return None


def upload_backup_to_github(file_path, filename):
    """
    Загружает файл бэкапа в приватный репозиторий на GitHub.
    Использует переменные окружения GITHUB_TOKEN и GITHUB_BACKUP_REPO.
    """
    token = os.environ.get('GITHUB_TOKEN')
    repo_name = os.environ.get('GITHUB_BACKUP_REPO')
    if not token or not repo_name:
        print("GitHub credentials not set, backup NOT uploaded")
        return False

    g = Github(token)
    repo = g.get_repo(repo_name)
    remote_path = f"backups/{filename}"

    with open(file_path, 'rb') as f:
        content = base64.b64encode(f.read()).decode()

    try:
        repo.create_file(remote_path, f"Auto backup {filename}", content, branch="main")
        print(f"✅ Uploaded {filename} to GitHub")
    except Exception:
        try:
            contents = repo.get_contents(remote_path, ref="main")
            repo.update_file(contents.path, f"Update backup {filename}", content, contents.sha, branch="main")
            print(f"🔄 Updated {filename} on GitHub")
        except Exception as e2:
            print(f"❌ Failed to upload to GitHub: {e2}")
            return False
    return True


# ================================================================
# СТРАНИЦЫ (HTML)
# ================================================================

def landing(request):
    """Стартовая страница входа (только для сотрудников)."""
    return render(request, 'landing.html')


def admin_panel(request):
    """Панель администратора (кастомная страница с ссылками на разделы)."""
    return render(request, 'admin_panel.html')


def waiter_hall(request):
    """Зал ресторана — интерфейс официанта."""
    return render(request, 'waiter_hall.html')


def kitchen_view(request):
    """Кухня — интерфейс повара."""
    return render(request, 'kitchen.html')


def reports_view(request):
    """Страница отчётов (только для администратора)."""
    return render(request, 'reports.html')


def help_page(request):
    """Руководство пользователя."""
    return render(request, 'help.html')


def docs_page(request):
    """Регламенты (техобслуживание, бэкап, восстановление)."""
    return render(request, 'docs.html')


def maintenance_log_page(request):
    """Страница журнала технического обслуживания."""
    return render(request, 'maintenance_log.html')


# ================================================================
# API АВТОРИЗАЦИИ
# ================================================================

@csrf_exempt
@require_http_methods(["POST"])
def api_login(request):
    """
    Вход пользователя по логину/паролю.
    Учитывает блокировку после 5 неудачных попыток.
    """
    try:
        body = json.loads(request.body)
        username = body.get('username', '').strip()
        password = body.get('password', '').strip()
        ip = get_client_ip(request)

        # Проверяем, есть ли запись о попытках для этого пользователя с этого IP
        attempt, created = LoginAttempt.objects.get_or_create(
            username=username,
            ip_address=ip,
            defaults={'attempts': 0, 'blocked_until': None}
        )

        # Если заблокирован — сообщаем остаток времени
        now = timezone.now()
        if attempt.blocked_until and attempt.blocked_until > now:
            remaining = int((attempt.blocked_until - now).total_seconds() / 60) + 1
            return JsonResponse({
                'success': False,
                'error': f'Слишком много попыток. Попробуйте через {remaining} мин.',
                'blocked': True
            })

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            # Сбрасываем счётчик при успешном входе
            attempt.attempts = 0
            attempt.blocked_until = None
            attempt.save()

            # Определяем роль пользователя
            role = 'staff'
            if user.is_superuser:
                role = 'admin'
            elif hasattr(user, 'profile') and user.profile.role:
                role = user.profile.role

            log_action(request, 'login', f'Вход: {username} (роль: {role})')
            return JsonResponse({'success': True, 'role': role, 'username': user.username})
        else:
            # Неудачная попытка — увеличиваем счётчик
            attempt.attempts += 1
            if attempt.attempts >= 5:
                attempt.blocked_until = now + timedelta(minutes=15)
            attempt.save()
            remaining_attempts = 5 - attempt.attempts
            msg = 'Неверный логин или пароль.'
            if remaining_attempts > 0:
                msg += f' Осталось попыток: {remaining_attempts}'
            return JsonResponse({'success': False, 'error': msg})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# ================================================================
# API ДАННЫЕ (меню, столы)
# ================================================================

@require_http_methods(["GET"])
def api_dishes(request):
    """Возвращает список доступных блюд с их категориями."""
    dishes = Dish.objects.filter(is_available=True).select_related('category')
    data = [{
        'id': d.id,
        'name': d.name,
        'description': d.description,
        'price': float(d.price),
        'category': d.category.name,
        'category_id': d.category.id,
    } for d in dishes]
    return JsonResponse({'success': True, 'data': data})


@require_http_methods(["GET"])
def api_categories(request):
    """Возвращает список всех категорий меню."""
    cats = Category.objects.all().order_by('order')
    return JsonResponse({'success': True, 'data': [{'id': c.id, 'name': c.name, 'icon': c.icon} for c in cats]})


@require_http_methods(["GET"])
def api_tables(request):
    """Возвращает список столов с их статусами."""
    try:
        tables = Table.objects.all().order_by('number')
        data = [{'id': t.id, 'number': t.number, 'seats': t.seats, 'status': t.status} for t in tables]
        return JsonResponse({'success': True, 'data': data})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["GET"])
def api_staff(request):
    """Возвращает количество активных сотрудников."""
    from django.contrib.auth.models import User
    count = User.objects.filter(is_active=True).count()
    return JsonResponse({'success': True, 'count': count})


# ================================================================
# API ЗАКАЗЫ
# ================================================================

@csrf_exempt
@require_http_methods(["POST"])
def api_create_order(request):
    """
    Создаёт новый заказ: проверяет стол, добавляет позиции, обновляет статус стола.
    """
    try:
        body = json.loads(request.body)
        table_id = body.get('table_id')
        items = body.get('items', [])
        guest_count = body.get('guest_count', 1)
        client_time = body.get('client_time')

        table = Table.objects.get(id=table_id)

        # Определяем время создания заказа (приоритет: переданное клиентом или текущее)
        if client_time:
            parsed = parse_datetime(client_time)
            current_time = parsed if parsed else timezone.now()
        else:
            current_time = timezone.now()

        order = Order.objects.create(
            table=table,
            status='new',
            guest_count=guest_count,
            created_at=current_time,
        )
        if request.user.is_authenticated:
            order.waiter = request.user
        order.save()

        total = Decimal('0')
        for item in items:
            dish = Dish.objects.get(id=item['dish_id'])
            OrderItem.objects.create(
                order=order,
                dish=dish,
                quantity=item['quantity'],
                price=dish.price,
                status='pending'
            )
            total += dish.price * item['quantity']

        order.total_amount = total
        order.save()
        table.status = 'occupied'
        table.save()

        log_action(request, 'create_order', f'Заказ #{order.id}, стол {table.number}, сумма {float(total):.2f} руб.')
        return JsonResponse({'success': True, 'order_id': order.id, 'total': float(total)})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@require_http_methods(["GET"])
def api_active_orders(request):
    """
    Возвращает активные заказы (new, cooking, ready) с их позициями и статусами блюд.
    Время отображается в часовом поясе Москвы (МСК+2).
    """
    orders = Order.objects.filter(
        status__in=['new', 'cooking', 'ready']
    ).select_related('table').prefetch_related('items__dish')

    data = []
    for order in orders:
        # Используем timezone.localtime, чтобы привести время к текущему часовому поясу (МСК)
        created_time = timezone.localtime(order.created_at).strftime('%H:%M') if order.created_at else ''

        items = []
        for item in order.items.all():
            status_choices = dict(OrderItem.STATUS_CHOICES)
            items.append({
                'id': item.id,
                'dish_name': item.dish.name,
                'quantity': item.quantity,
                'status': item.status,
                'status_display': status_choices.get(item.status, item.status),
            })

        data.append({
            'id': order.id,
            'table_number': order.table.number,
            'created_at': created_time,
            'status': order.status,
            'status_display': order.get_status_display(),
            'items': items,
        })

    return JsonResponse({'success': True, 'data': data})


@csrf_exempt
@require_http_methods(["POST"])
def api_update_item_status(request):
    """Обновляет статус конкретной позиции заказа (pending → cooking → ready)."""
    try:
        body = json.loads(request.body)
        item = OrderItem.objects.get(id=body.get('item_id'))
        new_status = body.get('status')
        item.status = new_status
        item.save()

        # Обновляем статус всего заказа, если все позиции готовы
        order = item.order
        all_items = order.items.all()
        if all(i.status == 'ready' for i in all_items):
            order.status = 'ready'
        elif any(i.status in ['pending', 'cooking'] for i in all_items):
            order.status = 'cooking'
        order.save()

        log_action(request, 'update_item', f'Блюдо {item.dish.name} → {new_status}, заказ #{order.id}')
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def api_mark_order_ready(request):
    """Отмечает заказ как полностью готовый (кнопка «Заказ готов» на кухне)."""
    try:
        body = json.loads(request.body)
        order = Order.objects.get(id=body.get('order_id'))
        order.status = 'ready'
        order.ready_at = timezone.now()
        order.save()
        log_action(request, 'mark_ready', f'Заказ #{order.id} готов')
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def api_take_order(request):
    """Официант забирает готовый заказ (переводит в статус 'served')."""
    try:
        body = json.loads(request.body)
        order = Order.objects.get(id=body.get('order_id'))
        order.status = 'served'
        order.save()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def api_pay_order(request):
    """Оплата заказа: меняет статус, сохраняет способ оплаты, освобождает стол."""
    try:
        data = json.loads(request.body)
        order = Order.objects.get(id=data.get('order_id'))
        if order.status == 'paid':
            return JsonResponse({'success': False, 'error': 'Заказ уже оплачен'})
        order.status = 'paid'
        order.payment_method = data.get('payment_method')
        order.save()
        order.table.status = 'free'
        order.table.save()

        # Генерируем чек
        try:
            generate_receipt_pdf(order)
        except Exception:
            pass

        log_action(request, 'pay_order', f'Заказ #{order.id}, {float(order.total_amount):.2f} руб., {order.payment_method}')
        return JsonResponse({'success': True})
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Заказ не найден'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@require_http_methods(["GET"])
def api_order_receipt(request, order_id):
    """Возвращает данные для отображения чека."""
    try:
        order = Order.objects.get(id=order_id)
        items = [{
            'name': i.dish.name,
            'quantity': i.quantity,
            'price': float(i.price),
            'total': float(i.price * i.quantity)
        } for i in order.items.all()]

        payment_label = dict(Order.PAYMENT_CHOICES).get(order.payment_method, 'Не оплачен')
        receipt_url = None
        try:
            receipt_url = f'/receipts/{order.receipt.id}/download/'
        except Exception:
            pass

        return JsonResponse({'success': True, 'data': {
            'order_id': order.id,
            'table_number': order.table.number,
            'created_at': timezone.localtime(order.created_at).strftime('%d.%m.%Y %H:%M') if order.created_at else '',
            'items': items,
            'total': float(order.total_amount),
            'payment_method': payment_label,
            'receipt_url': receipt_url,
        }})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


# ================================================================
# API ОТЧЁТЫ
# ================================================================

@require_http_methods(["GET"])
def api_reports(request):
    """
    Возвращает статистику по продажам за выбранный период (day, week, month, custom).
    """
    period = request.GET.get('period', 'week')
    today = timezone.now().date()

    if period == 'day':
        start_date = end_date = today
    elif period == 'month':
        start_date = today - timedelta(days=30)
        end_date = today
    elif period == 'custom':
        df = request.GET.get('date_from')
        dt = request.GET.get('date_to')
        start_date = datetime.strptime(df, '%Y-%m-%d').date() if df else today - timedelta(days=7)
        end_date = datetime.strptime(dt, '%Y-%m-%d').date() if dt else today
    else:  # week by default
        start_date = today - timedelta(days=7)
        end_date = today

    orders = Order.objects.filter(
        status='paid',
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    ).prefetch_related('items__dish').order_by('created_at')

    total_revenue = sum(float(o.total_amount) for o in orders)
    total_orders = orders.count()
    avg_check = total_revenue / total_orders if total_orders else 0

    # Подсчёт продаж по блюдам
    dish_data = {}
    for order in orders:
        for item in order.items.all():
            name = item.dish.name
            if name not in dish_data:
                dish_data[name] = {'count': 0, 'price': float(item.price)}
            dish_data[name]['count'] += item.quantity

    popular_dishes = [
        {'name': n, 'count': d['count'], 'price': d['price']}
        for n, d in sorted(dish_data.items(), key=lambda x: -x[1]['count'])[:5]
    ]

    # Данные для графика по дням
    daily_data = []
    for i in range((end_date - start_date).days + 1):
        day = start_date + timedelta(days=i)
        day_orders = orders.filter(created_at__date=day)
        daily_data.append({
            'date': day.strftime('%d.%m'),
            'revenue': sum(float(o.total_amount) for o in day_orders),
            'orders': day_orders.count(),
        })

    log_action(request, 'view_report', f'Период: {period} ({start_date} – {end_date})')
    return JsonResponse({'success': True, 'data': {
        'total_revenue': total_revenue,
        'total_orders': total_orders,
        'avg_check': avg_check,
        'popular_dishes': popular_dishes,
        'daily_data': daily_data,
    }})


# ================================================================
# API ЖУРНАЛ ТО
# ================================================================

@require_http_methods(["GET"])
def api_maintenance_logs(request):
    """Возвращает записи журнала технического обслуживания."""
    logs = MaintenanceLog.objects.all().order_by('-date')
    data = [{
        'id': l.id,
        'date': l.date.strftime('%Y-%m-%d'),
        'work_performed': l.work_performed,
        'performed_by': l.performed_by,
        'signature': l.signature or ''
    } for l in logs]
    return JsonResponse({'success': True, 'data': data})


@csrf_exempt
@require_http_methods(["POST"])
def api_maintenance_logs_add(request):
    """Добавляет новую запись в журнал ТО."""
    try:
        body = json.loads(request.body)
        log = MaintenanceLog.objects.create(
            date=body.get('date'),
            work_performed=body.get('work_performed'),
            performed_by=body.get('performed_by'),
            signature=body.get('signature', '')
        )
        return JsonResponse({'success': True, 'id': log.id})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# ================================================================
# API УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ
# ================================================================

@csrf_exempt
@require_http_methods(["POST"])
def api_unblock_user(request):
    """Разблокирует пользователя (админ)."""
    try:
        if not request.user.is_authenticated or not request.user.is_superuser:
            return JsonResponse({'success': False, 'error': 'Нет прав'}, status=403)
        body = json.loads(request.body)
        username = body.get('username', '').strip()
        LoginAttempt.objects.filter(username=username).update(attempts=0, blocked_until=None)
        log_action(request, 'other', f'Разблокирован пользователь: {username}')
        return JsonResponse({'success': True, 'message': f'Пользователь {username} разблокирован'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
@require_http_methods(["POST"])
def api_change_password(request):
    """Меняет пароль текущего пользователя (требуется старый пароль)."""
    try:
        body = json.loads(request.body)
        username = body.get('username', '').strip()
        old_pass = body.get('old_password', '').strip()
        new_pass = body.get('new_password', '').strip()

        if len(new_pass) < 6:
            return JsonResponse({'success': False, 'error': 'Пароль должен быть не менее 6 символов'})

        user = authenticate(request, username=username, password=old_pass)
        if not user:
            return JsonResponse({'success': False, 'error': 'Неверный текущий пароль'})

        user.set_password(new_pass)
        user.save()
        update_session_auth_hash(request, user)
        log_action(request, 'other', f'Смена пароля: {username}')
        return JsonResponse({'success': True, 'message': 'Пароль успешно изменён'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@require_http_methods(["GET"])
def api_blocked_users(request):
    """Возвращает список заблокированных пользователей (для администратора)."""
    if not request.user.is_authenticated or not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Нет прав'}, status=403)
    now = timezone.now()
    blocked = LoginAttempt.objects.filter(blocked_until__gt=now)
    data = [{
        'username': b.username,
        'attempts': b.attempts,
        'blocked_until': b.blocked_until.strftime('%H:%M:%S') if b.blocked_until else '',
        'ip': b.ip_address or '',
    } for b in blocked]
    return JsonResponse({'success': True, 'data': data})


# ================================================================
# API ЖУРНАЛ ДЕЙСТВИЙ (АУДИТ)
# ================================================================

@require_http_methods(["GET"])
def api_action_logs(request):
    """Возвращает последние 50 записей журнала действий."""
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


# ================================================================
# API СКАЧИВАНИЕ ЧЕКА
# ================================================================

@require_http_methods(["GET"])
def download_receipt(request, receipt_id):
    """Скачивает файл чека (текстовый)."""
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


# ================================================================
# АВТО-БЭКАП (триггер от cron-job.org)
# ================================================================

@require_http_methods(["GET", "POST"])
def auto_backup_trigger(request):
    """
    Создаёт резервную копию БД (pg_dump) и загружает её в GitHub.
    Вызывается по расписанию через cron-job.org.
    """
    secret = os.environ.get('BACKUP_SECRET_KEY', 'obshepit-backup-2026')
    if request.GET.get('key') != secret:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)

    backup_dir = '/tmp/backups'
    os.makedirs(backup_dir, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = os.path.join(backup_dir, f'auto_backup_{timestamp}.sql')

    db = settings.DATABASES['default']
    env = os.environ.copy()
    env['PGPASSWORD'] = db.get('PASSWORD', '')

    try:
        result = subprocess.run([
            'pg_dump', '-h', db['HOST'], '-p', str(db.get('PORT', 5432)),
            '-U', db['USER'], '-d', db['NAME'], '-f', backup_file, '--no-password'
        ], env=env, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            return JsonResponse({'success': False, 'error': result.stderr[:300]})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

    # Загружаем в GitHub
    upload_backup_to_github(backup_file, f'auto_backup_{timestamp}.sql')

    # Удаляем локальные файлы старше 30 дней
    cutoff = timezone.now() - timedelta(days=30)
    for fname in os.listdir(backup_dir):
        fpath = os.path.join(backup_dir, fname)
        if os.path.isfile(fpath):
            mtime = datetime.fromtimestamp(os.path.getmtime(fpath)).replace(tzinfo=timezone.utc)
            if mtime < cutoff:
                os.remove(fpath)

    log_action(request, 'create_backup', f'Авто-бэкап: auto_backup_{timestamp}.sql')
    return JsonResponse({'success': True, 'file': f'auto_backup_{timestamp}.sql'})


# ================================================================
# ЗАПАСНОЙ ЭНДПОИНТ ОПЛАТЫ (упрощённая версия)
# ================================================================

@csrf_exempt
def api_pay_fixed(request):
    """Упрощённая оплата (используется как fallback)."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Only POST allowed'}, status=405)
    try:
        data = json.loads(request.body)
        order = Order.objects.get(id=data.get('order_id'))
        if order.status == 'paid':
            return JsonResponse({'success': False, 'error': 'Заказ уже оплачен'})
        order.status = 'paid'
        order.payment_method = data.get('payment_method')
        order.save()
        order.table.status = 'free'
        order.table.save()
        try:
            generate_receipt_pdf(order)
        except Exception:
            pass
        return JsonResponse({'success': True, 'order_id': order.id})
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Заказ не найден'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
