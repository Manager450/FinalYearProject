from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.conf import settings
from .models import Bus, Booking, Payment, Review, BusRoute, BusStop, Seat, BusOperator
from .forms import BookingForm, ReviewForm, UserRegistrationForm, BusRouteForm, UserProfileForm, ReportForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from datetime import datetime
from django.contrib import messages
from django.utils import timezone
from django.utils.dateparse import parse_date
from .utils import generate_ticket, send_mticket, send_sms, format_phone_number
from django.http import FileResponse, JsonResponse, Http404, HttpResponseRedirect, HttpResponse
from django.core.mail import send_mail
import time
from .paystack import Paystack
import requests
import secrets
from datetime import date
from collections import defaultdict
import logging
from decimal import Decimal, ROUND_HALF_UP
from django.db.models import Sum

def home(request):
    today_date = timezone.now().date()
    return render(request, 'tickets/home.html', {'today_date': today_date})

def search_results(request):
    # Clear past buses
    Bus.clear_past_buses()
    
    if request.method == 'GET':
        source = request.GET.get('source')
        destination = request.GET.get('destination')
        date_str = request.GET.get('travel_date')
        
        # Parse date_str to a date object or set to None if invalid
        travel_date = parse_date(date_str)
        
        if not travel_date:
            messages.error(request, "Invalid travel date.")
            return redirect('home')
        
        # Get buses matching the criteria
        buses = Bus.objects.filter(source=source, destination=destination, departure_time__date=travel_date)
        
        # Organize buses by operator
        operators_data = []
        grouped_buses = defaultdict(list)
        for bus in buses:
            grouped_buses[bus.operator].append(bus)
        
        for operator, buses in grouped_buses.items():
            bus_count = len(buses)
            lowest_fare = min(bus.price for bus in buses)
            operators_data.append({
                'operator': operator,
                'bus_count': bus_count,
                'lowest_fare': lowest_fare,
            })
        
        total_buses = len(buses)
        context = {
            'operators_data': operators_data,
            'source': source,
            'destination': destination,
            'date': travel_date,
            'total_buses': total_buses,
        }
        return render(request, 'tickets/search_results.html', context)


logger = logging.getLogger(__name__)

def operator_buses(request, operator_id):
    operator = get_object_or_404(BusOperator, id=operator_id)
    
    # Fetch query parameters
    source = request.GET.get('source')
    destination = request.GET.get('destination')
    date_str = request.GET.get('travel_date')

    # Log the received parameters for debugging
    logger.debug(f"Operator Buses - Source: {source}, Destination: {destination}, Travel Date: {date_str}")
    print(f"Operator Buses - Source: {source}, Destination: {destination}, Travel Date: {date_str}")
    
    # Validate travel date
    travel_date = parse_date(date_str)
    
    if not travel_date:
        messages.error(request, "Invalid travel date. Please enter a valid date.")
        print("Invalid travel date received:", date_str)
        return redirect('home')

    if not source or not destination:
        messages.error(request, "Missing source or destination.")
        print(f"Missing source or destination - Source: {source}, Destination: {destination}")
        return redirect('home')
    
    # Query the buses for the operator, source, destination, and travel date
    buses = Bus.objects.filter(
        operator_id=operator_id,
        source=source,
        destination=destination,
        departure_time__date=travel_date
    )

    # Log the number of buses found
    logger.debug(f"Buses found for operator {operator_id}: {len(buses)}")
    print(f"Buses found for operator {operator_id}: {len(buses)}")
    
    # Ensure buses have available seats
    buses = [bus for bus in buses if bus.available_seats() > 0]

    for bus in buses:
        bus.travel_duration = (bus.arrival_time - bus.departure_time).total_seconds() // 3600
        bus.seats_available = Seat.objects.filter(bus=bus, is_available=True).count()
        bus.fare = bus.price

    context = {
        'buses': buses,
        'operator': operator,
    }

    return render(request, 'tickets/operator_buses.html', context)
    
