from django import forms
from django.utils.timezone import now

class SatelliteForm(forms.Form):
    date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='Date'
    )
    time = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time'}),
        label='Time'
    )
    latitude = forms.FloatField(label='Latitude')
    longitude = forms.FloatField(label='Longitude')


