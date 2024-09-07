from django import forms
from .models import Booking, Review, BusStop, BusOperator
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError

class BusRouteForm(forms.Form):
    boarding_point = forms.ModelChoiceField(queryset=BusStop.objects.all(), label="Boarding Point")
    dropping_point = forms.ModelChoiceField(queryset=BusStop.objects.all(), label="Dropping Point")

class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ['seats']

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

class UserProfileForm(forms.ModelForm):
    phone_number = forms.CharField(max_length=15, required=False)

    class Meta:
        model = User
        fields = ['username', 'email']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError('Email addresses must be unique.')
        return email
    
class ReportForm(forms.Form):
    bus_operator = forms.ModelChoiceField(queryset=BusOperator.objects.all(), required=True)
    
    # Use the DateInput widget with a calendar
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={
                'type': 'date',
                'class': 'form-control',  # Optional: add Bootstrap or custom styling
            }
        )
    )
    
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={
                'type': 'date',
                'class': 'form-control',  # Optional: add Bootstrap or custom styling
            }
        )
    )