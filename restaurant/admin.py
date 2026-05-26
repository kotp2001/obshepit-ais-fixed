from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import Category, Dish, Table, Order, OrderItem, MaintenanceLog, Profile


# ===== ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ =====

class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Профиль и роль'
    fields = ('role', 'pin_code')
    extra = 0


class CustomUserAdmin(UserAdmin):
    inlines = [ProfileInline]
    list_display  = ['username', 'first_name', 'last_name', 'email', 'get_role', 'is_staff', 'is_active']
    list_filter   = ['is_staff', 'is_superuser', 'is_active', 'profile__role']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    list_editable = ['is_staff', 'is_active']

    # Полные поля редактирования пользователя
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Личные данные', {'fields': ('first_name', 'last_name', 'email')}),
        ('Права доступа', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Важные даты', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'first_name', 'last_name', 'email', 'is_staff'),
        }),
    )

    def get_role(self, obj):
        try:
            return obj.profile.get_role_display()
        except Exception:
            return '—'
    get_role.short_description = 'Роль'
    get_role.admin_order_field = 'profile__role'


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


# ===== КАТЕГОРИИ =====

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display  = ['id', 'name', 'icon', 'order']
    list_editable = ['name', 'icon', 'order']
    search_fields = ['name']
    ordering      = ['order']


# ===== БЛЮДА =====

@admin.register(Dish)
class DishAdmin(admin.ModelAdmin):
    list_display  = ['id', 'name', 'category', 'price', 'is_available', 'weight']
    list_filter   = ['category', 'is_available']
    list_editable = ['price', 'is_available']
    search_fields = ['name', 'description']
    fields        = ['name', 'category', 'description', 'price', 'weight', 'calories', 'image_url', 'is_available']


# ===== СТОЛЫ =====

@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display  = ['number', 'seats', 'status']
    list_filter   = ['status']
    list_editable = ['status', 'seats']
    ordering      = ['number']


# ===== ПОЗИЦИИ ЗАКАЗА (инлайн) =====

class OrderItemInline(admin.TabularInline):
    model   = OrderItem
    extra   = 0
    fields  = ['dish', 'quantity', 'price', 'status', 'comment']
    readonly_fields = []
    show_change_link = True


# ===== ЗАКАЗЫ =====

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display   = ['id', 'table', 'waiter', 'created_at', 'status', 'total_amount', 'payment_method']
    list_filter    = ['status', 'payment_method', 'created_at']
    list_editable  = ['status']
    search_fields  = ['id', 'table__number']
    date_hierarchy = 'created_at'
    inlines        = [OrderItemInline]
    readonly_fields = []
    fields         = ['table', 'waiter', 'created_at', 'status', 'total_amount', 'payment_method', 'guest_count', 'ready_at']


# ===== ПОЗИЦИИ ЗАКАЗА (отдельно) =====

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display  = ['id', 'order', 'dish', 'quantity', 'price', 'status']
    list_filter   = ['status']
    list_editable = ['quantity', 'price', 'status']
    search_fields = ['dish__name', 'order__id']
    readonly_fields = []


# ===== ЖУРНАЛ ТО =====

@admin.register(MaintenanceLog)
class MaintenanceLogAdmin(admin.ModelAdmin):
    list_display  = ['id', 'date', 'work_performed', 'performed_by', 'created_at']
    list_filter   = ['date']
    search_fields = ['work_performed', 'performed_by']
    fields        = ['date', 'work_performed', 'performed_by', 'signature']
    readonly_fields = []
