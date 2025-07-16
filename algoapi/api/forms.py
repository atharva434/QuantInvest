from django import forms
from .models import UserAccounts, Expiry_Stock, Stock
from django.contrib.auth.models import User
from datetime import date

class UserInfo(forms.ModelForm):
    password = forms.CharField(widget = forms.PasswordInput()) #hash out the password
    
    class Meta():
        model = User
        fields = ('username','password')

class StockForm(forms.ModelForm):
    class Meta:
        model = Stock
        fields = '__all__'

class ClientRegistrationForm(forms.ModelForm):
    class Meta:
        model = UserAccounts
        fields = ['acc_name','acc_provider', 'app_key', 'secret_key']

class ClientRegistrationFrontendForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput())
    acc_name = forms.CharField()
    acc_provider = forms.CharField()
    app_key = forms.CharField()
    secret_key = forms.CharField()

class Expiry_StockForm(forms.ModelForm):
    class Meta:
        model = Expiry_Stock
        fields = '__all__'
        widgets = {
            'expiry_date': forms.DateInput(
                attrs={
                    'type': 'date',
                    'class': 'form-control',   # Bootstrap styling
                    'style': 'max-width: 150px;'  # Keeps it compact
                }
            ),
        }

class ExpiryForm(forms.Form):
    month = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    expiry_type = forms.ChoiceField(choices=[('weekly', 'Weekly'), ('monthly', 'Monthly')])
    expiry_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))


class WeeklyExpiryForm(forms.Form):
    expiry_date = forms.DateField(widget=forms.SelectDateWidget, initial=date.today)
    month = forms.CharField(max_length=20)