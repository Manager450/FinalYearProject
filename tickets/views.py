from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.conf import settings
from .models import Bus, Booking, Payment, Review, BusRoute, BusStop, Seat
from .forms import BookingForm, ReviewForm, UserRegistrationForm, BusRouteForm, UserProfileForm
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


def home(request):
    today_date = timezone.now().date()
    return render(request, 'tickets/home.html', {'today_date': today_date})

def search_results(request):
    # Clear past buses
    Bus.clear_past_buses()
    
    if request.method == 'GET':
        source = request.GET.get('source')
        destination = request.GET.get('destination')
        date_str = request.GET.get('travel_date')  # Use 'travel_date' to match the form field name
        
        # Parse date_str to a date object or set to None if invalid
        travel_date = parse_date(date_str) if date_str else None
        
        # If travel_date is None, it means the date was invalid or not provided
        if travel_date is None:
            messages.error(request, "Invalid travel date. Please enter a valid date.")
            return redirect('home')  # Redirect back to the home page or show an error page
        
        # Base query to filter buses by source and destination
        buses = Bus.objects.filter(source=source, destination=destination)
        
        # Further filter by travel date
        buses = buses.filter(departure_time__date=travel_date)
        
        # Filter buses to only those with available seats
        buses = [bus for bus in buses if bus.available_seats() > 0]
        
        # Compute additional attributes for each bus
        for bus in buses:
            bus.travel_duration = (bus.arrival_time - bus.departure_time).total_seconds() // 3600
            bus.seats_available = Seat.objects.filter(bus=bus, is_available=True).count()
            bus.fare = bus.price
        
        # Context for rendering the template
        context = {
            'buses': buses,
            'source': source,
            'destination': destination,
            'date': travel_date,
        }
        
        return render(request, 'tickets/search_results.html', context)
    
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
            print(type(settings))
            return redirect(redirect_url)
             
    else:
        form = BusRouteForm()
        form.fields['boarding_point'].queryset = boarding_points
        form.fields['dropping_point'].queryset = dropping_points
        return render(request, 'tickets/select_boarding_dropping.html', {'form': form, 'bus': bus})

@login_required(login_url='/login/')
def booking_summary(request, bus_id, boarding_point_id, dropping_point_id):
    bus = get_object_or_404(Bus, id=bus_id)
    boarding_point = get_object_or_404(BusStop, id=boarding_point_id)
    dropping_point = get_object_or_404(BusStop, id=dropping_point_id)
    seats = Seat.objects.filter(bus=bus)  # Fetch all seats

    if request.method == 'POST':
        selected_seat_ids = request.POST.getlist('seat_ids')

        if not selected_seat_ids:  # If no seats are selected
            return render(request, 'tickets/booking_summary.html', {
                'bus': bus,
                'boarding_point': boarding_point,
                'dropping_point': dropping_point,
                'seats': seats,
                'error_message': 'Please select at least one seat.'
            })

        selected_seat_ids = [int(seat_id.strip()) for seat_id in selected_seat_ids]
        total_price = bus.price * len(selected_seat_ids)  # Correctly calculate total price

        return redirect('payment',bus_id=bus.id, boarding_point_id=boarding_point_id, dropping_point_id=dropping_point_id, seat_ids=','.join(map(str, selected_seat_ids)), total_price=total_price)

    return render(request, 'tickets/booking_summary.html', {
        'bus': bus,
        'boarding_point': boarding_point,
        'dropping_point': dropping_point,
        'seats': seats
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

    # Retrieve the existing payment object
    existing_payment = Payment.objects.filter(
        booking__bus=bus,
        booking__boarding_point=boarding_point,
        booking__dropping_point=dropping_point,
        booking__user=request.user,
        status='Success'
    ).first()  # Use first() to get the object or None

    if existing_payment:
        messages.error(request, "Payment has already been made for this booking.")
        return redirect('payment_success', payment_id=existing_payment.id)

    if request.method == 'POST':
        phone_number = request.POST.get('phone_number')

        # Create the booking
        booking = Booking.objects.create(
            user=request.user,
            bus=bus,
            boarding_point=boarding_point,
            dropping_point=dropping_point,
        )
        booking.seats.set(seats)

        # Generate the reference
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
            'reference': reference,  # Use the generated reference
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
                status='Pending'  # Initially mark as pending
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
        elif 'send_sms' in request.POST:
            phone_number = request.POST.get('phone_number', booking.user.profile.phone_number)
            
            try:
                formatted_phone_number = format_phone_number(phone_number)
            except ValueError as e:
                messages.error(request, str(e))
                return redirect('payment_success', payment_id=payment_id)
            
            # Ensure send_mticket is called with formatted phone number
            send_mticket(formatted_phone_number, booking)
            messages.success(request, "m-Ticket sent successfully!")

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