def select_boarding_dropping_points(request, bus_id):
    bus = get_object_or_404(Bus, id=bus_id)
    bus_routes = BusRoute.objects.filter(bus=bus)

    boarding_points = BusStop.objects.filter(id__in=bus_routes.values_list('boarding_point', flat=True))
    dropping_points = BusStop.objects.filter(id__in=bus_routes.values_list('dropping_point', flat=True))

    if request.method == 'POST':
        form = BusRouteForm(request.POST)
        if form.is_valid():
            if not request.user.is_authenticated:
                return JsonResponse({'success': False, 'errors': 'Please log in to complete your booking'})

            boarding_point = form.cleaned_data['boarding_point']
            dropping_point = form.cleaned_data['dropping_point']
            redirect_url = reverse('booking_summary', args=[bus_id, boarding_point.id, dropping_point.id])
            return redirect(redirect_url)
    else:
        form = BusRouteForm()
        form.fields['boarding_point'].queryset = boarding_points
        form.fields['dropping_point'].queryset = dropping_points

    return render(request, 'tickets/select_boarding_dropping.html', {'form': form, 'bus': bus})


@login_required(login_url='/login/')
def booking_summary(request, bus_id, boarding_point_id, dropping_point_id):
    # Fetch bus, boarding point, dropping point, and seat information
    bus = get_object_or_404(Bus, id=bus_id)
    boarding_point = get_object_or_404(BusStop, id=boarding_point_id)
    dropping_point = get_object_or_404(BusStop, id=dropping_point_id)
    seats = Seat.objects.filter(bus=bus)  # Fetch all seats for the bus

    # Check if the request method is POST (i.e., form submission)
    if request.method == 'POST':
        # Get selected seat IDs from the form submission
        selected_seat_ids = request.POST.get('seat_ids', '').split(',')
        selected_seat_ids = [int(seat_id.strip()) for seat_id in selected_seat_ids if seat_id.strip()]

        # If no seats are selected, return error message
        if not selected_seat_ids:
            return render(request, 'tickets/booking_summary.html', {
                'bus': bus,
                'boarding_point': boarding_point,
                'dropping_point': dropping_point,
                'seats': seats,
                'error_message': 'Please select at least one seat.'
            })

        # Calculate total price based on the number of selected seats
        total_price = bus.price * len(selected_seat_ids)
        
        # Extract the departure date from the selected bus
        departure_date = bus.departure_time.date()

        # Check if the user already has any bookings on the same date, regardless of bus
        existing_bookings = Booking.objects.filter(
            user=request.user,
            bus__departure_time__date=departure_date
        )
        
        if existing_bookings.exists():
            # If the user has an existing booking on the same date, redirect to booking confirmation page
            return redirect('booking_confirmation', 
                            bus_id=bus_id, 
                            boarding_point_id=boarding_point_id, 
                            dropping_point_id=dropping_point_id,
                            seat_ids=','.join(map(str, selected_seat_ids)),
                            total_price=total_price)
        
        # If no existing bookings, redirect to the payment page
        return redirect('payment', 
                        bus_id=bus_id, 
                        boarding_point_id=boarding_point_id, 
                        dropping_point_id=dropping_point_id, 
                        seat_ids=','.join(map(str, selected_seat_ids)), 
                        total_price=total_price)

    # Handle the GET request to display the booking summary
    return render(request, 'tickets/booking_summary.html', {
        'bus': bus,
        'boarding_point': boarding_point,
        'dropping_point': dropping_point,
        'seats': seats,
    })

@login_required(login_url='/login/')
def booking_confirmation(request, bus_id, boarding_point_id, dropping_point_id, seat_ids, total_price):
    if request.method == 'POST':
        if 'confirm' in request.POST:
            # Redirect to payment page if user confirms the booking
            return redirect('payment', bus_id=bus_id, boarding_point_id=boarding_point_id, dropping_point_id=dropping_point_id, seat_ids=seat_ids, total_price=total_price)
        else:
            # Redirect back to booking summary if user cancels
            return redirect('booking_summary', bus_id=bus_id, boarding_point_id=boarding_point_id, dropping_point_id=dropping_point_id)
    
    return render(request, 'tickets/booking_confirmation.html', {
        'bus_id': bus_id,
        'boarding_point_id': boarding_point_id,
        'dropping_point_id': dropping_point_id,
        'seat_ids': seat_ids,
        'total_price': total_price
    })

@login_required
def cancel_booking_list(request):
    bookings = Booking.objects.filter(user=request.user, status='active')
    return render(request, 'tickets/cancel_booking_list.html', {'bookings': bookings})

