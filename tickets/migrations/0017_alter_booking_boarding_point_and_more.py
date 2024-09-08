# Generated by Django 5.1 on 2024-09-05 16:43

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0016_alter_booking_ticket_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='booking',
            name='boarding_point',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='booking_boarding_point', to='tickets.busstop'),
        ),
        migrations.AlterField(
            model_name='booking',
            name='dropping_point',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='booking_dropping_point', to='tickets.busstop'),
        ),
        migrations.AlterField(
            model_name='booking',
            name='ticket_id',
            field=models.CharField(default='39CB2C25', max_length=8, unique=True),
        ),
    ]