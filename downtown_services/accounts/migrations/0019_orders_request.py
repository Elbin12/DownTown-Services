# Generated by Django 5.1.1 on 2024-11-21 14:11

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0018_alter_orderpayment_total_amount'),
        ('worker', '0023_alter_requests_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='orders',
            name='request',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='serviced_request', to='worker.requests'),
        ),
    ]
