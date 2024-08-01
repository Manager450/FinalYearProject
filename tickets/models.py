from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import  post_save
from django.dispatch import receiver


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
    bus_type = models.CharField(max_length=50)  # Add this field
    total_seats = models.IntegerField(default=40)  # Add this field

    def __str__(self):
           return self.name

    def available_seats(self):
           return self.seat_set.filter(is_available=True).count()
   


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
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE)
    seat = models.ForeignKey(Seat, on_delete=models.CASCADE)
    seat_number = models.CharField(max_length=5)
    booked_on = models.DateTimeField(auto_now_add=True)
    boarding_point = models.ForeignKey(BusStop, related_name='booking_boarding_point', on_delete=models.CASCADE, default=1)
    dropping_point = models.ForeignKey(BusStop, related_name='booking_dropping_point', on_delete=models.CASCADE, default=1)

    def __str__(self):
        return f"{self.user.username} - {self.bus.name} - {self.seat.seat_number}"

class Payment(models.Model):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[('Success', 'Success'), ('Failed', 'Failed')])

    def __str__(self):
        return f"{self.booking} - {self.status}"

class Review(models.Model):
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField()
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.bus.name} - {self.rating}"

@receiver(post_save, sender=Bus)
def create_seats(sender, instance, created, **kwargs):
       if created:
           for i in range(1, instance.total_seats + 1):
               seat_number = f'{i}'
               Seat.objects.create(bus=instance, seat_number=seat_number)