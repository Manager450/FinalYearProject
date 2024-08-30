from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from django.http import FileResponse
import io 
from twilio.rest import Client
from django.conf import settings
import requests

def send_mticket(phone_number, booking):
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    
    # Extract seat numbers from the booking
    seat_numbers = ', '.join([seat.seat_number for seat in booking.seats.all()])
    
    # Create the message body
    message_body = (
        f"Your ticket for {booking.bus.name}:\n"
        f"Passenger: {booking.user.username}\n"
        f"Seat Numbers: {seat_numbers}\n"
        f"Boarding: {booking.boarding_point}\n"
        f"Dropping: {booking.dropping_point}\n"
        f"Departure: {booking.bus.departure_time}\n"
        f"Arrival: {booking.bus.arrival_time}"
    )
    
    # Send the message
    message = client.messages.create(
        body=message_body,
        from_=settings.TWILIO_PHONE_NUMBER,
        to=phone_number
    )
    
    return message.sid


def generate_ticket(booking):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Add Bus Operator Name
    p.setFont("Helvetica-Bold", 18)
    p.drawString(100, height - 150, f"Operator: {booking.bus.operator}")

    # Ticket Information
    p.setFont("Helvetica", 12)
    p.drawString(100, height - 200, f"Ticket for: {booking.bus.name}")
    p.drawString(100, height - 220, f"Passenger: {booking.user.username}")

    # Seat Numbers
    seat_numbers = ", ".join([seat.seat_number for seat in booking.seats.all()])
    p.drawString(100, height - 240, f"Seat Number(s): {seat_numbers}")

    # Journey Details
    p.drawString(100, height - 260, f"Boarding Point: {booking.boarding_point}")
    p.drawString(100, height - 280, f"Dropping Point: {booking.dropping_point}")
    p.drawString(100, height - 300, f"Departure: {booking.bus.departure_time}")
    p.drawString(100, height - 320, f"Arrival: {booking.bus.arrival_time}")

    # Save the PDF to the buffer
    p.save()
    buffer.seek(0)
    return buffer

def process_mobile_money_payment(phone_number, amount):
    headers = {
        'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}',
        'Content-Type': 'application/json',
    }
    data = {
        'amount': int(amount * 100),  # Convert amount to kobo
        'phone_number': phone_number,
        'email': 'user@example.com',  # Optional
        'currency': 'GHS',
        'payment_type': 'mobilemoneygh'
    }
    response = requests.post('https://api.paystack.co/transaction/initialize', json=data, headers=headers)
    
    print(f"API Response Status Code: {response.status_code}")
    print(f"API Response: {response.json()}")

    if response.status_code == 200:
        response_data = response.json()
        return response_data['status'], response_data['data']
    else:
        response_data = response.json()
        return response_data['status'], response_data['message']
