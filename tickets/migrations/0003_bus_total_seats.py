# Generated by Django 5.0.6 on 2024-07-31 07:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0002_busstop_city'),
    ]

    operations = [
        migrations.AddField(
            model_name='bus',
            name='total_seats',
            field=models.IntegerField(default=40),
        ),
    ]
