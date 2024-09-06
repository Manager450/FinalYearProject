from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.dispatch import receiver
from django.db.models.signals import  post_save
from django.core.exceptions import ValidationError
from .paystack import Paystack
import secrets
import uuid
from decimal import Decimal

class BusOperator(models.Model):
    name = models.CharField(max_length=100)
    contact_info = models.TextField()

    def __str__(self):
        return self.name

class Bus(models.Model):
    name = models.CharField(max_length=100)
    operator = models.ForeignKey(BusOperator, on_delete=models.CASCADE)
    departure_time = models.DateTimeField()
    arrival_time = models.DateTimeField()
    source = models.CharField(max_length=100)
    destination = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    amenities = models.TextField()
    bus_type = models.CharField(max_length=50)
    total_seats = models.IntegerField(default=50)

    def __str__(self):
        return self.name

    def available_seats(self):
        return self.seat_set.filter(is_available=True).count()

    @classmethod
    def clear_past_buses(cls):
        cls.objects.filter(departure_time__lt=timezone.now()).delete()

    def clean(self):
        if self.departure_time < timezone.now():
            raise ValidationError("Departure time cannot be in the past.")
        if self.arrival_time < self.departure_time:
            raise ValidationError("Arrival time cannot be earlier than departure time.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

class BusStop(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class BusRoute(models.Model):
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE)
    boarding_point = models.ForeignKey(BusStop, related_name='boarding_point', on_delete=models.CASCADE)
    dropping_point = models.ForeignKey(BusStop, related_name='dropping_point', on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.boarding_point} to {self.dropping_point}"

class Seat(models.Model):
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE)
    seat_number = models.CharField(max_length=5)
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.bus.name} - {self.seat_number}"

class Booking(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('cancelled', 'Cancelled'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE)
    seats = models.ManyToManyField(Seat)
    booked_on = models.DateTimeField(auto_now_add=True)
    boarding_point = models.ForeignKey(BusStop, related_name='booking_boarding_point', on_delete=models.CASCADE)
    dropping_point = models.ForeignKey(BusStop, related_name='booking_dropping_point', on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    cleared = models.BooleanField(default=False)
    ticket_id = models.CharField(max_length=8, unique=True, default=uuid.uuid4().hex[:8].upper())

    def __str__(self):
        return f"{self.user.username} - {self.bus.name}"

class Payment(models.Model):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reference = models.CharField(max_length=100, unique=True, null=True, blank=True)
    payment_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[
        ('Pending', 'Pending'),
        ('Success', 'Success'),
        ('Failed', 'Failed'),
        ('Refunded', 'Refunded'),
        ('RefundRequested', 'RefundRequested')
    ])
    refund_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.booking} - {self.status}"

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = secrets.token_urlsafe(20)
        super().save(*args, **kwargs)

    def amount_value(self):
        return int(self.amount * 100)

    def verify_payment(self):
        paystack = Paystack()
        status, result = paystack.verify_payment(self.reference)
        if status and result['amount'] / 100 == self.amount:
            self.status = 'Success'
            self.save()
            return True
        self.status = 'Failed'
        self.save()
        return False

class Review(models.Model):
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField()
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.bus.name} - {self.rating}"

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=15, blank=True)

    def __str__(self):
        return self.user.username


@receiver(post_save, sender=Bus)
def create_seats(sender, instance, created, **kwargs):
    if created:
        for i in range(1, instance.total_seats + 1):
            seat_number = f'{i}'
            Seat.objects.create(bus=instance, seat_number=seat_number)

@receiver(post_save, sender=Bus)
def clear_past_buses_on_save(sender, instance, **kwargs):
    Bus.clear_past_buses()
