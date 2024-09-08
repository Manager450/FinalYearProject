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
    bus_operator = forms.ModelChoiceField(
        queryset=BusOperator.objects.none(),  # Initially empty, will be dynamically filled in the view
        required=False  # Only required for superusers
    )

    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={
                'type': 'date',
                'class': 'form-control',
            }
        )
    )

    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={
                'type': 'date',
                'class': 'form-control',
            }
        )
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Superuser sees all bus operators
        if user and user.is_superuser:
            self.fields['bus_operator'].queryset = BusOperator.objects.all()
            self.fields['bus_operator'].required = True
        # Bus operators don't need to select a bus operator, it's set automatically
        elif user and hasattr(user, 'bus_operator'):
            self.fields.pop('bus_operator')  # Remove the field for bus operators
