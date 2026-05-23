from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from datetime import datetime, timedelta, timezone as dt_timezone
import json
import os
import shutil
from decimal import Decimal
from collections import defaultdict
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
        username = body.get('username')
        password = body.get('password')
        
        from django.contrib.auth import authenticate
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            from django.contrib.auth import login
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

# ==================== API ОСНОВНЫЕ ====================

@require_http_methods(["GET"])
def api_dishes(request):
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
    categories = Category.objects.all().order_by('order')
    data = [{'id': c.id, 'name': c.name, 'icon': c.icon} for c in categories]
    return JsonResponse({'success': True, 'data': data})

@require_http_methods(["GET"])
def api_tables(request):
    tables = Table.objects.all().order_by('number')
    data = [{
        'id': t.id,
        'number': t.number,
        'seats': t.seats,
        'status': t.status,
    } for t in tables]
    return JsonResponse({'success': True, 'data': data})

@csrf_exempt
@require_http_methods(["POST"])
def api_create_order(request):
    try:
        body = json.loads(request.body)
        table_id = body.get('table_id')
        items = body.get('items', [])
        guest_count = body.get('guest_count', 1)
        client_time = body.get('client_time')
        
        table = Table.objects.get(id=table_id)
        
        # Используем время с компьютера пользователя, если передано
        if client_time:
            parsed = parse_datetime(client_time)
            if parsed is not None:
                # Если время пришло с timezone offset (например UTC из toISOString),
                # конвертируем в naive local datetime
                if parsed.tzinfo is not None:
                    current_time = parsed.astimezone().replace(tzinfo=None)
                else:
                    current_time = parsed
            else:
                current_time = datetime.now()
        else:
            current_time = datetime.now()
        
        order = Order.objects.create(
            table=table,
            status='new',
            guest_count=guest_count,
            created_at=current_time,
            updated_at=current_time
        )
        # auto_now_add игнорирует created_at при create(), поэтому обновляем явно
        Order.objects.filter(pk=order.pk).update(created_at=current_time)
        
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
        
        return JsonResponse({'success': True, 'order_id': order.id, 'total': float(total)})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@require_http_methods(["GET"])
def api_active_orders(request):
    orders = Order.objects.filter(status__in=['new', 'cooking', 'ready']).select_related('table').prefetch_related('items__dish')
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
        body = json.loads(request.body)
        item_id = body.get('item_id')
        status = body.get('status')
        
        item = OrderItem.objects.get(id=item_id)
        item.status = status
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
        body = json.loads(request.body)
        order_id = body.get('order_id')
        order = Order.objects.get(id=order_id)
        order.status = 'ready'
        order.ready_at = datetime.now()
        order.save()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@csrf_exempt
@require_http_methods(["POST"])
def api_take_order(request):
    try:
        body = json.loads(request.body)
        order_id = body.get('order_id')
        order = Order.objects.get(id=order_id)
        order.status = 'served'
        order.save()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@csrf_exempt
@require_http_methods(["POST"])
def api_pay_order(request):
    try:
        body = json.loads(request.body)
        order_id = body.get('order_id')
        payment_method = body.get('payment_method')
        
        order = Order.objects.get(id=order_id)
        order.status = 'paid'
        order.payment_method = payment_method
        order.save()
        
        table = order.table
        table.status = 'free'
        table.save()
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@require_http_methods(["GET"])
def api_order_receipt(request, order_id):
    try:
        order = Order.objects.get(id=order_id)
        items = []
        for item in order.items.all():
            items.append({
                'name': item.dish.name,
                'quantity': item.quantity,
                'price': float(item.price),
                'total': float(item.price * item.quantity)
            })
        
        payment_method_display = {
            'cash': 'Наличные',
            'card': 'Карта',
            'qr': 'QR-код'
        }.get(order.payment_method, 'Не оплачен')
        
        receipt_data = {
            'order_id': order.id,
            'table_number': order.table.number,
            'created_at': order.created_at.strftime('%d.%m.%Y %H:%M') if order.created_at else '',
            'items': items,
            'total': float(order.total_amount),
            'payment_method': payment_method_display
        }
        return JsonResponse({'success': True, 'data': receipt_data})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

# ==================== API ОТЧЁТОВ ====================

