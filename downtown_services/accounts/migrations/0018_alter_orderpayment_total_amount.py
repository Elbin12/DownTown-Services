# Generated by Django 5.1.1 on 2024-11-14 17:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0017_orderpayment_created_at_orderpayment_updated_at_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='orderpayment',
            name='total_amount',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
