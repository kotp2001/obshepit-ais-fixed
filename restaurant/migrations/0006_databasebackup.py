from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('restaurant', '0005_maintenance_log_data'),
    ]

    operations = [
        migrations.CreateModel(
            name='DatabaseBackup',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='Название')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создана')),
                ('data', models.TextField(verbose_name='Данные (JSON)')),
                ('size', models.IntegerField(default=0, verbose_name='Размер, байт')),
                ('records_count', models.IntegerField(default=0, verbose_name='Записей в копии')),
                ('fmt', models.CharField(default='json', max_length=10, verbose_name='Формат')),
                ('note', models.CharField(blank=True, max_length=300, verbose_name='Комментарий')),
            ],
            options={
                'verbose_name': 'Резервная копия',
                'verbose_name_plural': 'Резервные копии',
                'ordering': ['-created_at'],
            },
        ),
    ]
