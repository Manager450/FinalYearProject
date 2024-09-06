from django.contrib import admin
from django.db import models
from tickets.models import BusOperator, Bus, BusRoute, BusStop, Seat, Booking, Payment, Review, Profile
from django.core.exceptions import ValidationError
from django.forms import ModelForm
from decimal import Decimal
from django.db.models import Sum, F, DecimalField, Case, When, Count


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

class SeatAdmin(admin.ModelAdmin):
    form = SeatForm

@admin.register(BusOperator)
class BusOperatorAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_info', 'total_revenue', 'revenue_after_commission', 'seats_booked')
    search_fields = ('name',)

    def total_revenue(self, obj):
        return obj.total_revenue
    total_revenue.admin_order_field = 'total_revenue'

    def revenue_after_commission(self, obj):
        if obj.total_revenue:
            return obj.total_revenue - (obj.total_revenue * Decimal('0.10'))
        return Decimal('0.00')
    revenue_after_commission.admin_order_field = 'revenue_after_commission'

    def seats_booked(self, obj):
        return obj.seats_booked
    seats_booked.admin_order_field = 'seats_booked'

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            total_revenue=Sum(Case(
                When(bus__booking__status='active', then=F('bus__price')),
                output_field=DecimalField(),
            )),
            # Correcting the seats_booked aggregation using Count
            seats_booked=Count(
                'bus__booking__seats',
                filter=models.Q(bus__booking__status='active')
            )
        )
        return queryset

@admin.register(Bus)
class BusAdmin(admin.ModelAdmin):
    list_display = ('name', 'operator', 'departure_time', 'arrival_time', 'price', 'total_seats', 'get_total_amount', 'get_revenue_after_commission')
    list_filter = ('operator', 'departure_time', 'arrival_time')
    search_fields = ('name', 'operator__name', 'source', 'destination')
    ordering = ('departure_time',)

    def get_total_amount(self, obj):
        # Sum the payment amounts for bookings related to this bus
        total_amount = obj.booking_set.filter(status='active').aggregate(total=Sum('payment__amount'))['total']
        return total_amount if total_amount else Decimal('0.00')
    get_total_amount.short_description = 'Total Amount'

    def get_revenue_after_commission(self, obj):
        total_amount = self.get_total_amount(obj)
        return total_amount - (total_amount * Decimal('0.10'))
    get_revenue_after_commission.short_description = 'Revenue After Commission'
    
@admin.register(BusRoute)
class BusRouteAdmin(admin.ModelAdmin):
    list_display = ('bus', 'boarding_point', 'dropping_point')
    search_fields = ('bus__name', 'boarding_point__name', 'dropping_point__name')

@admin.register(BusStop)
class BusStopAdmin(admin.ModelAdmin):
    list_display = ('name', 'city')
    search_fields = ('name', 'city')

@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    list_display = ('bus', 'seat_number', 'is_available')
    list_filter = ('bus', 'is_available')

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('user', 'bus', 'booked_on', 'status')
    list_filter = ('status', 'booked_on')
    search_fields = ('user__username', 'bus__name')
    ordering = ('-booked_on',)

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('booking', 'amount', 'status', 'payment_date')
    list_filter = ('status', 'payment_date')
    search_fields = ('booking__ticket_id', 'reference')

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('bus', 'user', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('bus__name', 'user__username')

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number')
    search_fields = ('user__username', 'phone_number')
