from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django import forms
from .models import Category, Dish, Table, Order, OrderItem, MaintenanceLog, Profile

# ========== ПРОФИЛЬ (INLINE) ==========
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Профиль'
    fields = ('role',)   # убрали пин-код

# ========== ФОРМА ДОБАВЛЕНИЯ ПОЛЬЗОВАТЕЛЯ (только логин, пароль, роль) ==========
class UserAddForm(forms.ModelForm):
    password1 = forms.CharField(label='Пароль', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Подтверждение пароля', widget=forms.PasswordInput)
    role = forms.ChoiceField(choices=Profile.ROLE_CHOICES, label='Роль', initial='waiter')

    class Meta:
        model = User
        fields = ('username',)

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('Пользователь с таким именем уже существует.')
        return username

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('Пароли не совпадают.')
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
            Profile.objects.create(user=user, role=self.cleaned_data['role'])
        return user

# ========== КАСТОМНЫЙ USER ADMIN ==========
class CustomUserAdmin(UserAdmin):
    add_form = UserAddForm
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'role'),
        }),
    )
    list_display = ['username', 'email', 'first_name', 'last_name', 'get_role', 'is_staff']
    list_filter = ['is_staff', 'is_superuser', 'profile__role']
    search_fields = ['username', 'email']
    inlines = [ProfileInline]

    def get_role(self, obj):
        if hasattr(obj, 'profile'):
            return obj.profile.get_role_display()
        return 'Не указана'
    get_role.short_description = 'Роль'
    get_role.admin_order_field = 'profile__role'

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

# ========== КАТЕГОРИИ ==========
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'icon', 'order']
    list_editable = ['order']
    search_fields = ['name']

# ========== БЛЮДА ==========
@admin.register(Dish)
class DishAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'is_available']
    list_filter = ['category', 'is_available']
    search_fields = ['name']

# ========== СТОЛЫ (убраны поля X, Y, статус из формы) ==========
@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ['number', 'seats', 'status']
    list_filter = ['status']
    list_editable = ['status']
    fields = ('number', 'seats')   # только номер и количество мест

# ========== ЗАКАЗЫ ==========
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'table', 'get_waiter_name', 'created_at', 'status', 'total_amount', 'payment_method']
    list_filter = ['status', 'created_at']
    search_fields = ['table__number']

    def get_waiter_name(self, obj):
        if obj.waiter:
            return obj.waiter.username
        return 'Admin'
    get_waiter_name.short_description = 'Официант'

# ========== ПОЗИЦИИ ЗАКАЗА ==========
@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'dish', 'quantity', 'price', 'status']
    list_filter = ['status']

# ========== ЖУРНАЛ ТО (без поля Подпись) ==========
@admin.register(MaintenanceLog)
class MaintenanceLogAdmin(admin.ModelAdmin):
    list_display = ['date', 'work_performed', 'performed_by', 'created_at']
    list_filter = ['date']
    search_fields = ['work_performed', 'performed_by']
