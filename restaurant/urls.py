from django.urls import path
from . import views
from .excel import export_orders_excel, export_popular_excel

urlpatterns = [
    # Главная страница
    path('', views.landing, name='landing'),
    
    # Страницы для сотрудников
    path('waiter/', views.waiter_hall, name='waiter'),
    path('kitchen/', views.kitchen_view, name='kitchen'),
    path('reports/', views.reports_view, name='reports'),
    path('admin-panel/', views.admin_panel, name='admin_panel'),
    
    # Документация
    path('help/', views.help_page, name='help'),
    path('docs/', views.docs_page, name='docs'),
    path('maintenance-log/', views.maintenance_log_page, name='maintenance_log'),
    
    # Резервное копирование (ручное)
    path('admin/backup/', views.admin_backup, name='admin_backup'),
    path('admin/backup/download/<str:filename>/', views.admin_backup_download, name='admin_backup_download'),
    path('admin/backup/restore/<str:filename>/', views.admin_backup_restore, name='admin_backup_restore'),
    path('admin/backup/delete/<str:filename>/', views.admin_backup_delete, name='admin_backup_delete'),
    
    # Автоматическое резервное копирование (cron)
    path('api/auto-backup/', views.auto_backup_trigger, name='auto_backup_trigger'),
    path('admin/auto-backups/', views.list_auto_backups, name='list_auto_backups'),
    path('admin/auto-backups/download/<str:filename>/', views.download_auto_backup, name='download_auto_backup'),
    
    # API
    path('api/login/', views.api_login, name='api_login'),
    path('api/dishes/', views.api_dishes, name='api_dishes'),
    path('api/categories/', views.api_categories, name='api_categories'),
    path('api/tables/', views.api_tables, name='api_tables'),
    path('api/orders/create/', views.api_create_order, name='api_create_order'),
    path('api/orders/active/', views.api_active_orders, name='api_active_orders'),
    path('api/orders/update-item/', views.api_update_item_status, name='api_update_item'),
    path('api/orders/mark-ready/', views.api_mark_order_ready, name='api_mark_ready'),
    path('api/orders/take/', views.api_take_order, name='api_take_order'),
    path('api/orders/pay/', views.api_pay_order, name='api_pay_order'),
    path('api/orders/receipt/<int:order_id>/', views.api_order_receipt, name='api_receipt'),
    path('api/reports/', views.api_reports, name='api_reports'),
    path('api/maintenance-logs/', views.api_maintenance_logs, name='api_maintenance_logs'),
    path('api/maintenance-logs/add/', views.api_maintenance_logs_add, name='api_maintenance_logs_add'),
    
    # Экспорт
    path('export/orders/', export_orders_excel, name='export_orders'),
    path('export/popular/', export_popular_excel, name='export_popular'),
]
