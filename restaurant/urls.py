from django.urls import path
from . import views
from .excel import export_orders_excel, export_popular_excel

urlpatterns = [
    path('', views.landing, name='landing'),

    # Интерфейсы сотрудников
    path('waiter/',          views.waiter_hall,         name='waiter'),
    path('kitchen/',         views.kitchen_view,         name='kitchen'),
    path('reports/',         views.reports_view,         name='reports'),
    path('admin-panel/',     views.admin_panel,          name='admin_panel'),
    path('help/',            views.help_page,            name='help'),
    path('docs/',            views.docs_page,            name='docs'),
    path('maintenance-log/', views.maintenance_log_page, name='maintenance_log'),

    # API авторизации
    path('api/login/', views.api_login, name='api_login'),

    # API данные
    path('api/staff/',       views.api_staff,       name='api_staff'),
    path('api/dishes/',      views.api_dishes,      name='api_dishes'),
    path('api/categories/',  views.api_categories,  name='api_categories'),
    path('api/tables/',      views.api_tables,       name='api_tables'),

    # API заказы
    path('api/orders/create/',                   views.api_create_order,      name='api_create_order'),
    path('api/orders/active/',                   views.api_active_orders,     name='api_active_orders'),
    path('api/orders/update-item/',              views.api_update_item_status,name='api_update_item'),
    path('api/orders/mark-ready/',               views.api_mark_order_ready,  name='api_mark_ready'),
    path('api/orders/take/',                     views.api_take_order,        name='api_take_order'),
    path('api/orders/pay/',                      views.api_pay_order,         name='api_pay_order'),
    path('api/orders/receipt/<int:order_id>/',   views.api_order_receipt,     name='api_receipt'),

    # API отчёты и ТО
    path('api/reports/',                views.api_reports,             name='api_reports'),
    path('api/maintenance-logs/',       views.api_maintenance_logs,    name='api_maintenance_logs'),
    path('api/maintenance-logs/add/',   views.api_maintenance_logs_add,name='api_maintenance_logs_add'),

    # Разблокировка / смена пароля
    path('api/unblock-user/',    views.api_unblock_user,   name='api_unblock_user'),
    path('api/change-password/', views.api_change_password, name='api_change_password'),
    path('api/blocked-users/',   views.api_blocked_users,  name='api_blocked_users'),

    # Журнал действий
    path('api/action-logs/', views.api_action_logs, name='api_action_logs'),

    # Скачать чек
    path('receipts/<int:receipt_id>/download/', views.download_receipt, name='download_receipt'),

    # Авто-бэкап endpoint (для cron-job.org)
    path('api/auto-backup/', views.auto_backup_trigger, name='auto_backup_trigger'),

    # Экспорт Excel
    path('export/orders/',  export_orders_excel,  name='export_orders'),
    path('export/popular/', export_popular_excel,  name='export_popular'),
]
