# Generated by Django 4.0.4 on 2022-05-01 17:21

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ecom', '0004_remove_orders_email'),
    ]

    operations = [
        migrations.AddField(
            model_name='orders',
            name='Payment',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='ecom.payment'),
        ),
    ]