from django.contrib import admin
from django.core.exceptions import ValidationError
from django.forms import ModelForm
from .models import Bus, Booking, Payment, Review, BusOperator, Seat, BusStop, BusRoute

# Custom form for the Seat model
class SeatForm(ModelForm):
    class Meta:
        model = Seat
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        seat_number = cleaned_data.get('seat_number')
        bus = cleaned_data.get('bus')

        if seat_number and bus and seat_number > bus.total_seats:
            raise ValidationError(
                'Seat number %(seat_number)s cannot be greater than the total number of seats %(total_seats)s.',
                params={'seat_number': seat_number, 'total_seats': bus.total_seats},
            )

# Custom admin class for the Seat model
class SeatAdmin(admin.ModelAdmin):
    form = SeatForm


admin.site.register(Bus)
admin.site.register(Booking)
admin.site.register(Payment)
admin.site.register(Review)
admin.site.register(BusOperator)
admin.site.register(Seat, SeatAdmin)
admin.site.register(BusStop)
admin.site.register(BusRoute)