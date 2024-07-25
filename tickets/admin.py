from django.contrib import admin
from .models import Bus, Booking, Payment, Review, BusOperator, Seat, BusStop, BusRoute

admin.site.register(Bus)
admin.site.register(Booking)
admin.site.register(Payment)
admin.site.register(Review)
admin.site.register(BusOperator)
admin.site.register(Seat)
admin.site.register(BusStop)
admin.site.register(BusRoute)