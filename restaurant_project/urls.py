from django.contrib import admin
from django.urls import path, include

# Устанавливаем URL для админ-панели (вместо /admin/)
urlpatterns = [
    path('secret-admin/', admin.site.urls),  # <-- теперь админка доступна только по этому URL
    path('backup/', include('restaurant.backup_urls')),
    path('', include('restaurant.urls')),
]
