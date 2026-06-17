# ==========================================================================
#  restaurant/admin.py
#  Настройка административной панели Django для всех моделей системы.
#  Здесь задаётся, какие поля показывать в списках, какие формы использовать,
#  какие проверки выполнять при сохранении и какие действия скрыть.
# ==========================================================================
from django.contrib import admin
from django import forms
from datetime import datetime
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import Category, Dish, Table, Order, OrderItem, MaintenanceLog, Profile, ActionLog, Receipt, LoginAttempt


# ===== ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ (роль сотрудника) =====
# Профиль выводится «встроенно» (inline) прямо на странице пользователя.
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Профиль и роль'
    # В форме создания/редактирования пользователя оставляем ТОЛЬКО роль.
    # Пин-код убран по требованию: при создании сотрудника достаточно
    # логина, пароля, подтверждения пароля и роли.
    fields = ('role',)
    extra = 0


# ===== ПОЛЬЗОВАТЕЛИ (русские заголовки, без массовых действий) =====
class CustomUserAdmin(UserAdmin):
    inlines = [ProfileInline]                      # к пользователю прикрепляем профиль с ролью
    # Колонки в списке сотрудников
    list_display = ['id', 'username', 'is_staff', 'is_active']
    list_display_links = ['id', 'username']
    list_filter = []                               # фильтры справа не показываем
    search_fields = ['username', 'email']          # строка поиска ищет по логину и email
    actions = None                                 # убираем выпадающее меню массовых действий

    # Поля на странице РЕДАКТИРОВАНИЯ существующего пользователя
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Личные данные', {'fields': ('first_name', 'last_name', 'email')}),
        ('Права доступа', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Важные даты', {'fields': ('last_login', 'date_joined')}),
    )
    # Поля на странице СОЗДАНИЯ нового пользователя: логин + пароль + подтверждение.
    # Роль добавляется через встроенный профиль (ProfileInline) ниже на той же странице.
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2'),
        }),
    )


# Перерегистрируем модель User со своими настройками
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


# ===== КАТЕГОРИИ БЛЮД =====
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'order']         # столбцы списка
    list_display_links = ['id', 'name']            # кликабельные ячейки (переход в карточку)
    search_fields = ['name']                       # поиск по названию
    ordering = ['order']                           # сортировка по полю «порядок»
    fields = ['name', 'order']                     # в форме только название и порядок (иконку не редактируем)
    actions = None


# ===== БЛЮДА =====
@admin.register(Dish)
class DishAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'category', 'price', 'is_available']
    list_display_links = ['id', 'name']
    list_editable = ['price', 'is_available']      # цену и доступность можно править прямо в списке
    search_fields = ['name']
    fields = ['name', 'category', 'price', 'is_available']
    actions = None


# ===== СТОЛЫ =====
class TableAdminForm(forms.ModelForm):
    """Форма стола с проверками ввода.

    * Номер стола — только ручной ввод (без стрелок-«ползунка»), не меньше 1, без повторов.
    * Количество мест — целое число СТРОГО больше 0 (не меньше 0 и не равно 0).
    """

    # Поле «Номер стола»: текстовое поле с числовой клавиатурой на телефоне.
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

    # Поле «Количество мест»: минимум 1 (стол без мест не имеет смысла).
    seats = forms.IntegerField(
        min_value=1,
        label='Количество мест',
        widget=forms.NumberInput(attrs={
            'min': 1,
            'step': 1,
            'placeholder': 'Например, 4',
        }),
        error_messages={
            'min_value': 'Количество мест должно быть больше 0.',
            'invalid': 'Введите количество мест числом.',
            'required': 'Укажите количество мест.',
        },
    )

    class Meta:
        model = Table
        fields = ['number', 'seats', 'status']

    def clean_number(self):
        # Проверяем номер стола: >= 1 и уникальность.
        number = self.cleaned_data.get('number')
        if number is None:
            return number
        if number < 1:
            raise forms.ValidationError('Номер стола не может быть меньше 1.')
        qs = Table.objects.filter(number=number)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)     # при редактировании не считаем сам себя
        if qs.exists():
            raise forms.ValidationError(f'Стол №{number} уже существует, выберите другой номер.')
        return number

    def clean_seats(self):
        # Проверяем количество мест: не пустое, не меньше 0 и не равно 0 (то есть >= 1).
        seats = self.cleaned_data.get('seats')
        if seats is None:
            raise forms.ValidationError('Укажите количество мест.')
        if seats <= 0:
            raise forms.ValidationError('Количество мест должно быть больше 0.')
        return seats


@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    form = TableAdminForm                          # используем форму с проверками выше
    list_display = ['number', 'seats', 'get_status_display']
    list_display_links = ['number']
    ordering = ['number']
    fields = ['number', 'seats', 'status']
    actions = None

    def get_status_display(self, obj):
        # Человекочитаемый статус стола (Свободен / Занят / Забронирован)
        return obj.get_status_display()
    get_status_display.short_description = 'Статус'


