from django import forms
from .models import Event
from datetime import datetime

from django import forms
from .models import Event

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['timestamp', 'area_geojson']
        widgets = {
            'timestamp': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'area_geojson': forms.HiddenInput(),
        }





