from django.contrib import admin
from django import forms
from datetime import datetime
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import Category, Dish, Table, Order, OrderItem, MaintenanceLog, Profile, ActionLog, Receipt, LoginAttempt


# ===== ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ =====

class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Профиль и роль'
    fields = ('role', 'pin_code')
    extra = 0


# ===== ПОЛЬЗОВАТЕЛИ (РУССКИЕ ЗАГОЛОВКИ, БЕЗ list_editable) =====

class CustomUserAdmin(UserAdmin):
    inlines = [ProfileInline]
    # Столбец get_role убран по требованию
    list_display = ['id', 'username', 'is_staff', 'is_active']
    list_display_links = ['id', 'username']
    list_filter = []
    search_fields = ['username', 'email']
    actions = None

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Личные данные', {'fields': ('first_name', 'last_name', 'email')}),
        ('Права доступа', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Важные даты', {'fields': ('last_login', 'date_joined')}),
    )
    # 'role' убрано из add_fieldsets — это поле модели Profile, а не User,
    # из-за чего страница добавления пользователя падала с FieldError.
    # Роль задаётся в блоке «Профиль и роль» на странице редактирования.
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2'),
        }),
    )


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


# ===== КАТЕГОРИИ (УБРАНА ИКОНКА) =====

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'order']
    list_display_links = ['id', 'name']
    search_fields = ['name']
    ordering = ['order']
    # Только название и порядок (иконку не показываем и не редактируем)
    fields = ['name', 'order']
    actions = None


# ===== БЛЮДА =====

@admin.register(Dish)
class DishAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'category', 'price', 'is_available']
    list_display_links = ['id', 'name']
    list_editable = ['price', 'is_available']
    search_fields = ['name']
    fields = ['name', 'category', 'price', 'is_available']
    actions = None


# ===== СТОЛЫ (ИСПРАВЛЕНЫ СТАТУСЫ) =====

class TableAdminForm(forms.ModelForm):
    # Номер стола вводится только вручную (без «ползунка»/стрелок),
    # не может быть меньше 1 и не может повторяться.
    number = forms.IntegerField(
        min_value=1,
        label='Номер стола',
        widget=forms.TextInput(attrs={
            'inputmode': 'numeric',
            'pattern': '[0-9]*',
            'autocomplete': 'off',
            'placeholder': 'Введите номер стола',
        }),
        error_messages={
            'min_value': 'Номер стола не может быть меньше 1.',
            'invalid': 'Введите номер стола числом.',
            'required': 'Укажите номер стола.',
        },
    )

    class Meta:
        model = Table
        fields = ['number', 'seats', 'status']

    def clean_number(self):
        number = self.cleaned_data.get('number')
        if number is None:
            return number
        if number < 1:
            raise forms.ValidationError('Номер стола не может быть меньше 1.')
        qs = Table.objects.filter(number=number)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(f'Стол №{number} уже существует, выберите другой номер.')
        return number


@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    form = TableAdminForm
    list_display = ['number', 'seats', 'get_status_display']
    list_display_links = ['number']
    ordering = ['number']
    fields = ['number', 'seats', 'status']
    actions = None

    def get_status_display(self, obj):
        # Используем встроенный метод модели
        return obj.get_status_display()
    get_status_display.short_description = 'Статус'


# ===== ПОЗИЦИИ ЗАКАЗА (ИНЛАЙН) =====

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ['dish', 'quantity', 'price', 'get_status_display']
    readonly_fields = []
    show_change_link = True
    can_delete = True

    def get_status_display(self, obj):
        return obj.get_status_display()
    get_status_display.short_description = 'Статус'


class OrderAdminForm(forms.ModelForm):
    created_at = forms.SplitDateTimeField(
        widget=forms.SplitDateTimeWidget(
            date_attrs={'type': 'date'},
            time_attrs={'type': 'time'},
        ),
        initial=datetime.now,
        required=False,
        label='Дата и время создания'
    )

    class Meta:
        model = Order
        fields = '__all__'

    def clean_created_at(self):
        val = self.cleaned_data.get('created_at')
        if not val:
            return datetime.now()
        return val


