# Generated by Django 5.1.1 on 2024-11-12 12:41

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0010_remove_userprofile_lat_remove_userprofile_lng_and_more'),
        ('worker', '0017_requests_is_completed'),
    ]

    operations = [
        migrations.CreateModel(
            name='Orders',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('service_name', models.CharField(max_length=255)),
                ('service_description', models.TextField()),
                ('service_price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('service_image_url', models.URLField(max_length=500)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('working', 'Working'), ('completed', 'Completed'), ('cancelled', 'Cancelled')], default='pending', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('service_provider', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='serviced_orders', to='worker.customworker')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='orders', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
