# Generated by Django 5.1.1 on 2024-11-02 06:35

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('worker', '0010_alter_services_pic'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Requests',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('description', models.TextField()),
                ('status', models.CharField(choices=[('request_sent', 'Request Sent'), ('accepted', 'Accepted'), ('rejected', 'Rejected')], default='request_sent', max_length=20)),
                ('service', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='request', to='worker.services')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='request', to=settings.AUTH_USER_MODEL)),
                ('worker', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='request', to='worker.customworker')),
            ],
        ),
    ]
