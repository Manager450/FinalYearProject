from django import forms
from .models import Booking, Review, BusStop
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError

class BusRouteForm(forms.Form):
    boarding_point = forms.ModelChoiceField(
        queryset=BusStop.objects.none(),
        widget=forms.RadioSelect,
        empty_label="Select Boarding Point"
    )
    dropping_point = forms.ModelChoiceField(
        queryset=BusStop.objects.none(),
        widget=forms.RadioSelect,
        empty_label="Select Dropping Point"
    )

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