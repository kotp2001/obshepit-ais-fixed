from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from restaurant.models import Profile

class Command(BaseCommand):
    help = 'Создание пользователей с ролями'

    def handle(self, *args, **options):
        users_data = [
            {'username': 'admin', 'password': 'admin123', 'role': 'admin', 'is_superuser': True, 'is_staff': True},
            {'username': 'waiter', 'password': 'waiter123', 'role': 'waiter', 'pin_code': '1234'},
            {'username': 'chef', 'password': 'chef123', 'role': 'chef'},
        ]

        for data in users_data:
            user, created = User.objects.get_or_create(username=data['username'])
            if created:
                user.set_password(data['password'])
                if data.get('is_superuser'):
                    user.is_superuser = True
                    user.is_staff = True
                user.save()
                Profile.objects.create(
                    user=user,
                    role=data['role'],
                    pin_code=data.get('pin_code', '')
                )
                self.stdout.write(self.style.SUCCESS(f'Создан пользователь: {data["username"]} с ролью {data["role"]}'))
            else:
                self.stdout.write(self.style.WARNING(f'Пользователь уже существует: {data["username"]}'))
