# Generated by Django 4.0.4 on 2022-05-02 20:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ecom', '0005_orders_payment'),
    ]

    operations = [
        migrations.AddField(
            model_name='orders',
            name='ref_code',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
    ]