@require_http_methods(["GET"])
def api_reports(request):
    period = request.GET.get('period', 'week')
    
    today = datetime.now().date()
    
    if period == 'day':
        start_date = today
        end_date = today
    elif period == 'week':
        start_date = today - timedelta(days=7)
        end_date = today
    elif period == 'month':
        start_date = today - timedelta(days=30)
        end_date = today
    elif period == 'custom':
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        if date_from:
            start_date = datetime.strptime(date_from, '%Y-%m-%d').date()
        else:
            start_date = today - timedelta(days=7)
        if date_to:
            end_date = datetime.strptime(date_to, '%Y-%m-%d').date()
        else:
            end_date = today
    else:
        start_date = today - timedelta(days=7)
        end_date = today
    
    orders = Order.objects.filter(
        status='paid',
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    ).order_by('created_at')
    
    total_revenue = sum(float(o.total_amount) for o in orders)
    total_orders = orders.count()
    avg_check = total_revenue / total_orders if total_orders > 0 else 0
    
    dish_data = {}
    for order in orders:
        for item in order.items.all():
            dish_name = item.dish.name
            dish_price = float(item.price)
            if dish_name not in dish_data:
                dish_data[dish_name] = {'count': 0, 'price': dish_price}
            dish_data[dish_name]['count'] += item.quantity
    
    popular_dishes = [
        {'name': name, 'count': data['count'], 'price': data['price']} 
        for name, data in sorted(dish_data.items(), key=lambda x: -x[1]['count'])
    ][:5]
    
    daily_data = []
    delta = (end_date - start_date).days
    for i in range(delta + 1):
        day = start_date + timedelta(days=i)
        day_orders = orders.filter(created_at__date=day)
        daily_data.append({
            'date': day.strftime('%d.%m'),
            'revenue': sum(float(o.total_amount) for o in day_orders),
            'orders': day_orders.count(),
        })
    
    return JsonResponse({
        'success': True,
        'data': {
            'total_revenue': total_revenue,
            'total_orders': total_orders,
            'avg_check': avg_check,
            'popular_dishes': popular_dishes,
            'daily_data': daily_data,
        }
    })

# ==================== API ЖУРНАЛА ТО ====================

@require_http_methods(["GET"])
def api_maintenance_logs(request):
    logs = MaintenanceLog.objects.all()
    data = [{
        'id': log.id,
        'date': log.date.strftime('%Y-%m-%d'),
        'work_performed': log.work_performed,
        'performed_by': log.performed_by,
        'signature': log.signature
    } for log in logs]
    return JsonResponse({'success': True, 'data': data})

@csrf_exempt
@require_http_methods(["POST"])
def api_maintenance_logs_add(request):
    try:
        body = json.loads(request.body)
        log = MaintenanceLog.objects.create(
            date=body.get('date'),
            work_performed=body.get('work_performed'),
            performed_by=body.get('performed_by')
        )
        return JsonResponse({'success': True, 'id': log.id})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

# ==================== РЕЗЕРВНОЕ КОПИРОВАНИЕ ====================

@login_required(login_url="/")
def admin_backup(request):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('/')
    backups = []
    backup_dir = 'backups'

    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)

    if request.method == 'POST':
        db_path = 'db.sqlite3'
        if os.path.exists(db_path):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = os.path.join(backup_dir, f'db_backup_{timestamp}.sqlite3')
            shutil.copy2(db_path, backup_path)
            # Удаляем старые копии (старше 30 дней)
            for file in os.listdir(backup_dir):
                file_path = os.path.join(backup_dir, file)
                if os.path.isfile(file_path) and os.path.getctime(file_path) < (datetime.now().timestamp() - 30 * 24 * 3600):
                    os.remove(file_path)
        return redirect('/admin/backup/')

    if os.path.exists(backup_dir):
        for file in os.listdir(backup_dir):
            file_path = os.path.join(backup_dir, file)
            if os.path.isfile(file_path) and file.endswith('.sqlite3'):
                stat = os.stat(file_path)
                backups.append({
                    'name': file,
                    'date': datetime.fromtimestamp(stat.st_ctime).strftime('%Y-%m-%d %H:%M:%S'),
                    'size': round(stat.st_size / 1024, 2)
                })
        backups.sort(key=lambda x: x['date'], reverse=True)

    return render(request, 'backup.html', {'backups': backups})

@login_required(login_url="/")
def admin_backup_download(request, filename):
    backup_dir = 'backups'
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(backup_dir, safe_filename)

    if not os.path.exists(file_path) or not safe_filename.endswith('.sqlite3'):
        raise Http404("Файл не найден")

    with open(file_path, 'rb') as f:
        response = HttpResponse(f.read(), content_type='application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename="{safe_filename}"'
        return response

@login_required(login_url="/")
def admin_backup_restore(request, filename):
    backup_dir = 'backups'
    safe_filename = os.path.basename(filename)
    backup_path = os.path.join(backup_dir, safe_filename)
    db_path = 'db.sqlite3'

    if not os.path.exists(backup_path):
        raise Http404("Файл не найден")

    # Создаём автоматический бэкап перед восстановлением
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    auto_backup_path = os.path.join(backup_dir, f'auto_before_restore_{timestamp}.sqlite3')
    if os.path.exists(db_path):
        shutil.copy2(db_path, auto_backup_path)

    shutil.copy2(backup_path, db_path)
    return redirect('/admin/backup/')

@login_required(login_url="/")
def admin_backup_delete(request, filename):
    backup_dir = 'backups'
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(backup_dir, safe_filename)

    if os.path.exists(file_path) and safe_filename.endswith('.sqlite3'):
        os.remove(file_path)

    return redirect('/admin/backup/')
