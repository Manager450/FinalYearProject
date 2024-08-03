from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from django.http import FileResponse
import io 
from twilio.rest import Client
from django.conf import settings

def send_mticket(phone_number, booking):
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    message = client.messages.create(
        body=f"Your ticket for {booking.bus.name}:\nPassenger: {booking.user.username}\nSeat Number: {booking.seat_number}\nBoarding: {booking.boarding_point}\nDropping: {booking.dropping_point}\nDeparture: {booking.bus.departure_time}\nArrival: {booking.bus.arrival_time}",
        from_=settings.TWILIO_PHONE_NUMBER,
        to=phone_number
    )
    return message.sid


def generate_ticket(booking):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    p.drawString(100, 750, f"Ticket for {booking.bus.name}")
    p.drawString(100, 730, f"Passenger: {booking.user.username}")
    p.drawString(100, 710, f"Seat Number: {booking.seats}")
    p.drawString(100, 690, f"Boarding Point: {booking.boarding_point}")
    p.drawString(100, 670, f"Dropping Point: {booking.dropping_point}")
    p.drawString(100, 650, f"Departure: {booking.bus.departure_time}")
    p.drawString(100, 630, f"Arrival: {booking.bus.arrival_time}")
    p.save()
    buffer.seek(0)
    return buffer

def process_mobile_money_payment(phone_number, amount):
    # Placeholder for mobile money payment integration
    # Implement the API call to your mobile money provider here
    # Example: Call MTN MoMo API and return the status
    # For now, we will assume the payment is always successful
    return 'Success'
