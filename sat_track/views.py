import json
from datetime import datetime
from turtle import shape
from django.contrib.auth import authenticate, login
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth.views import LoginView
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View
from django.views.generic import CreateView
from .forms import EventForm
from django.urls import reverse_lazy
from django.shortcuts import redirect
import requests
from sat_track.models import UserAccountModel, Event
from django.http import JsonResponse
from sat_track.models import Event
from django.http import JsonResponse
from sat_track.models import Event
from django.utils import timezone
from skyfield.api import utc


def home(request):
    if request.method == 'POST':
        form = EventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)

            event.timestamp = timezone.make_aware(event.timestamp)

            event.save()
            return redirect('event_detail', event_id=event.id)
    else:
        form = EventForm()
    return render(request, 'home.html', {'form': form})

def event_detail(request, event_id):
    event = Event.objects.get(pk=event_id)
    return render(request, 'event_detail.html', {'event': event})

#TODO dać to gdzieś sensownie pewnie do klasy USER?
def user_profile(request):
    return render(request, 'user_profile.html')

def user_logout(request):
    request.session.flush()  # clear all session data
    return redirect('home')  # or 'home' if you'd prefer



class RegistrationView(View):
    def post(self, request):
        data = json.loads(request.body)
        email = data.get("email")
        password = data.get("password")
        confirm_password = data.get("confirm_password")

        if UserAccountModel.objects.filter(email=email).exists():
            return JsonResponse({
                "status": "error",
                "field": "email",
                "message": "Ten e-mail jest już zarejestrowany."
            }, status=400)

        hashed_password = make_password(password)
        user = UserAccountModel(email=email, password=hashed_password)
        user.save()

        request.session["user_id"] = user.id
        request.session["user_email"] = user.email

        return JsonResponse({
            "status": "success",
            "redirect_url": str(reverse_lazy("profile"))
        })

    def get(self, request):
        return render(request, "registration.html")

class SignInView(View):
    def post(self, request):
            data = json.loads(request.body)
            print("DEBUG DATA:", data)

            email = data.get('email')
            password = data.get('password')

            try:
                user = UserAccountModel.objects.get(email=email)
            except UserAccountModel.DoesNotExist:
                return JsonResponse({
                    "status": "error",
                    "field": "email",
                    "message": "Nie znaleziono użytkownika o podanym adresie e-mail."
                }, status=400)

            if not check_password(password, user.password):
                return JsonResponse({
                    "status": "error",
                    "field": "password",
                    "message": "Nieprawidłowe hasło."
                }, status=400)

            # Simulate a session manually
            request.session["user_id"] = user.id
            request.session["user_email"] = user.email

            return JsonResponse({
                "status": "success",
                "redirect_url": str(reverse_lazy("profile"))
            })



    def get(self, request):

        # Just render the HTML page for non-AJAX GET requests
        return render(request, 'sign_in.html')

    def create_event(request):
        if request.method == 'POST':
            form = EventForm(request.POST)
            if form.is_valid():
                form.save()
                return redirect('success')
        else:
            form = EventForm()
        return render(request, 'event_form.html', {'form': form})


def weather_panel(request):
    location_query = request.GET.get("location")

    if not location_query:
        return render(request, "weather_panel.html", {
            "error": "Podaj lokalizację, aby wyświetlić pogodę."
        })

    api_key = "0ddb12030aa8441484a95953251704"
    url = f"http://api.weatherapi.com/v1/forecast.json?key={api_key}&q={location_query}&days=3&aqi=no&alerts=no"

    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        return render(request, "weather_panel.html", {
            "error": f"Nie udało się pobrać danych pogodowych: {e}"
        })

    forecast_days = data.get("forecast", {}).get("forecastday", [])

    context = {
        "forecast_days": forecast_days,
        "location": data.get("location", {}),
        "current": data.get("current", {}),
    }

    return render(request, "weather_panel.html", context)


# sat_track/apis/skyfield_orbit.py
from datetime import datetime, timedelta
from skyfield.api import load, EarthSatellite
import pytz
from sat_track.apis import N2YOTLEFetcher
from shapely.geometry import shape, Point
from shapely.ops import transform
import pyproj


class SatelliteTrajectoryCalculator:
    def __init__(self, sat_id):
        self.sat_id = sat_id
        self.ts = load.timescale()

    def propagate_trajectory(self, days=14, step_minutes=1):
        tle_data = N2YOTLEFetcher(self.sat_id).fetch_tle()

        if "error" in tle_data:
            return {"error": tle_data["error"]}

        satellite = EarthSatellite(tle_data["line1"], tle_data["line2"], tle_data["satname"])

        # Startowy czas z UTC
        start = datetime.utcnow().replace(tzinfo=utc)
        step_range = [start + timedelta(minutes=m) for m in range(0, days * 24 * 60, step_minutes)]
        times = self.ts.utc(step_range)

        # Oblicz trajektorię
        geocentric = satellite.at(times)
        subpoints = geocentric.subpoint()

        # Zbierz wyniki
        results = []
        for i, time in enumerate(step_range):
            longitude = subpoints.longitude.degrees[i]
            if longitude < 0:
                longitude += 360

            results.append({
                "timestamp": time.isoformat(),
                "latitude": subpoints.latitude.degrees[i],
                "longitude": longitude,
                "altitude_km": subpoints.elevation.km[i]
            })

        return {
            "satellite": tle_data["satname"],
            "sat_id": self.sat_id,
            "positions": results
        }

    def filter_over_bbox(self, positions, geojson_str, footprint_km=145):
        try:
            geojson_obj = json.loads(geojson_str)
            polygon = shape(geojson_obj["geometry"])
        except Exception as e:
            return {
                "error": f"Błąd odczytu GeoJSON: {e}",
                "positions_over_area": []
            }

        # Konwersja do układu metrycznego (Web Mercator)
        wgs84 = pyproj.CRS("EPSG:4326")
        metric = pyproj.CRS("EPSG:3857")
        to_meters = pyproj.Transformer.from_crs(wgs84, metric, always_xy=True).transform

        # Przekształć polygon do układu metrycznego
        polygon_m = transform(to_meters, polygon)

        filtered_positions = []

        for p in positions:
            # Punkt w WGS84
            pt = Point(p["longitude"], p["latitude"])
            # Punkt satelity w metrach
            pt_m = transform(to_meters, pt)
            # Oblicz odległość między punktem a polygonem
            distance = pt_m.distance(polygon_m)  # w metrach

            if distance <= footprint_km * 1000:
                filtered_positions.append(p)

        return {
            "positions_over_area": filtered_positions,
            "count": len(filtered_positions)
        }


from django.shortcuts import render
from django.http import JsonResponse
from sat_track.models import Event

def sentinel2_over_bbox(request, event_id):
    try:
        event = Event.objects.get(pk=event_id)
    except Event.DoesNotExist:
        return JsonResponse({'error': 'Nie znaleziono wydarzenia'}, status=404)

    sentinel_id = 40697  # Sentinel-2A
    calculator = SatelliteTrajectoryCalculator(sentinel_id)

    trajectory = calculator.propagate_trajectory(days=30)

    if "error" in trajectory:
        return render(request, "event_detail.html", {
            "event": event,
            "error": trajectory["error"]
        })

    filtered = calculator.filter_over_bbox(trajectory["positions"], event.area_geojson)

    return render(request, "event_detail.html", {
        "event": event,
        "trajectory": trajectory,
        "overpasses": filtered["positions_over_area"],
        "overpasses_count": filtered["count"]
    })