# ===== ПОЗИЦИИ ЗАКАЗА (встроенный список внутри заказа) =====
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    # ВАЖНО: 'get_status_display' — это метод, а не поле модели. Чтобы Django
    # не падал с ошибкой «Unknown field(s) (get_status_display)» при открытии
    # страницы добавления заказа, метод обязательно указывается в readonly_fields.
    fields = ['dish', 'quantity', 'price', 'get_status_display']
    readonly_fields = ['get_status_display']
    show_change_link = True
    can_delete = True

    def get_status_display(self, obj):
        # Статус позиции заказа (В очереди / Готовится / Готов / Подано)
        return obj.get_status_display()
    get_status_display.short_description = 'Статус'


# ===== ФОРМА ЗАКАЗА =====
class OrderAdminForm(forms.ModelForm):
    # Дата и время создания вводятся двумя полями (дата + время).
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
        # Если дату не указали — подставляем текущий момент.
        val = self.cleaned_data.get('created_at')
        if not val:
            return datetime.now()
        return val


# ===== ЗАКАЗЫ =====
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    form = OrderAdminForm
    # В списке заказов показываем: ID, цену, стол, тип оплаты, дату.
    list_display = ['id', 'get_price', 'get_table_display', 'get_payment_display', 'get_date']
    list_display_links = ['id']
    list_editable = []
    search_fields = ['id', 'table__number']
    date_hierarchy = 'created_at'                   # навигация по датам сверху
    inlines = [OrderItemInline]                    # позиции заказа редактируются на той же странице
    readonly_fields = []
    fields = ['table', 'waiter', 'created_at', 'status', 'payment_method', 'guest_count']
    actions = None

    # --- вычисляемые столбцы для списка ---
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
        # Предзаполняем поле даты/времени текущим моментом при создании заказа.
        from datetime import datetime
        initial = super().get_changeform_initial_data(request)
        now = datetime.now()
        initial['created_at_0'] = now.strftime('%Y-%m-%d')
        initial['created_at_1'] = now.strftime('%H:%M:%S')
        return initial

    def save_model(self, request, obj, form, change):
        # При сохранении: если дата пустая — ставим сейчас; если официант не задан — текущий пользователь.
        from datetime import datetime
        if obj.created_at is None:
            obj.created_at = datetime.now()
        if not obj.waiter_id:
            obj.waiter = request.user
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        # После сохранения позиций пересчитываем общую сумму заказа.
        super().save_related(request, form, formsets, change)
        order = form.instance
        total = sum((i.price or 0) * (i.quantity or 0) for i in order.items.all())
        if order.total_amount != total:
            order.total_amount = total
            order.save(update_fields=['total_amount'])


# ===== ПОЗИЦИИ ЗАКАЗА (как отдельный раздел) =====
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


# ===== ОБЩИЕ НАДПИСИ АДМИНКИ =====
admin.site.site_header = 'АИС «Общепит»'
admin.site.site_title = 'АИС Общепит'
admin.site.index_title = 'Панель управления'


# ===== ЖУРНАЛ ДЕЙСТВИЙ (только чтение) =====
@admin.register(ActionLog)
class ActionLogAdmin(admin.ModelAdmin):
    # Показываем: ID, время, пользователь, действие, IP-адрес.
    list_display = ['id', 'timestamp', 'user', 'action', 'ip_address']
    list_display_links = ['id']
    list_filter = []
    search_fields = ['user__username', 'description', 'ip_address']
    readonly_fields = ['user', 'action', 'description', 'ip_address', 'timestamp']
    ordering = ['-timestamp']
    actions = None
    list_per_page = 100                            # 100 записей на страницу

    # Журнал нельзя редактировать или добавлять вручную — только просматривать и чистить.
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


# ===== ЧЕКИ (только чтение) =====
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


# ===== ПОПЫТКИ ВХОДА (для блокировки подбора пароля) =====
@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    list_display = ['username', 'ip_address', 'attempts', 'blocked_until', 'last_attempt', 'is_blocked']
    list_display_links = ['username']
    list_filter = []
    search_fields = ['username', 'ip_address']
    readonly_fields = ['username', 'ip_address', 'last_attempt']
    ordering = ['-last_attempt']
    actions = ['unblock_users']                     # единственное оставленное действие — разблокировка

    def is_blocked(self, obj):
        # Зелёная галочка/крест: заблокирован ли вход прямо сейчас.
        from django.utils import timezone
        return bool(obj.blocked_until and obj.blocked_until > timezone.now())
    is_blocked.boolean = True
    is_blocked.short_description = 'Заблокирован'

    @admin.action(description='Снять блокировку (сбросить 15-минутное ожидание)')
    def unblock_users(self, request, queryset):
        # Обнуляем счётчик попыток и снимаем блокировку у выбранных записей.
        updated = queryset.update(attempts=0, blocked_until=None)
        self.message_user(request, f'Разблокировано пользователей: {updated}.')
