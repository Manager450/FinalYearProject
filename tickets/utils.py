import io
import uuid
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from django.http import FileResponse
import africastalking
from django.conf import settings
import requests
import re
from tickets.models import Booking

def calculate_total_revenue():
    total_revenue = 0
    bookings = Booking.objects.filter(status='active')
    for booking in bookings:
        total_revenue += booking.total_amount()
    return total_revenue

def calculate_busticketx_commission():
    total_revenue = calculate_total_revenue()
    commission_rate = 0.15
    return total_revenue * commission_rate

def format_phone_number(number):
    """
    Format the phone number to international format.
    Assumes Ghanaian numbers start with '0' and need '+233' prefix.
    """
    number = number.strip()
    if number.startswith('0'):
        number = '+233' + number[1:]
    elif not number.startswith('+'):
        # If it's not already international format, prepend '+233'
        number = '+233' + number
    # Basic validation (ensuring the number only contains digits and '+' at the start)
    if not re.match(r'^\+\d+$', number):
        raise ValueError("Invalid phone number format.")
    return number


# Initialize Africastalking SDK
username = settings.AFRICAS_TALKING_USERNAME 
api_key = settings.AFRICAS_TALKING_API_KEY
africastalking.initialize(username, api_key)

def send_sms(phone_number, message):
    try:
        sms = africastalking.SMS

        response = sms.send(message, [phone_number])
        return response
    except Exception as e:
        print(f"An error occurred: {e}")
        return None


def send_mticket(phone_number, booking):
    # Initialize Africa's Talking SDK
    africastalking.initialize(username=settings.AFRICAS_TALKING_USERNAME, api_key=settings.AFRICAS_TALKING_API_KEY)
    
    # Get the SMS service
    sms = africastalking.SMS

    # Extract seat numbers from the booking
    seat_numbers = ', '.join([seat.seat_number for seat in booking.seats.all()])
    
    # Create the message body with detailed information, including the Ticket ID
    message_body = (
        f"Your BusTicketX Ticket\n"
        f"Ticket ID: {booking.ticket_id}\n"
        f"Bus: {booking.bus.name}\n"
        f"Passenger: {booking.user.username}\n"
        f"Seat Numbers: {seat_numbers}\n"
        f"Boarding Point: {booking.boarding_point}\n"
        f"Dropping Point: {booking.dropping_point}\n"
        f"Departure Time: {booking.bus.departure_time}\n"
        f"Arrival Time: {booking.bus.arrival_time}\n"
        f"Thank you for choosing BusTicketX!"
    )
    
    # Send the message
    response = sms.send(message=message_body, recipients=[phone_number])
    
    return response

def generate_ticket(booking):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Define styles
    styles = getSampleStyleSheet()
    normal_style = styles['Normal']
    heading_style = styles['Heading1']
    normal_style.leading = 14  # Adjust line height for better spacing

    # Draw a border around the ticket
    p.setStrokeColor(colors.black)
    p.setLineWidth(2)
    p.rect(50, height - 750, width - 100, 700)

    # Add Logo at the top
    logo_path = "static/images/logo-no-background.png"  # Path to your logo
    logo = ImageReader(logo_path)
    
    # Adjust these values to position and style the logo
    logo_width = 150  # Width of the logo
    logo_height = 75  # Height of the logo
    logo_x = (width - logo_width) / 2  # Center the logo horizontally
    logo_y = height - 100  # Adjust the Y position from the top

    p.drawImage(logo, logo_x, logo_y - logo_height, width=logo_width, height=logo_height)

    # Title
    p.setFont("Helvetica-Bold", 24)
    title_y = logo_y - logo_height - 30
    p.drawString(100, title_y, "Bus Ticket")

    # Ticket ID Section
    p.setFont("Helvetica-Bold", 14)
    ticket_id_y = title_y - 40
    p.drawString(100, ticket_id_y, f"Ticket ID: {booking.ticket_id}")

    # Operator Section
    p.setFont("Helvetica-Bold", 16)
    operator_y = ticket_id_y - 40
    p.drawString(100, operator_y, f"Operator: {booking.bus.operator}")

    # Ticket Information Section
    p.setFont("Helvetica", 14)
    bus_info_y = operator_y - 40
    p.drawString(100, bus_info_y, f"Bus: {booking.bus.name}")
    p.drawString(100, bus_info_y - 20, f"Passenger: {booking.user.username}")

    # Seat Numbers Section
    seat_numbers_y = bus_info_y - 40
    seat_numbers = ", ".join([seat.seat_number for seat in booking.seats.all()])
    p.drawString(100, seat_numbers_y, f"Seat Number(s): {seat_numbers}")

    # Journey Details Section
    journey_details_y = seat_numbers_y - 60
    p.drawString(100, journey_details_y, f"Boarding Point: {booking.boarding_point}")
    p.drawString(100, journey_details_y - 20, f"Dropping Point: {booking.dropping_point}")
    p.drawString(100, journey_details_y - 40, f"Departure: {booking.bus.departure_time}")
    p.drawString(100, journey_details_y - 60, f"Arrival: {booking.bus.arrival_time}")

    # Additional Information Section
    additional_info_y = journey_details_y - 120
    p.drawString(100, additional_info_y, f"Travel Date: {booking.bus.departure_time.strftime('%Y-%m-%d')}")
    p.drawString(100, additional_info_y - 20, "Thank you for booking with BusTicketX!")

    # Terms and Conditions Section
    terms = (
        "Terms & Conditions: This ticket is non-refundable and non-transferable. "
        "Please arrive at the boarding point at least 15 minutes before departure. "
        "BusTicketX is not responsible for any delays due to traffic or other unforeseen circumstances."
    )
    term_style = ParagraphStyle(name='Terms', fontName='Helvetica', fontSize=10, leading=12, alignment=1)
    text = Paragraph(terms, style=term_style)
    text_width = width - 200
    text_x = 100
    text_y = additional_info_y - 80
    
    # Adjust the position of the text to ensure it fits within the ticket border
    text.wrapOn(p, text_width, 100)  # Wrap text to fit within width and height
    text.drawOn(p, text_x, text_y)

    # Save the PDF to the buffer
    p.save()
    buffer.seek(0)
    return buffer