# ===== ЗАКАЗЫ =====

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    form = OrderAdminForm
    # Только: ID, цена, стол, тип оплаты, дата
    list_display = [
        'id',
        'get_price',
        'get_table_display',
        'get_payment_display',
        'get_date',
    ]
    list_display_links = ['id']
    list_editable = []
    search_fields = ['id', 'table__number']
    date_hierarchy = 'created_at'
    inlines = [OrderItemInline]
    readonly_fields = []
    fields = ['table', 'waiter', 'created_at', 'status', 'payment_method', 'guest_count']
    actions = None

    def get_price(self, obj):
        return f'{obj.total_amount} ₽'
    get_price.short_description = 'Цена'
    get_price.admin_order_field = 'total_amount'

    def get_date(self, obj):
        return obj.created_at.strftime('%d.%m.%Y %H:%M') if obj.created_at else '—'
    get_date.short_description = 'Дата'
    get_date.admin_order_field = 'created_at'

    def get_table_display(self, obj):
        return f'Стол {obj.table.number} ({obj.table.seats} мест)'
    get_table_display.short_description = 'Стол'

    def get_waiter_display(self, obj):
        if obj.waiter:
            return obj.waiter.username
        return 'Не назначен'
    get_waiter_display.short_description = 'Официант'

    def get_status_display(self, obj):
        return obj.get_status_display()
    get_status_display.short_description = 'Статус'

    def get_payment_display(self, obj):
        return obj.get_payment_method_display() if obj.payment_method else 'Ожидается'
    get_payment_display.short_description = 'Тип оплаты'

    def get_changeform_initial_data(self, request):
        from datetime import datetime
        initial = super().get_changeform_initial_data(request)
        now = datetime.now()
        initial['created_at_0'] = now.strftime('%Y-%m-%d')
        initial['created_at_1'] = now.strftime('%H:%M:%S')
        return initial

    def save_model(self, request, obj, form, change):
        from datetime import datetime
        if obj.created_at is None:
            obj.created_at = datetime.now()
        if not obj.waiter_id:
            obj.waiter = request.user
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        order = form.instance
        total = sum((i.price or 0) * (i.quantity or 0) for i in order.items.all())
        if order.total_amount != total:
            order.total_amount = total
            order.save(update_fields=['total_amount'])


# ===== ПОЗИЦИИ ЗАКАЗА (ОТДЕЛЬНО) =====

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'order', 'dish', 'quantity', 'price', 'get_status_display']
    list_display_links = ['id']
    list_editable = ['quantity', 'price']
    search_fields = ['dish__name', 'order__id']
    readonly_fields = []
    actions = None

    def get_status_display(self, obj):
        return obj.get_status_display()
    get_status_display.short_description = 'Статус'


# ===== ЖУРНАЛ ТО =====

@admin.register(MaintenanceLog)
class MaintenanceLogAdmin(admin.ModelAdmin):
    list_display = ['id', 'date', 'work_performed', 'performed_by', 'created_at']
    list_display_links = ['id']
    list_filter = []
    search_fields = ['work_performed', 'performed_by']
    fields = ['date', 'work_performed', 'performed_by']
    readonly_fields = []
    actions = None


# ===== КАСТОМИЗАЦИЯ DJANGO ADMIN =====
admin.site.site_header = 'АИС «Общепит»'
admin.site.site_title = 'АИС Общепит'
admin.site.index_title = 'Панель управления'


# ===== ЖУРНАЛ ДЕЙСТВИЙ =====
@admin.register(ActionLog)
class ActionLogAdmin(admin.ModelAdmin):
    # Только: ID, время, пользователь, действие, IP-адрес
    list_display = ['id', 'timestamp', 'user', 'action', 'ip_address']
    list_display_links = ['id']
    list_filter = []
    search_fields = ['user__username', 'description', 'ip_address']
    readonly_fields = ['user', 'action', 'description', 'ip_address', 'timestamp']
    ordering = ['-timestamp']
    actions = None
    list_per_page = 100  # листаем по 100 записей на страницу

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return True

    def add_view(self, request, form_url='', extra_context=None):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('Нельзя добавлять записи вручную')

    def change_view(self, request, object_id, form_url='', extra_context=None):
        from django.http import HttpResponseRedirect
        return HttpResponseRedirect('../')


# ===== ЧЕКИ =====
@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ['id', 'order', 'total', 'payment_method', 'created_at']
    list_display_links = ['id']
    list_filter = []
    readonly_fields = ['order', 'pdf_file', 'created_at', 'total', 'payment_method']
    ordering = ['-created_at']
    actions = None

    def has_add_permission(self, request):
        return False


# ===== ПОПЫТКИ ВХОДА =====
@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    list_display = ['username', 'ip_address', 'attempts', 'blocked_until', 'last_attempt', 'is_blocked']
    list_display_links = ['username']
    list_filter = []
    search_fields = ['username', 'ip_address']
    readonly_fields = ['username', 'ip_address', 'last_attempt']
    ordering = ['-last_attempt']
    actions = ['unblock_users']

    def is_blocked(self, obj):
        from django.utils import timezone
        return bool(obj.blocked_until and obj.blocked_until > timezone.now())
    is_blocked.boolean = True
    is_blocked.short_description = 'Заблокирован'

    @admin.action(description='Снять блокировку (сбросить 15-минутное ожидание)')
    def unblock_users(self, request, queryset):
        updated = queryset.update(attempts=0, blocked_until=None)
        self.message_user(request, f'Разблокировано пользователей: {updated}.')
