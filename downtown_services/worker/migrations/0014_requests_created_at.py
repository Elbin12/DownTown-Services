# Generated by Django 5.1.1 on 2024-11-07 14:59

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('worker', '0013_alter_requests_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='requests',
            name='created_at',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
    ]
