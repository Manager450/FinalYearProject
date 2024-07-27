from django import forms
from .models import Booking, Review, BusStop
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

class BusRouteForm(forms.Form):
    boarding_point = forms.ModelChoiceField(queryset=BusStop.objects.none(), widget=forms.RadioSelect)
    dropping_point = forms.ModelChoiceField(queryset=BusStop.objects.none(), widget=forms.RadioSelect)
    class Meta:
        model = Booking
        fields = ['boarding_point','dropping_point']
   
class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ['seat_number']

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    phone_number = forms.CharField(max_length=15, required=True)
    class Meta:
        model = User
        fields = ['username', 'phone_number', 'email', 'password1', 'password2']
