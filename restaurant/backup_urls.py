from django.urls import path
from . import views

urlpatterns = [
    # Страница резервного копирования
    path('', views.admin_backup, name='admin_backup'),
    # Скачивание файла бэкапа
    path('download/<str:filename>/', views.admin_backup_download, name='admin_backup_download'),
    # Восстановление базы данных из бэкапа
    path('restore/<str:filename>/', views.admin_backup_restore, name='admin_backup_restore'),
    # Удаление файла бэкапа
    path('delete/<str:filename>/', views.admin_backup_delete, name='admin_backup_delete'),
]
