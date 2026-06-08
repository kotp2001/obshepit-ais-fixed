from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('restaurant', '0003_actionlog_receipt_loginattempt'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='created_at',
            field=models.DateTimeField(
                blank=True,
                default=django.utils.timezone.now,
                verbose_name='Создан',
            ),
        ),
    ]
