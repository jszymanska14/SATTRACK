from django import forms
from .models import Event, Observation, MeasurementPlan
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


class MeasurementPlanForm(forms.ModelForm):
    class Meta:
        model = MeasurementPlan
        fields = ['name', 'crop_type', 'season_year', 'area_geojson', 'fields_json', 'home_lat', 'home_lon', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Wheat fields south region 2026',
            }),
            'crop_type': forms.Select(attrs={'class': 'form-control'}),
            'season_year': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 2020, 'max': 2035,
            }),
            'area_geojson': forms.HiddenInput(),
            'fields_json': forms.HiddenInput(),
            'home_lat': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. 50.065',
                'step': 'any',
            }),
            'home_lon': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. 19.945',
                'step': 'any',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Additional notes about this measurement campaign plan…',
                'rows': 3,
            }),
        }


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
