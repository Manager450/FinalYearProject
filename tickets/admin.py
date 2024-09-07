from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import reverse
from django.db import models
from django.db.models import Sum, F, DecimalField, Case, When, Count
from django.template.response import TemplateResponse
from django import forms
from .models import BusOperator, Bus, BusRoute, BusStop, Seat, Booking, Payment, Review, Profile
from decimal import Decimal



# Admin class for BusOperator
class BusOperatorAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_info', 'total_revenue', 'revenue_after_commission', 'seats_booked')
    search_fields = ('name',)

    # Display total revenue
    def total_revenue(self, obj):
        return obj.total_revenue
    total_revenue.admin_order_field = 'total_revenue'

    # Calculate and display revenue after commission
    def revenue_after_commission(self, obj):
        if obj.total_revenue:
            return obj.total_revenue - (obj.total_revenue * Decimal('0.10'))
        return Decimal('0.00')
    revenue_after_commission.admin_order_field = 'revenue_after_commission'

    # Display the number of seats booked
    def seats_booked(self, obj):
        return obj.seats_booked
    seats_booked.admin_order_field = 'seats_booked'

    # Customize the queryset to include total revenue and booked seats
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            total_revenue=Sum(Case(
                When(bus__booking__status='active', then=F('bus__price')),
                output_field=DecimalField(),
            )),
            seats_booked=Count(
                'bus__booking__seats',
                filter=models.Q(bus__booking__status='active')
            )
        )
        return queryset

    def generate_report(self, request, queryset, extra_context=None):
        return redirect(reverse('generate_report')) 

    generate_report.short_description = 'Generate Report'

    # Add the generate report action to the admin actions
    def get_actions(self, request):
        actions = super().get_actions(request)
        actions['generate_report'] = (self.generate_report, 'generate_report', self.generate_report.short_description)
        return actions



# Admin class for Bus
class BusAdmin(admin.ModelAdmin):
    list_display = ('name', 'operator', 'departure_time', 'arrival_time', 'price', 'total_seats', 'get_total_amount', 'get_revenue_after_commission')
    list_filter = ('operator', 'departure_time', 'arrival_time')
    search_fields = ('name', 'operator__name', 'source', 'destination')
    ordering = ('departure_time',)

    # Calculate the total amount from bookings
    def get_total_amount(self, obj):
        total_amount = obj.booking_set.filter(status='active').aggregate(total=Sum('payment__amount'))['total']
        return total_amount if total_amount else Decimal('0.00')
    get_total_amount.short_description = 'Total Amount'

    # Calculate revenue after commission
    def get_revenue_after_commission(self, obj):
        total_amount = self.get_total_amount(obj)
        return total_amount - (total_amount * Decimal('0.10'))
    get_revenue_after_commission.short_description = 'Revenue After Commission'


# Admin class for BusRoute
class BusRouteAdmin(admin.ModelAdmin):
    list_display = ('bus', 'boarding_point', 'dropping_point')
    search_fields = ('bus__name', 'boarding_point__name', 'dropping_point__name')


# Admin class for BusStop
class BusStopAdmin(admin.ModelAdmin):
    list_display = ('name', 'city')
    search_fields = ('name', 'city')


# Admin class for Seat
class SeatAdmin(admin.ModelAdmin):
    list_display = ('bus', 'seat_number', 'is_available')
    list_filter = ('bus', 'is_available')


# Admin class for Booking
class BookingAdmin(admin.ModelAdmin):
    list_display = ('user', 'bus', 'booked_on', 'status')
    list_filter = ('status', 'booked_on')
    search_fields = ('user__username', 'bus__name')
    ordering = ('-booked_on',)


# Admin class for Payment
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('booking', 'amount', 'status', 'payment_date')
    list_filter = ('status', 'payment_date')
    search_fields = ('booking__ticket_id', 'reference')


# Admin class for Review
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('bus', 'user', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('bus__name', 'user__username')


# Admin class for Profile
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number')
    search_fields = ('user__username', 'phone_number')


# Register all the models with their corresponding admin classes
admin.site.register(BusOperator, BusOperatorAdmin)
admin.site.register(Bus, BusAdmin)
admin.site.register(BusRoute, BusRouteAdmin)
admin.site.register(BusStop, BusStopAdmin)
admin.site.register(Seat, SeatAdmin)
admin.site.register(Booking, BookingAdmin)
admin.site.register(Payment, PaymentAdmin)
admin.site.register(Review, ReviewAdmin)
admin.site.register(Profile, ProfileAdmin)
