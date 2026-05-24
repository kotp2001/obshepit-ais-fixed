from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from restaurant.models import Profile

class Command(BaseCommand):
    help = 'Создание пользователей с ролями'

    def handle(self, *args, **options):
        users_data = [
            {'username': 'admin',  'password': 'admin123',  'role': 'admin',  'is_superuser': True, 'is_staff': True},
            {'username': 'waiter', 'password': 'waiter123', 'role': 'waiter', 'pin_code': '1234'},
            {'username': 'chef',   'password': 'chef123',   'role': 'chef'},
        ]

        for data in users_data:
            user, created = User.objects.get_or_create(username=data['username'])
            if created:
                user.set_password(data['password'])
            else:
                # Всегда обновляем пароль чтобы логин работал
                user.set_password(data['password'])

            if data.get('is_superuser'):
                user.is_superuser = True
                user.is_staff = True
            user.save()

            # Создаём или обновляем профиль
            profile, _ = Profile.objects.get_or_create(user=user)
            profile.role = data['role']
            profile.pin_code = data.get('pin_code', '')
            profile.save()

            status = 'Создан' if created else 'Обновлён'
            self.stdout.write(self.style.SUCCESS(
                f'{status}: {data["username"]} / {data["password"]} (роль: {data["role"]})'
            ))
