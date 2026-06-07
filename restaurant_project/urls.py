from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('backup/', include('restaurant.backup_urls')),   # НЕ под admin/ !
    path('', include('restaurant.urls')),
]
