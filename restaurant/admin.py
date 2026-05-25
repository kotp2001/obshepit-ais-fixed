from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import Category, Dish, Table, Order, OrderItem, MaintenanceLog, Profile

class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Профиль'
    fields = ('role', 'pin_code')

class CustomUserAdmin(UserAdmin):
    inlines = [ProfileInline]
    list_display = ['username', 'email', 'first_name', 'last_name', 'get_role', 'is_staff']
    list_filter = ['is_staff', 'is_superuser', 'profile__role']
    search_fields = ['username', 'email']
    
    def get_role(self, obj):
        if hasattr(obj, 'profile'):
            return obj.profile.get_role_display()
        return 'Не указана'
    get_role.short_description = 'Роль'
    get_role.admin_order_field = 'profile__role'

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'icon', 'order']
    list_editable = ['order']
    search_fields = ['name']

@admin.register(Dish)
class DishAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'is_available']
    list_filter = ['category', 'is_available']
    search_fields = ['name']

@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ['number', 'seats', 'status']
    list_filter = ['status']
    list_editable = ['status']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'table', 'waiter', 'created_at', 'status', 'total_amount']
    list_filter = ['status', 'created_at']
    search_fields = ['id', 'table__number']
    date_hierarchy = 'created_at'
    # created_at доступен для редактирования — можно задавать дату прошлых заказов
    fields = ['table', 'waiter', 'created_at', 'status', 'total_amount', 'payment_method', 'guest_count', 'comment']
    readonly_fields = []

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'dish', 'quantity', 'price', 'status']
    list_filter = ['status']

@admin.register(MaintenanceLog)
class MaintenanceLogAdmin(admin.ModelAdmin):
    list_display = ['date', 'work_performed', 'performed_by', 'created_at']
    list_filter = ['date']
    search_fields = ['work_performed', 'performed_by']