login_required
def cancel_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)

    if request.method == "POST":
        # Check if the travel date has passed
        travel_date = booking.bus.departure_time.date()
        if travel_date < timezone.now().date():
            messages.error(request, 'The travel date has passed. Refund is not possible.')
            return redirect('cancel_booking', booking_id=booking.id)

        # Initialize refund process with Paystack
        payment = Payment.objects.get(booking=booking)
        paystack = Paystack()

        headers = {
            'Authorization': f'Bearer {paystack.PAYSTACK_SK}',
            'Content-Type': 'application/json',
        }
        data = {
            'transaction': payment.reference,
            'amount': payment.amount_value(),  # Amount in kobo
        }

        url = paystack.base_url + "refund"
        response = requests.post(url, headers=headers, json=data)
        response_data = response.json()

        if response.status_code == 200 and response_data['status']:
            # Update the booking status to 'cancelled'
            booking.status = 'cancelled'
            booking.save()

            # Free up the seats associated with this booking
            seats = booking.seats.all()
            for seat in seats:
                seat.is_available = True
                seat.save()

            # Mark the payment as refunded
            payment.status = 'Refunded'
            payment.save()

            messages.success(request, 'Your booking has been cancelled successfully. Refund will be processed within 5-7 business days.')

            return render(request, 'tickets/cancel_confirmation.html')
        else:
            messages.error(request, 'Refund failed. Please try again later or contact support.')
            return redirect('cancel_booking', booking_id=booking.id)

    return render(request, 'tickets/cancel_booking.html', {'booking': booking})
        
def bus_details(request, bus_id):
    bus = get_object_or_404(Bus, id=bus_id)
    return render(request, 'tickets/bus_details.html', {'bus': bus})

@login_required
def payment(request, bus_id, boarding_point_id, dropping_point_id, seat_ids, total_price):
    bus = get_object_or_404(Bus, id=bus_id)
    boarding_point = get_object_or_404(BusStop, id=boarding_point_id)
    dropping_point = get_object_or_404(BusStop, id=dropping_point_id)
    seat_ids_list = [int(seat_id) for seat_id in seat_ids.split(',')]
    seats = Seat.objects.filter(id__in=seat_ids_list)
    paystack_public_key = settings.PAYSTACK_PUBLIC_KEY

    existing_payment = Payment.objects.filter(
        booking__bus=bus,
        booking__boarding_point=boarding_point,
        booking__dropping_point=dropping_point,
        booking__user=request.user,
        status='Success'
    ).first()

    if existing_payment:
        messages.error(request, "Payment has already been made for this booking.")
        return redirect('payment_success', payment_id=existing_payment.id)

    if request.method == 'POST':
        phone_number = request.POST.get('phone_number')
        booking_for_self = request.POST.get('booking_for_self')

        if booking_for_self == 'yes':
            booking_user = request.user
            name_on_ticket = None  # Not needed for self-booking

        else:
            other_account = request.POST.get('other_account')

            if other_account == 'yes':
                username = request.POST.get('username')
                try:
                    booking_user = User.objects.get(username=username)
                except User.DoesNotExist:
                    messages.error(request, "User not found.")
                    return redirect('payment', bus_id=bus.id, boarding_point_id=boarding_point.id, dropping_point_id=dropping_point.id, seat_ids=seat_ids, total_price=total_price)

                # Check if the user already has a booking on the same date
                existing_booking = Booking.objects.filter(user=booking_user, bus__departure_time=bus.departure_time).first()

                if existing_booking:
                    messages.warning(request, f"{username} already has a booking with {existing_booking.bus.name} on {existing_booking.bus.departure_time.strftime('%Y-%m-%d')}.")
                    return redirect('payment', bus_id=bus.id, boarding_point_id=boarding_point.id, dropping_point_id=dropping_point.id, seat_ids=seat_ids, total_price=total_price)

                name_on_ticket = None  # Not needed if user has an account

            else:
                booking_user = None  # No user account, so we will just use the name
                name_on_ticket = request.POST.get('name_on_ticket')

        # Create the booking
        booking = Booking.objects.create(
            user=booking_user,
            bus=bus,
            boarding_point=boarding_point,
            dropping_point=dropping_point,
        )
        booking.seats.set(seats)

        # Generate the payment reference
        reference = secrets.token_urlsafe(20)

        # Initialize payment with Paystack
        paystack = Paystack()
        headers = {
            'Authorization': f'Bearer {paystack.PAYSTACK_SK}',
            'Content-Type': 'application/json',
        }
        data = {
            'email': request.user.email,
            'amount': int(total_price * 100),  # Amount in kobo
            'reference': reference,
            'callback_url': request.build_absolute_uri(reverse('verify_payment', args=[reference]))
        }

        url = paystack.base_url + "transaction/initialize/"
        response = requests.post(url, headers=headers, json=data)
        response_data = response.json()

        if response.status_code == 200 and response_data['status']:
            authorization_url = response_data['data']['authorization_url']

            # Save the payment with the same reference
            payment = Payment.objects.create(
                booking=booking,
                amount=total_price,
                reference=reference,
                status='Pending'
            )

            # Mark seats as unavailable (can undo if payment fails)
            for seat in seats:
                seat.is_available = False
                seat.save()

            return redirect(authorization_url)
        else:
            return redirect('payment_failed')

    context = {
        'total_price': total_price,
        'seats': seats,
        'paystack_public_key': paystack_public_key,
        'bus': bus,  # Pass bus details for display
    }

    return render(request, 'tickets/payment.html', context)


