from django.urls import include, path, register_converter
from .converters import DecimalConverter
from . import views

register_converter(DecimalConverter, 'decimal')

urlpatterns = [
    path('', views.home, name='home'),
    path('search/', views.search_results, name='search_results'),
    path('bus/<int:bus_id>/', views.bus_details, name='bus_details'),
    path('payment/<int:bus_id>/<int:boarding_point_id>/<int:dropping_point_id>/<str:seat_ids>/<decimal:total_price>/', views.payment, name='payment'),
    # path('payment/verify/<str:reference>/', views.verify_payment, name='verify_payment'),
    path('payment_success/<int:payment_id>/', views.payment_success, name='payment_success'),
    path('payment_failed/', views.payment_failed, name='payment_failed'),
    path('my_bookings/', views.my_bookings, name='my_bookings'),
    path('booking/<int:booking_id>/', views.booking_details, name='booking_details'),
    path('clear-booking/<int:booking_id>/', views.clear_booking, name='clear_booking'),
    path('clear-all-bookings/', views.clear_all_bookings, name='clear_all_bookings'),
    path('select-boarding-dropping/<int:bus_id>/', views.select_boarding_dropping_points, name='select_boarding_dropping'),
    path('booking-summary/<int:bus_id>/<int:boarding_point_id>/<int:dropping_point_id>/', views.booking_summary, name='booking_summary'),
    path('cancel-booking/', views.cancel_booking_list, name='cancel_booking_list'),
    path('cancel-booking/<int:booking_id>/', views.cancel_booking, name='cancel_booking'),
    path('download_ticket/<int:booking_id>/', views.download_ticket, name='download_ticket'),
    path('error/', views.error_page, name='error_page'),
    path('register/', views.register, name='register'),
    path('logout/', views.user_logout, name='logout'),
    path('login/', views.user_login, name='login'),
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('profile/change_password/', views.change_password, name='change_password'),  path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('profile/change_password/', views.change_password, name='change_password'),
    path('settings/', views.site_settings, name='settings'),
    path('about/', views.about, name='about'),
    path('terms/', views.terms, name='terms'),
    path('privacy/', views.privacy, name='privacy'),
    path('help/', views.help_view, name='help'),
    path('faqs/', views.faqs, name='faqs'),
    path('review/<int:bus_id>/', views.review_bus, name='review_bus'),
    path('ajax/boarding-points/', views.get_boarding_points, name='get_boarding_points'),
    path('ajax/dropping-points/', views.get_dropping_points, name='get_dropping_points'),
    path('accounts/', include('allauth.urls')),
    path('password-reset/', views.password_reset_request, name='password_reset_request'),
    path('reset-password/', views.password_reset_confirm, name='password_reset_confirm'),
]
