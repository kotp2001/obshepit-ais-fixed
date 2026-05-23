import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill
from django.http import HttpResponse
from .models import Order, OrderItem, Dish
from datetime import datetime

def export_orders_excel(request):
    orders = Order.objects.filter(status='paid').order_by('-created_at')
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Заказы"
    
    # Заголовки
    headers = ['ID заказа', 'Стол', 'Дата', 'Время', 'Сумма', 'Способ оплаты', 'Позиции']
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center')
        cell.fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        cell.font = Font(bold=True, color="FFFFFF")
    
    # Данные
    for row, order in enumerate(orders, 2):
        items_text = ", ".join([f"{item.dish.name} x{item.quantity}" for item in order.items.all()])
        ws.cell(row=row, column=1, value=order.id)
        ws.cell(row=row, column=2, value=order.table.number)
        ws.cell(row=row, column=3, value=order.created_at.strftime('%d.%m.%Y'))
        ws.cell(row=row, column=4, value=order.created_at.strftime('%H:%M'))
        ws.cell(row=row, column=5, value=float(order.total_amount))
        ws.cell(row=row, column=6, value=dict(Order.PAYMENT_CHOICES).get(order.payment_method, ''))
        ws.cell(row=row, column=7, value=items_text)
    
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename=orders_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    wb.save(response)
    return response

def export_popular_excel(request):
    from collections import defaultdict
    dish_count = defaultdict(int)
    orders = Order.objects.filter(status='paid')
    for order in orders:
        for item in order.items.all():
            dish_count[item.dish.name] += item.quantity
    
    sorted_dishes = sorted(dish_count.items(), key=lambda x: -x[1])
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Популярные блюда"
    
    headers = ['Место', 'Блюдо', 'Количество продаж']
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center')
        cell.fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        cell.font = Font(bold=True, color="FFFFFF")
    
    for idx, (dish_name, count) in enumerate(sorted_dishes, 1):
        ws.cell(row=idx+1, column=1, value=idx)
        ws.cell(row=idx+1, column=2, value=dish_name)
        ws.cell(row=idx+1, column=3, value=count)
    
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename=popular_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    wb.save(response)
    return response
