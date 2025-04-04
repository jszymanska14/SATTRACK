from django.shortcuts import render
from .forms import SatelliteForm

def home_view(request):
    return render(request, 'sat_track/home.html')

def satellite_input_view(request):
    if request.method == 'POST':
        form = SatelliteForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            return render(request, 'sat_track/result.html', {'data': data})
    else:
        form = SatelliteForm()
    return render(request, 'sat_track/form.html', {'form': form})
