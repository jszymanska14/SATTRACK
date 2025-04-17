from django import forms
from .models import Event
from datetime import datetime

class EventForm(forms.ModelForm):
    date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='Data'
    )
    time = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time'}),
        label='Godzina'
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






