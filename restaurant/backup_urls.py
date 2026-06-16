from django.urls import path
from . import views

app_name = 'backup'

urlpatterns = [
    path('', views.backup_list, name='backup_list'),
    path('create/', views.backup_create, name='backup_create'),
    path('download/<str:filename>/', views.backup_download, name='backup_download'),
    path('restore/<str:filename>/', views.backup_restore, name='backup_restore'),
    path('delete/<str:filename>/', views.backup_delete, name='backup_delete'),
]
