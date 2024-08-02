from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from .models import Bus, Booking, Payment, Review, BusRoute, BusStop, Seat
from .forms import BookingForm, ReviewForm, UserRegistrationForm, BusRouteForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from datetime import datetime
from django.contrib import messages
from .utils import generate_ticket, send_mticket, process_mobile_money_payment
from django.http import FileResponse, JsonResponse


def home(request):
    return render(request, 'tickets/home.html')

def search_results(request):
    if request.method == 'GET':
        source = request.GET.get('source')
        destination = request.GET.get('destination')
        date_str = request.GET.get('date')
        if date_str:
            travel_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        else:
            travel_date = None
        buses = Bus.objects.filter(source=source, destination=destination)
        if travel_date:
            buses = buses.filter(departure_time__date=travel_date)

        buses = [bus for bus in buses if bus.available_seats() > 0]  
        context = {
                    'buses' : buses,
                    'source': source,
                    'destination': destination,
                    'date' : travel_date,
                }
            
        for bus in buses:
            bus.travel_duration = (bus.arrival_time - bus.departure_time).total_seconds() // 3600
            bus.seats_available = Seat.objects.filter(bus=bus, is_available=True).count()
            bus.fare = bus.price


        return render(request, 'tickets/search_results.html', context)

def select_boarding_dropping_points(request, bus_id):
    bus = get_object_or_404(Bus, id=bus_id)
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
        form.fields['boarding_point'].queryset = BusStop.objects.filter(city=bus.source)
        form.fields['dropping_point'].queryset = BusStop.objects.filter(city=bus.destination)
        return render(request, 'tickets/select_boarding_dropping.html', {'form': form, 'bus': bus})

@login_required(login_url='/login/')
def booking_summary(request, bus_id, boarding_point_id, dropping_point_id):
    bus = get_object_or_404(Bus, id=bus_id)
    boarding_point = get_object_or_404(BusStop, id=boarding_point_id)
    dropping_point = get_object_or_404(BusStop, id=dropping_point_id)
    seats = Seat.objects.filter(bus=bus, is_available=True)
    
    if request.method == 'POST':
        selected_seat_ids = request.POST.getlist('seat_ids')
        selected_seat_ids = [int(seat_id.strip()) for seat_id in selected_seat_ids]
        total_price = bus.price * len(selected_seat_ids)
        
        booking = Booking.objects.create(
            user=request.user,
            bus=bus,
            boarding_point=boarding_point,
            dropping_point=dropping_point
        )
        
        for seat_id in selected_seat_ids:
            seat = get_object_or_404(Seat, id=seat_id)
            booking.seats.add(seat)
            seat.is_available = False
            seat.save()
        
        return redirect('payment', booking_id=booking.id, total_price=total_price)
    
    return render(request, 'tickets/booking_summary.html', {'bus': bus, 'boarding_point': boarding_point, 'dropping_point': dropping_point, 'seats': seats})

def bus_details(request, bus_id):
    bus = get_object_or_404(Bus, id=bus_id)
    return render(request, 'tickets/bus_details.html', {'bus': bus})

@login_required
def book_bus(request, bus_id):
    bus = get_object_or_404(Bus, id=bus_id)
    if request.method == 'POST':
        form = BookingForm(request.POST)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.user = request.user
            booking.bus = bus
            booking.save()
            return redirect('payment', booking_id=booking.id)
    else:
        form = BookingForm()
    return render(request, 'tickets/book_bus.html', {'form': form, 'bus': bus})

@login_required
def payment(request, booking_id, total_price):
    booking = get_object_or_404(Booking, id=booking_id)
    
    if request.method == 'POST':
        # Process Mobile Money Payment
        phone_number = request.POST.get('phone_number')
        payment_status = process_mobile_money_payment(phone_number, total_price)
        
        if payment_status == 'Success':
            Payment.objects.create(booking=booking, amount=total_price, status='Success')
            return redirect('payment_success', payment_id=booking.payment.id)
        else:
            messages.error(request, 'Payment failed. Please try again.')
    
    return render(request, 'tickets/payment.html', {'booking': booking, 'total_price': total_price})


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
            send_mticket(phone_number, booking)
            messages.success(request, "m-Ticket sent successfully!")

    return render(request, 'tickets/payment_success.html', {'payment': payment, 'booking': booking})

@login_required
def my_bookings(request):
    bookings = Booking.objects.filter(user=request.user)
    return render(request, 'tickets/my_bookings.html', {'bookings': bookings})

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
        form = AuthenticationForm()
    return render(request, 'tickets/login.html', {'form': form})

def user_logout(request):
    logout(request)
    return redirect('home')

@login_required
def profile(request):
    return render(request, 'tickets/profile.html')

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

def settings(request):
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

