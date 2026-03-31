from django import forms
from .models import Event, Observation
from datetime import datetime


class EventForm(forms.ModelForm):
    date = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control',
        }),
        label='Date'
    )
    time = forms.TimeField(
        widget=forms.TimeInput(attrs={
            'type': 'time',
            'class': 'form-control',
        }),
        label='Time'
    )

    class Meta:
        model = Event
        fields = ['area_geojson']
        widgets = {
            'area_geojson': forms.HiddenInput(),
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        date = self.cleaned_data.get('date')
        time = self.cleaned_data.get('time')
        instance.timestamp = datetime.combine(date, time)
        if commit:
            instance.save()
        return instance


class ObservationForm(forms.ModelForm):
    class Meta:
        model = Observation
        fields = ['latitude', 'longitude', 'date', 'time', 'satellite_name', 'notes']
        widgets = {
            'latitude': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. 50.0647',
                'step': 'any',
            }),
            'longitude': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. 19.9450',
                'step': 'any',
            }),
            'date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
            }),
            'time': forms.TimeInput(attrs={
                'type': 'time',
                'class': 'form-control',
            }),
            'satellite_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. ISS, Sentinel-2A, Starlink',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Additional notes about this observation...',
                'rows': 3,
            }),
        }
