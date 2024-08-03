from django.urls import path, register_converter
from .converters import DecimalConverter
from . import views

register_converter(DecimalConverter, 'decimal')

urlpatterns = [
    path('', views.home, name='home'),
    path('search/', views.search_results, name='search_results'),
    path('bus/<int:bus_id>/', views.bus_details, name='bus_details'),
    path('book/', views.book_bus, name='book_bus'),
    path('payment/<int:booking_id>/<decimal:total_price>/', views.payment, name='payment'),
    path('payment_success/<int:payment_id>/', views.payment_success, name='payment_success'),
    path('my_bookings/', views.my_bookings, name='my_bookings'),
    path('booking/<int:booking_id>/', views.booking_details, name='booking_details'),
    path('select-boarding-dropping/<int:bus_id>/', views.select_boarding_dropping_points, name='select_boarding_dropping'),
    path('booking-summary/<int:bus_id>/<int:boarding_point_id>/<int:dropping_point_id>/', views.booking_summary, name='booking_summary'),
    path('register/', views.register, name='register'),
    path('logout/', views.user_logout, name='logout'),
    path('login/', views.user_login, name='login'),
    path('profile/', views.profile, name='profile'),
    path('settings/', views.settings, name='settings'),
    path('about/', views.about, name='about'),
    path('terms/', views.terms, name='terms'),
    path('privacy/', views.privacy, name='privacy'),
    path('help/', views.help_view, name='help'),
    path('faqs/', views.faqs, name='faqs'),
    path('review/<int:bus_id>/', views.review_bus, name='review_bus'),
    path('ajax/boarding-points/', views.get_boarding_points, name='get_boarding_points'),
    path('ajax/dropping-points/', views.get_dropping_points, name='get_dropping_points'),
]
