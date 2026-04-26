import json
from datetime import datetime, timedelta

from django.contrib.auth.hashers import make_password, check_password
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.urls import reverse_lazy
from django.utils import timezone
import requests

from sat_track.models import UserAccountModel, Event, Observation
from .forms import EventForm, ObservationForm

from skyfield.api import utc


# ---------------------------------------------------------------------------
# HOME
# ---------------------------------------------------------------------------

def home(request):
    if request.method == 'POST':
        form = EventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.timestamp = timezone.make_aware(event.timestamp)
            if request.session.get('user_id'):
                try:
                    event.user = UserAccountModel.objects.get(pk=request.session['user_id'])
                except UserAccountModel.DoesNotExist:
                    pass
            event.save()
            return redirect('event_detail', event_id=event.id)
    else:
        form = EventForm()
    return render(request, 'home.html', {'form': form})


# ---------------------------------------------------------------------------
# EVENT DETAIL (satellite analysis)
# ---------------------------------------------------------------------------

def event_detail(request, event_id):
    event = Event.objects.get(pk=event_id)
    return render(request, 'event_detail.html', {'event': event})


# ---------------------------------------------------------------------------
# USER PROFILE / PANEL
# ---------------------------------------------------------------------------

def user_profile(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('sign_in')

    try:
        user = UserAccountModel.objects.get(pk=user_id)
    except UserAccountModel.DoesNotExist:
        request.session.flush()
        return redirect('sign_in')

    observations = user.observations.all()

    if request.method == 'POST':
        form = ObservationForm(request.POST)
        if form.is_valid():
            obs = form.save(commit=False)
            obs.user = user
            obs.save()
            return redirect('profile')
    else:
        form = ObservationForm()

    return render(request, 'user_profile.html', {
        'user': user,
        'observations': observations,
        'form': form,
    })


def delete_observation(request, obs_id):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('sign_in')
    obs = get_object_or_404(Observation, pk=obs_id, user_id=user_id)
    obs.delete()
    return redirect('profile')


# ---------------------------------------------------------------------------
# OBSERVATION CALENDAR
# ---------------------------------------------------------------------------

def observation_calendar(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('sign_in')
    return render(request, 'observation_calendar.html')


def calendar_events_api(request):
    """JSON endpoint returning observation data for FullCalendar."""
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse([], safe=False)

    observations = Observation.objects.filter(user_id=user_id)
    events = []
    for obs in observations:
        events.append({
            'title': f'{obs.satellite_name}',
            'start': f'{obs.date}T{obs.time}',
            'className': 'fc-event-observation',
            'extendedProps': {
                'lat': obs.latitude,
                'lon': obs.longitude,
                'notes': obs.notes,
                'satellite': obs.satellite_name,
            }
        })

    user_events = Event.objects.filter(user_id=user_id)
    for ev in user_events:
        events.append({
            'title': 'Satellite Analysis',
            'start': ev.timestamp.isoformat(),
            'className': 'fc-event-pass-good',
            'url': f'/event/{ev.id}/',
        })

    return JsonResponse(events, safe=False)


# ---------------------------------------------------------------------------
# LOGOUT
# ---------------------------------------------------------------------------

def user_logout(request):
    request.session.flush()
    return redirect('home')


# ---------------------------------------------------------------------------
# REGISTRATION
# ---------------------------------------------------------------------------

class RegistrationView(View):
    def post(self, request):
        data = json.loads(request.body)
        email = data.get("email")
        username = data.get("username", "")
        password = data.get("password")

        if UserAccountModel.objects.filter(email=email).exists():
            return JsonResponse({
                "status": "error",
                "field": "email",
                "message": "This email is already registered."
            }, status=400)

        hashed_password = make_password(password)
        user = UserAccountModel(
            email=email,
            username=username or email.split('@')[0],
            password=hashed_password,
            provider='local',
        )
        user.save()

        request.session["user_id"] = user.id
        request.session["user_email"] = user.email

        return JsonResponse({
            "status": "success",
            "redirect_url": str(reverse_lazy("profile"))
        })

    def get(self, request):
        return render(request, "registration.html")


# ---------------------------------------------------------------------------
# SIGN IN
# ---------------------------------------------------------------------------

class SignInView(View):
    def post(self, request):
        data = json.loads(request.body)
        email = data.get('email')
        password = data.get('password')

        try:
            user = UserAccountModel.objects.get(email=email)
        except UserAccountModel.DoesNotExist:
            return JsonResponse({
                "status": "error",
                "field": "email",
                "message": "No account found with this email."
            }, status=400)

        if not check_password(password, user.password):
            return JsonResponse({
                "status": "error",
                "field": "password",
                "message": "Incorrect password."
            }, status=400)

        request.session["user_id"] = user.id
        request.session["user_email"] = user.email

        return JsonResponse({
            "status": "success",
            "redirect_url": str(reverse_lazy("profile"))
        })

    def get(self, request):
        return render(request, 'sign_in.html')


# ---------------------------------------------------------------------------
# WEATHER PANEL  (using weatherapi.com – same API as original)
# ---------------------------------------------------------------------------

WEATHER_API_KEY = "0ddb12030aa8441484a95953251704"


def weather_panel(request):
    location_query = request.GET.get("location")

    if not location_query:
        return render(request, "weather_panel.html")

    url = (
        f"http://api.weatherapi.com/v1/forecast.json"
        f"?key={WEATHER_API_KEY}&q={location_query}&days=3&aqi=no&alerts=no"
    )

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.ConnectionError:
        return render(request, "weather_panel.html", {
            "error": "Could not connect to the weather service. Check your internet connection."
        })
    except requests.exceptions.Timeout:
        return render(request, "weather_panel.html", {
            "error": "Weather service timed out. Please try again."
        })
    except Exception as e:
        return render(request, "weather_panel.html", {
            "error": f"Failed to fetch weather data: {e}"
        })

    if "error" in data:
        return render(request, "weather_panel.html", {
            "error": f"Weather API error: {data['error'].get('message', 'Unknown error')}"
        })

    forecast_days = data.get("forecast", {}).get("forecastday", [])

    context = {
        "forecast_days": forecast_days,
        "location": data.get("location", {}),
        "current": data.get("current", {}),
    }
    return render(request, "weather_panel.html", context)


# ---------------------------------------------------------------------------
# WEATHER HELPERS (for satellite–weather analysis)
# ---------------------------------------------------------------------------

def get_weather_for_coordinates(lat, lon, date_str):
    url = (
        f"http://api.weatherapi.com/v1/forecast.json"
        f"?key={WEATHER_API_KEY}&q={lat},{lon}&dt={date_str}&aqi=no&alerts=no"
    )
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Weather fetch error: {e}")
        return None


def analyze_weather_conditions(weather_data):
    if not weather_data:
        return {"score": 0, "description": "No weather data available"}

    if "error" in weather_data:
        return {"score": 0, "description": "Weather API returned an error"}

    if 'forecast' not in weather_data:
        return {"score": 0, "description": "No forecast data available"}

    forecast_days = weather_data['forecast'].get('forecastday', [])
    if not forecast_days:
        return {"score": 0, "description": "No forecast days available"}

    forecast_day = forecast_days[0]['day']

    cloud_cover = forecast_day.get('avgvis_km', 0)
    precip_chance = forecast_day.get('daily_chance_of_rain', 0)
    wind_speed = forecast_day.get('maxwind_kph', 0)

    score = 100
    issues = []

    if cloud_cover < 5:
        score -= 30
        issues.append("Low visibility")
    elif cloud_cover < 10:
        score -= 15
        issues.append("Limited visibility")

    if precip_chance > 70:
        score -= 40
        issues.append("High chance of rain")
    elif precip_chance > 40:
        score -= 20
        issues.append("Moderate chance of rain")

    if wind_speed > 30:
        score -= 25
        issues.append("Strong wind")
    elif wind_speed > 20:
        score -= 10
        issues.append("Moderate wind")

    score = max(0, score)

    if score >= 80:
        description = "Excellent conditions for observation"
    elif score >= 60:
        description = "Good conditions for observation"
    elif score >= 40:
        description = "Moderate conditions for observation"
    else:
        description = "Poor conditions for observation"

    if issues:
        description += f" ({', '.join(issues)})"

    return {
        "score": score,
        "description": description,
        "details": {
            "visibility_km": cloud_cover,
            "rain_chance": precip_chance,
            "wind_speed_kph": wind_speed
        }
    }


def get_area_center_coordinates(geojson_str):
    try:
        geojson_obj = json.loads(geojson_str)
        coordinates = geojson_obj["geometry"]["coordinates"][0]
        lats = [coord[1] for coord in coordinates]
        lons = [coord[0] for coord in coordinates]
        center_lat = sum(lats) / len(lats)
        center_lon = sum(lons) / len(lons)
        # Leaflet can return longitudes outside [-180,180] when user pans the map
        center_lon = ((center_lon + 180) % 360) - 180
        return center_lat, center_lon
    except Exception as e:
        print(f"Area center error: {e}")
        return None, None


def analyze_satellite_weather_match(overpasses, area_geojson):
    center_lat, center_lon = get_area_center_coordinates(area_geojson)
    if not center_lat or not center_lon:
        return []

    weather_cache = {}

    analyzed_passes = []
    for overpass in overpasses:
        try:
            pass_datetime = datetime.fromisoformat(
                overpass['timestamp'].replace('Z', '+00:00')
            )
            date_str = pass_datetime.strftime('%Y-%m-%d')

            if date_str not in weather_cache:
                weather_data = get_weather_for_coordinates(center_lat, center_lon, date_str)
                weather_cache[date_str] = {
                    'raw': weather_data,
                    'analysis': analyze_weather_conditions(weather_data),
                }

            cached = weather_cache[date_str]
            weather_analysis = cached['analysis']

            analyzed_passes.append({
                'overpass': overpass,
                'weather': weather_analysis,
                'weather_raw': cached['raw'],
                'date': date_str,
                'recommendation': weather_analysis['score'] >= 60
            })
        except Exception as e:
            analyzed_passes.append({
                'overpass': overpass,
                'weather': {"score": 0, "description": f"Analysis error: {str(e)}"},
                'weather_raw': None,
                'date': 'unknown',
                'recommendation': False
            })

    return analyzed_passes




from skyfield.api import load, EarthSatellite
import pytz
from concurrent.futures import ThreadPoolExecutor, as_completed

from sat_track.apis import N2YOClient, OPTICAL_SATELLITES, SpectatorClient
from shapely.geometry import shape, Point
from shapely.ops import transform
import pyproj

_shared_timescale = None

def _get_timescale():
    global _shared_timescale
    if _shared_timescale is None:
        _shared_timescale = load.timescale()
    return _shared_timescale


class SatelliteTrajectoryCalculator:
    def __init__(self, sat_id):
        self.sat_id = sat_id
        self.client = N2YOClient(sat_id)
        self.ts = _get_timescale()

    def propagate_trajectory(self, center_date=None, margin_days=3, step_minutes=5):
        tle_data = self.client.fetch_tle()

        if "error" in tle_data:
            return {"error": tle_data["error"]}

        satellite = EarthSatellite(
            tle_data["line1"], tle_data["line2"], tle_data["satname"]
        )

        if center_date is None:
            center_date = datetime.utcnow().replace(tzinfo=utc)
        elif center_date.tzinfo is None:
            center_date = center_date.replace(tzinfo=utc)

        start = center_date - timedelta(days=margin_days)
        end = center_date + timedelta(days=margin_days)
        total_minutes = int((end - start).total_seconds() / 60)
        step_range = [
            start + timedelta(minutes=m)
            for m in range(0, total_minutes, step_minutes)
        ]
        times = self.ts.utc(step_range)

        geocentric = satellite.at(times)
        subpoints = geocentric.subpoint()

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
                "error": f"GeoJSON parse error: {e}",
                "positions_over_area": []
            }

        wgs84 = pyproj.CRS("EPSG:4326")
        metric = pyproj.CRS("EPSG:3857")
        to_meters = pyproj.Transformer.from_crs(
            wgs84, metric, always_xy=True
        ).transform

        polygon_m = transform(to_meters, polygon)
        filtered_positions = []

        for p in positions:
            pt = Point(p["longitude"], p["latitude"])
            pt_m = transform(to_meters, pt)
            distance = pt_m.distance(polygon_m)
            if distance <= footprint_km * 1000:
                filtered_positions.append(p)

        return {
            "positions_over_area": filtered_positions,
            "count": len(filtered_positions)
        }


# ---------------------------------------------------------------------------
# SATELLITE ANALYSIS VIEW  (Spectator passes + TLE ground-track)
# ---------------------------------------------------------------------------

def _geojson_bbox(area_geojson_str):
    """Return (min_lon, min_lat, max_lon, max_lat) bounding box from GeoJSON."""
    try:
        data = json.loads(area_geojson_str)
        lons, lats = [], []

        def _collect(obj):
            if isinstance(obj, list):
                if len(obj) >= 2 and all(isinstance(v, (int, float)) for v in obj[:2]):
                    lons.append(obj[0])
                    lats.append(obj[1])
                else:
                    for item in obj:
                        _collect(item)
            elif isinstance(obj, dict):
                for v in obj.values():
                    _collect(v)

        _collect(data)
        if lons and lats:
            return min(lons), min(lats), max(lons), max(lats)
    except Exception:
        pass
    return None


def _pass_date_distance(analysis, target_date):
    """Absolute day distance between a pass and the user-chosen date."""
    try:
        d = datetime.strptime(analysis['date'], '%Y-%m-%d').date()
        return abs((d - target_date).days)
    except Exception:
        return 999


def sentinel2_over_bbox(request, event_id):
    try:
        event = Event.objects.get(pk=event_id)
    except Event.DoesNotExist:
        return JsonResponse({'error': 'Event not found'}, status=404)

    user_dt = event.timestamp
    user_date = user_dt.date() if hasattr(user_dt, 'date') else user_dt

    center_lat, center_lon = get_area_center_coordinates(event.area_geojson)

    all_overpasses = []
    all_analyzed = []
    all_recommendations = []
    passes_by_date = {}
    satellite_results = []
    errors = []

    for sat_key, sat_info in OPTICAL_SATELLITES.items():
        sat_id = sat_info['norad_id']
        sat_name = sat_info['name']
        swath_km = sat_info['swath_km']

        # --- TLE ground-track: ±3 days around the user-chosen date --------
        calculator = SatelliteTrajectoryCalculator(sat_id)
        trajectory = calculator.propagate_trajectory(
            center_date=user_dt, margin_days=3, step_minutes=5,
        )

        if "error" in trajectory:
            errors.append(f"{sat_name}: {trajectory['error']}")
            continue

        filtered = calculator.filter_over_bbox(
            trajectory["positions"], event.area_geojson,
            footprint_km=swath_km // 2,
        )

        for pos in filtered["positions_over_area"]:
            pos["satellite"] = sat_name
            pos["is_imaging"] = sat_info.get("imaging", False)

        all_overpasses.extend(filtered["positions_over_area"])

        analyzed = analyze_satellite_weather_match(
            filtered["positions_over_area"],
            event.area_geojson,
        )
        for a in analyzed:
            a["satellite"] = sat_name

        all_analyzed.extend(analyzed)

        for analysis in analyzed:
            date = analysis['date']
            if date not in passes_by_date:
                passes_by_date[date] = []
            passes_by_date[date].append(analysis)
            if analysis['recommendation']:
                all_recommendations.append(analysis)

        satellite_results.append({
            "key": sat_key,
            "info": sat_info,
            "trajectory": trajectory,
            "overpasses_count": filtered["count"],
        })

    # Sort recommendations: closest to user-chosen date first
    all_recommendations.sort(key=lambda a: _pass_date_distance(a, user_date))

    # Sort passes_by_date: closest date first
    passes_by_date = dict(
        sorted(passes_by_date.items(),
               key=lambda item: abs((datetime.strptime(item[0], '%Y-%m-%d').date() - user_date).days)
               if item[0] != 'unknown' else 999)
    )

    # --- Spectator.earth overpasses -----------------------------------------
    # Single API call returns all satellite passes over the area with the
    # critical `acquisition` field: True = will image, False = passing only,
    # None = acquisition plan not available for this satellite.

    spectator_overpasses = []
    spectator_error = None
    spectator_frequency = None
    overpasses_by_date = {}

    bbox = _geojson_bbox(event.area_geojson)
    if bbox:
        # Compute how many days before/after today the event falls
        from datetime import date as _date
        today = _date.today()
        event_date_only = user_dt.date() if hasattr(user_dt, 'date') else user_dt
        days_diff = (event_date_only - today).days
        days_before_req = max(0, -days_diff + 3)
        days_after_req = max(7, days_diff + 3)

        sp = SpectatorClient()
        sp_result = sp.fetch_overpasses(
            bbox,
            satellites=SpectatorClient.SUPPORTED_SATELLITES,
            days_before=days_before_req,
            days_after=days_after_req,
        )

        if "error" in sp_result:
            spectator_error = sp_result["error"]
        else:
            spectator_overpasses = sp_result.get("overpasses", [])
            spectator_frequency = sp_result.get("frequency")

        # Sort by date and group by date for display
        spectator_overpasses.sort(key=lambda x: x.get("date", ""))
        for op in spectator_overpasses:
            d = op.get("date_only", "unknown")
            overpasses_by_date.setdefault(d, []).append(op)

    imaging_count = sum(1 for o in spectator_overpasses if o.get("acquisition_status") == "imaging")
    no_image_count = sum(1 for o in spectator_overpasses if o.get("acquisition_status") == "no_image")
    unknown_count = sum(1 for o in spectator_overpasses if o.get("acquisition_status") == "unknown")

    return render(request, "event_detail.html", {
        "event": event,
        "satellite_results": satellite_results,
        "overpasses": all_overpasses,
        "overpasses_count": len(all_overpasses),
        "analyzed_passes": all_analyzed,
        "passes_by_date": passes_by_date,
        "recommendations": all_recommendations,
        "area_geojson": event.area_geojson,
        # Spectator overpasses
        "spectator_overpasses": spectator_overpasses,
        "spectator_count": len(spectator_overpasses),
        "spectator_overpasses_by_date": overpasses_by_date,
        "spectator_frequency": spectator_frequency,
        "spectator_error": spectator_error,
        "imaging_count": imaging_count,
        "no_image_count": no_image_count,
        "unknown_count": unknown_count,
        "errors": errors,
        "user_date": user_date.isoformat(),
    })
