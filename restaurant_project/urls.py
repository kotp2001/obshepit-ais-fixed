from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),              # админка снова по /admin/
    path('backup/', include('restaurant.backup_urls')),
    path('', include('restaurant.urls')),         # все остальные пути
]