@login_required
def verify_payment(request, reference):
    payment = get_object_or_404(Payment, reference=reference)

    if payment.status == 'Pending':
        verified = payment.verify_payment()
        if verified:
            messages.success(request, "Payment successful! Your booking is confirmed.")
            return redirect('payment_success', payment_id=payment.id)
        else:
            # Mark seats as available again if payment failed
            for seat in payment.booking.seats.all():
                seat.is_available = True
                seat.save()
            messages.error(request, "Payment failed or verification unsuccessful.")
            return redirect('payment_failed')

    return redirect('payment_success', payment_id=payment.id)


@login_required
def payment_success(request, payment_id):
    payment = get_object_or_404(Payment, id=payment_id)
    booking = payment.booking

    if request.method == 'POST':
        if 'download' in request.POST:
            buffer = generate_ticket(booking)
            return FileResponse(buffer, as_attachment=True, filename='ticket.pdf')
        
        return redirect('payment_success', payment_id=payment_id)
            
            # Ensure send_mticket is called with formatted phone number

    return render(request, 'tickets/payment_success.html', {'payment': payment, 'booking': booking})



def payment_failed(request):
    return render(request, 'tickets/payment_failed.html', {'message': 'Payment verification failed. Please try again.'})

def error_page(request):
    return render(request, 'tickets/error.html', {'message': 'An error occurred. Please try again.'})

@login_required
def download_ticket(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user, status='active', cleared=False)
    
    if request.method == 'POST':
        buffer = generate_ticket(booking)
        return FileResponse(buffer, as_attachment=True, filename='ticket.pdf')
    
    raise Http404

@login_required
def my_bookings(request):
    active_bookings = Booking.objects.filter(user=request.user, status='active', cleared=False)
    cancelled_bookings = Booking.objects.filter(user=request.user, status='cancelled', cleared=False)
    return render(request, 'tickets/my_bookings.html', {
        'active_bookings': active_bookings,
        'cancelled_bookings': cancelled_bookings,
    })

@login_required
def clear_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user, status='active')
    booking.cleared = True
    booking.save()
    messages.success(request, 'Booking cleared from My Bookings successfully.')
    return redirect('my_bookings')

@login_required
def clear_all_bookings(request):
    Booking.objects.filter(user=request.user).update(cleared=True)
    messages.success(request, 'All bookings cleared from My Bookings successfully.')
    return redirect('my_bookings')

@login_required
def booking_details(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    return render(request, 'tickets/booking_details.html', {'booking': booking})

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.profile.phone_number = form.cleaned_data.get('phone_number')
            user.profile.save()
            login(request, user)
            return redirect('home')
    else:
        form = UserRegistrationForm()
    return render(request, 'tickets/register.html', {'form': form})

def user_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('home')
            else:
                return print("user not found")
            
    else:
        form = AuthenticationForm()
    return render(request, 'tickets/login.html', {'form': form})

def user_logout(request):
    logout(request)
    return redirect('home')

@login_required
def profile(request):
    return render(request, 'tickets/profile.html')

@login_required
def edit_profile(request):
    if request.method == 'POST':
        user_form = UserProfileForm(request.POST, instance=request.user)
        if user_form.is_valid():
            user_form.save()
            user_profile = request.user.profile
            user_profile.phone_number = user_form.cleaned_data.get('phone_number')
            user_profile.save()
            return redirect('profile')
    else:
        user_form = UserProfileForm(instance=request.user)
    
    return render(request, 'tickets/edit_profile.html', {'user_form': user_form})

@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important!
            messages.success(request, 'Your password was successfully updated!')
            return redirect('profile')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, 'tickets/change_password.html', {'form': form})

def about(request):
    return render(request, 'tickets/about.html')

