from django.urls import path
from . import backup_views

app_name = 'backup'

urlpatterns = [
    path('', backup_views.backup_list, name='backup_list'),
    path('create/', backup_views.backup_create, name='backup_create'),
    path('download/<int:pk>/', backup_views.backup_download, name='backup_download'),
    path('restore/<int:pk>/', backup_views.backup_restore, name='backup_restore'),
    path('delete/<int:pk>/', backup_views.backup_delete, name='backup_delete'),
    path('upload/', backup_views.backup_upload, name='backup_upload'),
]
