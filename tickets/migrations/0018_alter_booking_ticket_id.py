# Generated by Django 5.1 on 2024-09-06 01:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0017_alter_booking_boarding_point_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='booking',
            name='ticket_id',
            field=models.CharField(default='13636A00', max_length=8, unique=True),
        ),
    ]