def terms(request):
    return render(request, 'tickets/terms.html')

def privacy(request):
    return render(request, 'tickets/privacy.html')

def help_view(request):
    return render(request, 'tickets/help.html')

def faqs(request):
    return render(request, 'tickets/faqs.html')

def site_settings(request):
    return render(request, 'tickets/settings.html')

@login_required
def review_bus(request, bus_id):
    bus = get_object_or_404(Bus, id=bus_id)
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.bus = bus
            review.user = request.user
            review.save()
            return redirect('bus_details', bus_id=bus.id)
    else:
        form = ReviewForm()
    return render(request, 'tickets/review_bus.html', {'form': form, 'bus': bus})

def get_boarding_points(request):
    source = request.GET.get('source')
    boarding_points = BusStop.objects.filter(city=source)
    data = list(boarding_points.values('id', 'name'))
    return JsonResponse(data, safe=False)

def get_dropping_points(request):
    destination = request.GET.get('destination')
    dropping_points = BusStop.objects.filter(city=destination)
    data = list(dropping_points.values('id', 'name'))
    return JsonResponse(data, safe=False)

# Forgot Password
def password_reset_request(request):
    if request.method == "POST":
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email)
            # Send a simple email with the reset link (in this case, just a direct link)
            reset_url = request.build_absolute_uri(reverse('password_reset_confirm'))
            subject = "Password Reset Requested"
            message = f"Click the link below to reset your password:\n\n{reset_url}"
            send_mail(subject, message, 'from@example.com', [user.email], fail_silently=False)
            messages.success(request, 'Password reset email sent!')
        except User.DoesNotExist:
            messages.error(request, 'No account found with this email.')
        return redirect('login')
    return render(request, 'tickets/password_reset.html')

def password_reset_confirm(request):
    if request.method == "POST":
        email = request.POST.get('email')
        password = request.POST.get('password')
        try:
            user = User.objects.get(email=email)
            user.set_password(password)
            user.save()
            update_session_auth_hash(request, user)  # Keep the user logged in after password change
            messages.success(request, 'Your password has been reset successfully!')
            return redirect('login')
        except User.DoesNotExist:
            messages.error(request, 'No account found with this email.')
    return render(request, 'tickets/password_reset_confirm.html')

def report_view(request):
    operators = BusOperator.objects.all()
    context = {
        'operators': operators
    }
    return render(request, 'tickets/report.html', context)

from django.http import JsonResponse
from .models import Booking, User

def check_user_booking(request):
    username = request.GET.get('username')
    bus_id = request.GET.get('bus_id')
    user = User.objects.filter(username=username).first()
    
    if not user:
        return JsonResponse({'error': 'User not found'}, status=404)

    existing_booking = Booking.objects.filter(user=user, bus__id=bus_id).first()
    
    if existing_booking:
        return JsonResponse({
            'has_booking': True,
            'username': username,
            'bus_name': existing_booking.bus.name,
            'travel_date': existing_booking.bus.departure_time.strftime('%Y-%m-%d')
        })
    
    return JsonResponse({'has_booking': False})


def generate_report_view(request):
    if request.method == 'POST':
        form = ReportForm(request.POST)
        if form.is_valid():
            operator = form.cleaned_data['bus_operator']
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']

            # Filter bookings based on operator and date range
            if operator:
                bookings = Booking.objects.filter(bus__operator=operator, booked_on__range=[start_date, end_date])
            else:
                bookings = Booking.objects.filter(booked_on__range=[start_date, end_date])

            total_revenue = bookings.aggregate(total=Sum('payment__amount'))['total'] or Decimal('0.00')
            total_revenue_after_commission = total_revenue - (total_revenue * Decimal('0.10'))

            # Round amounts to two decimal places
            total_revenue = total_revenue.quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)
            total_revenue_after_commission = total_revenue_after_commission.quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)

            seats_booked = bookings.count()
            seats_unbooked = Seat.objects.filter(bus__operator=operator, is_available=True).count() if operator else 0

            context = {
                'operator': operator,
                'total_revenue': total_revenue,
                'total_revenue_after_commission': total_revenue_after_commission,
                'seats_booked': seats_booked,
                'seats_unbooked': seats_unbooked,
                'start_date': start_date,
                'end_date': end_date,
            }

            return render(request, 'admin/report.html', context)
        else:
            messages.error(request, "There was an error with the form. Please check the inputs.")
    else:
        form = ReportForm()

    return render(request, 'admin/report_form.html', {'form': form})
