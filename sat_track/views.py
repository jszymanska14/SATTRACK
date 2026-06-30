import io
import json
import math
import struct
from datetime import datetime, timedelta

import numpy as np
from django.contrib.auth.hashers import make_password, check_password
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
import requests

from sat_track.models import UserAccountModel, Event, Observation, MeasurementPlan
from .forms import EventForm, ObservationForm, MeasurementPlanForm

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
                'recommendation': weather_analysis['score'] >= 60,
                'is_imaging': overpass.get('is_imaging', False),
                'category': overpass.get('category', ''),
                'acquisition_status': 'unknown',
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

from sat_track.apis import (
    N2YOClient, OPTICAL_SATELLITES, SpectatorClient,
    build_phases_with_dates,
    generate_satellite_calendar_for_season,
    IMGWClient,
)
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


def _normalize_satellite_name(name):
    return (name or '').strip().lower().replace(' ', '-').replace('_', '-')


def _parse_pass_timestamp(timestamp_str):
    if not timestamp_str:
        return None
    try:
        return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
    except Exception:
        return None


def _attach_spectator_acquisition(analyzed_passes, spectator_overpasses, max_delta_minutes=25):
    """
    Match TLE-derived pass points with Spectator overpasses and set
    acquisition_status on each analysis (imaging / no_image / unknown).
    """
    if not analyzed_passes:
        return

    sp_by_sat = {}
    sp_by_sat_date = {}
    for op in spectator_overpasses or []:
        sat_key = _normalize_satellite_name(op.get('satellite'))
        sp_by_sat.setdefault(sat_key, []).append(op)
        date_key = (sat_key, op.get('date_only', ''))
        sp_by_sat_date.setdefault(date_key, []).append(op)

    for analysis in analyzed_passes:
        sat_key = _normalize_satellite_name(analysis.get('satellite'))
        pass_time = _parse_pass_timestamp(analysis.get('overpass', {}).get('timestamp'))
        pass_date = analysis.get('date', '')
        best_status = 'unknown'
        best_delta = None

        for op in sp_by_sat.get(sat_key, []):
            op_time = _parse_pass_timestamp(op.get('date'))
            if not pass_time or not op_time:
                continue
            delta_min = abs((pass_time - op_time).total_seconds()) / 60
            if delta_min <= max_delta_minutes and (best_delta is None or delta_min < best_delta):
                best_delta = delta_min
                best_status = op.get('acquisition_status', 'unknown')

        # Fallback: one Spectator pass for this satellite on this date
        if best_status == 'unknown' and pass_date:
            day_ops = sp_by_sat_date.get((sat_key, pass_date), [])
            if len(day_ops) == 1:
                best_status = day_ops[0].get('acquisition_status', 'unknown')
            elif len(day_ops) > 1 and pass_time:
                for op in day_ops:
                    op_time = _parse_pass_timestamp(op.get('date'))
                    if not op_time:
                        continue
                    delta_min = abs((pass_time - op_time).total_seconds()) / 60
                    if best_delta is None or delta_min < best_delta:
                        best_delta = delta_min
                        best_status = op.get('acquisition_status', 'unknown')

        analysis['acquisition_status'] = best_status


def _is_sentinel2_satellite(name):
    return _normalize_satellite_name(name).startswith('sentinel-2')


def _apply_sentinel2_imaging_fallback(analyzed_passes):
    """
    Spectator often omits Sentinel-2 acquisition plans on the free API tier.
    TLE passes already filtered to the user AOI and swath are treated as imaging.
    """
    for analysis in analyzed_passes:
        if analysis.get('acquisition_status') != 'unknown':
            continue
        if not _is_sentinel2_satellite(analysis.get('satellite')):
            continue
        analysis['acquisition_status'] = 'imaging'


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
            pos["category"] = sat_info.get("category", "")

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

    _attach_spectator_acquisition(all_analyzed, spectator_overpasses)
    _apply_sentinel2_imaging_fallback(all_analyzed)

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


# ===========================================================================
# MEASUREMENT PLANNING MODULE
# ===========================================================================

import math as _math


def _haversine(lat1, lon1, lat2, lon2):
    """Distance in km between two (lat, lon) points."""
    R = 6371.0
    dlat = _math.radians(lat2 - lat1)
    dlon = _math.radians(lon2 - lon1)
    a = (_math.sin(dlat / 2) ** 2
         + _math.cos(_math.radians(lat1)) * _math.cos(_math.radians(lat2))
         * _math.sin(dlon / 2) ** 2)
    return R * 2 * _math.asin(_math.sqrt(max(0, a)))


def _plan_bbox(plan):
    """Return (min_lon, min_lat, max_lon, max_lat) bounding box from a MeasurementPlan."""
    lons, lats = [], []
    if plan.area_geojson:
        bbox = _geojson_bbox(plan.area_geojson)
        if bbox:
            return bbox
    fields = plan.get_fields()
    if fields:
        lats = [f['lat'] for f in fields]
        lons = [f['lon'] for f in fields]
        pad = 0.15
        return min(lons) - pad, min(lats) - pad, max(lons) + pad, max(lats) + pad
    # Default: small box around central Poland
    return 19.5, 51.5, 21.0, 52.5


def _compute_optimal_route(fields, home_lat, home_lon):
    """Nearest-neighbour TSP heuristic. Returns ordered list of field dicts."""
    if not fields:
        return []
    unvisited = list(range(len(fields)))
    route = []
    cur_lat, cur_lon = home_lat, home_lon
    while unvisited:
        nearest = min(unvisited, key=lambda i: _haversine(cur_lat, cur_lon, fields[i]['lat'], fields[i]['lon']))
        unvisited.remove(nearest)
        f = dict(fields[nearest])
        f['order'] = len(route) + 1
        f['dist_from_prev_km'] = round(_haversine(cur_lat, cur_lon, f['lat'], f['lon']), 1)
        route.append(f)
        cur_lat, cur_lon = f['lat'], f['lon']
    return route


def _route_total_km(route, home_lat, home_lon):
    if not route:
        return 0.0
    total = _haversine(home_lat, home_lon, route[0]['lat'], route[0]['lon'])
    for i in range(1, len(route)):
        total += _haversine(route[i - 1]['lat'], route[i - 1]['lon'], route[i]['lat'], route[i]['lon'])
    total += _haversine(route[-1]['lat'], route[-1]['lon'], home_lat, home_lon)
    return round(total, 1)


def _estimate_duration(route, phase):
    """
    Estimate field campaign duration in hours.
    Base time per field depends on the number of measurements in the phase.
    """
    if not route:
        return 0.0
    n_measurements = len(phase.get('measurements', []))
    # Base time: 30 min/field + 10 min per measurement instrument
    time_per_field_h = 0.5 + n_measurements * (10 / 60)
    # Travel time: assume 60 km/h average on rural roads
    travel_h = sum(f.get('dist_from_prev_km', 0) for f in route) / 60
    # Return trip
    if route:
        travel_h += route[-1].get('dist_from_prev_km', 0) / 60
    return round(time_per_field_h * len(route) + travel_h + 0.5, 1)  # +0.5h base overhead


def _clean_display_text(value):
    """Remove dash characters from labels shown in the planner UI."""
    if value is None:
        return ''
    return str(value).replace('-', ' ').replace('–', ' ').replace('—', ' ')


def compute_measurement_plan_recommendations(plan):
    """
    Build a season-long field campaign plan.

    The planner intentionally does not use weather forecasts: seasonal plans
    usually cover many months, while operational forecasts are only meaningful
    for a short horizon. Instead, it selects one measurement campaign per
    phenological phase, preferring passes with confirmed image acquisition
    from Spectator.earth and dates closest to the middle of the phase.
    """
    from datetime import date as _date

    crop_type = plan.crop_type
    season_year = plan.season_year
    fields = plan.get_fields()
    today = _date.today()

    # --- Phenological phases (all phases for the season) ---
    all_phases = build_phases_with_dates(crop_type, season_year)

    # Keep only phases that have not yet ended (end_date >= today)
    phases = [p for p in all_phases if p['end_date'] >= today]

    if all_phases:
        season_end = max(p['end_date'] for p in all_phases)
    else:
        season_end = _date(season_year, 12, 31)

    # Season starts from today (forward-looking plan)
    season_start = today

    # --- Area geometry ---
    bbox = _plan_bbox(plan)
    center_lat, center_lon = plan.get_area_center()

    # --- Nearest IMGW weather station ---
    imgw_station = None
    try:
        imgw = IMGWClient()
        imgw_station = imgw.get_nearest_station(center_lat, center_lon)
    except Exception:
        pass

    # --- Satellite pass calendar from today to season end ---
    satellite_calendar = generate_satellite_calendar_for_season(
        bbox, season_start, season_end, center_lat, center_lon
    )

    # --- Score each pass without weather ---
    ACQUISITION_SCORES = {
        'imaging': 100,    # Spectator confirms image acquisition
        'estimated': 70,   # orbital repeat estimate outside Spectator horizon
        'unknown': 45,     # Spectator has no acquisition plan
        'no_image': 10,    # Spectator says no image will be acquired
    }
    SATELLITE_SCORES = {
        'Sentinel-2A': 100,
        'Sentinel-2B': 100,
        'Sentinel-2C': 100,
        'Landsat-8': 80,
        'Landsat-9': 80,
    }
    SAT_COLORS = {
        'Sentinel-2A': '#00d4ff', 'Sentinel-2B': '#00bfff', 'Sentinel-2C': '#00a8e8',
        'Landsat-8': '#ff8c00',   'Landsat-9': '#ffa500',
    }

    scored_passes = []
    for sat_pass in satellite_calendar:
        pass_date = sat_pass['date_obj']
        if not pass_date:
            continue
        # Only consider future passes (from today)
        if pass_date < today:
            continue
        date_str = sat_pass['date']

        for phase in phases:
            if not (phase['start_date'] <= pass_date <= phase['end_date']):
                continue

            phase_days = max(1, (phase['end_date'] - phase['start_date']).days + 1)
            phase_midpoint = phase['start_date'] + timedelta(days=phase_days // 2)
            distance_from_midpoint = abs((pass_date - phase_midpoint).days)
            timing_score = max(0, 100 - (distance_from_midpoint / max(1, phase_days / 2)) * 50)

            acq = sat_pass.get('acquisition_status', 'estimated')
            acquisition_score = ACQUISITION_SCORES.get(acq, 45)
            satellite_score = SATELLITE_SCORES.get(sat_pass.get('satellite'), 70)
            source_bonus = 5 if sat_pass.get('is_real') else 0

            total_score = round(min(
                100,
                acquisition_score * 0.60 + timing_score * 0.25 + satellite_score * 0.15 + source_bonus
            ), 1)

            satellite_label = sat_pass.get('satellite', '').replace('-', ' ')
            if acq == 'imaging':
                acquisition_label = 'confirmed image acquisition'
            elif acq == 'no_image':
                acquisition_label = 'confirmed pass without image acquisition'
            elif acq == 'estimated':
                acquisition_label = 'estimated overpass based on orbital repeat cycle'
            else:
                acquisition_label = 'overpass with unknown acquisition plan'

            scored_passes.append({
                **sat_pass,
                'date_label': pass_date.strftime('%d %b %Y'),
                'phase': phase,
                'phase_key': phase['key'],
                'priority_score': total_score,
                'acquisition_score': acquisition_score,
                'timing_score': round(timing_score, 1),
                'satellite_score': satellite_score,
                'satellite_label': satellite_label,
                'days_from_phase_midpoint': distance_from_midpoint,
                'phase_midpoint': phase_midpoint.isoformat(),
                'selection_reason': (
                    f"{satellite_label} on {pass_date.strftime('%d %b %Y')}: {acquisition_label}; "
                    f"{distance_from_midpoint} days from the middle of the phase."
                ),
                'sat_color': SAT_COLORS.get(sat_pass['satellite'], '#aaaaaa'),
            })

    scored_passes.sort(key=lambda x: (x['date'], -x['priority_score']))

    # --- Select one best campaign for every phenological phase ---
    campaigns = []
    for phase in phases:
        candidates = [sp for sp in scored_passes if sp['phase_key'] == phase['key']]
        if not candidates:
            continue
        campaigns.append(max(candidates, key=lambda sp: (
            sp['priority_score'],
            sp['acquisition_score'],
            -sp['days_from_phase_midpoint'],
            sp.get('is_real', False),
        )))

    campaigns.sort(key=lambda x: x['date'])

    home_lat = plan.home_lat or center_lat
    home_lon = plan.home_lon or center_lon

    for i, camp in enumerate(campaigns, 1):
        camp['campaign_number'] = i
        if fields:
            route = _compute_optimal_route(fields, home_lat, home_lon)
            total_km = _route_total_km(route, home_lat, home_lon)
            duration_h = round(total_km / 60 + len(route) * 0.5, 1)
        else:
            route, total_km, duration_h = [], 0, 0
        camp['field_route'] = route
        camp['total_distance_km'] = total_km
        camp['estimated_duration_h'] = duration_h

    # --- Coverage matrix (phase_key → campaign_number or None) ---
    coverage = {p['key']: None for p in phases}
    for camp in campaigns:
        pk = camp['phase_key']
        if coverage[pk] is None:
            coverage[pk] = camp['campaign_number']

    # Serialize dates for JSON template use
    for p in phases:
        p['start_date_str'] = p['start_date'].isoformat()
        p['end_date_str']   = p['end_date'].isoformat()
        p['display_name'] = _clean_display_text(p.get('name'))
        p['display_bbch'] = _clean_display_text(p.get('bbch'))
        p['display_description'] = _clean_display_text(p.get('description'))

    for sp in scored_passes:
        sp['date_obj'] = sp['date_obj'].isoformat() if hasattr(sp.get('date_obj'), 'isoformat') else sp.get('date')

    return {
        'phases':            phases,
        'all_phases':        all_phases,
        'satellite_calendar': scored_passes,
        'campaigns':         campaigns,
        'coverage_matrix':   coverage,
        'season_start':      season_start,
        'season_end':        season_end,
        'center_lat':        center_lat,
        'center_lon':        center_lon,
        'fields':            fields,
        'home_lat':          home_lat,
        'home_lon':          home_lon,
        'imgw_station':      imgw_station,
    }


# ---------------------------------------------------------------------------
# PLANNER VIEWS
# ---------------------------------------------------------------------------

def measurement_planner(request):
    """List plans + create new plan form."""
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('sign_in')

    try:
        user = UserAccountModel.objects.get(pk=user_id)
    except UserAccountModel.DoesNotExist:
        request.session.flush()
        return redirect('sign_in')

    if request.method == 'POST':
        form = MeasurementPlanForm(request.POST)
        if form.is_valid():
            plan = form.save(commit=False)
            plan.user = user
            plan.save()
            return redirect('plan_detail', plan_id=plan.id)
    else:
        form = MeasurementPlanForm(initial={'season_year': 2026})

    plans = MeasurementPlan.objects.filter(user=user)
    crop_labels = dict(MeasurementPlan.CROP_CHOICES)

    return render(request, 'measurement_planner.html', {
        'form': form,
        'plans': plans,
        'crop_labels': crop_labels,
    })


def measurement_plan_detail(request, plan_id):
    """Compute and display full measurement plan recommendations."""
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('sign_in')

    plan = get_object_or_404(MeasurementPlan, pk=plan_id, user_id=user_id)

    results = compute_measurement_plan_recommendations(plan)

    # Serialize for template JSON consumption
    campaigns_json = json.dumps([
        {
            'number': c['campaign_number'],
            'date': c['date'],
            'date_label': c.get('date_label', c['date']),
            'satellite': c['satellite'],
            'satellite_label': c.get('satellite_label', c['satellite'].replace('-', ' ')),
            'phase_key': c['phase']['key'],
            'phase_name': c['phase'].get('display_name', c['phase']['name']),
            'phase_color': c['phase']['color'],
            'total_distance_km': c.get('total_distance_km', 0),
            'estimated_duration_h': c.get('estimated_duration_h', 0),
            'fields': [
                {
                    'lat': f['lat'],
                    'lon': f['lon'],
                    'name': f.get('name', 'Field'),
                    'order': f['order'],
                    'dist_from_prev_km': f.get('dist_from_prev_km', 0),
                }
                for f in c.get('field_route', [])
            ],
        }
        for c in results['campaigns']
    ])
    fields_json = json.dumps(results['fields'])

    from datetime import date as _today_date
    _today = _today_date.today()

    # Use all_phases for the timeline so past phases appear greyed out
    _all = results.get('all_phases', results['phases'])
    for p in _all:
        if 'display_name' not in p:
            p['display_name'] = _clean_display_text(p.get('name'))
        if 'start_date_str' not in p:
            p['start_date_str'] = p['start_date'].isoformat()
        if 'end_date_str' not in p:
            p['end_date_str'] = p['end_date'].isoformat()

    phase_timeline_json = json.dumps([
        {
            'key': p['key'],
            'name': p.get('display_name', p['name']),
            'color': p['color'],
            'start': p['start_date_str'],
            'end': p['end_date_str'],
            'start_label': p['start_date'].strftime('%d %b'),
            'end_label': p['end_date'].strftime('%d %b'),
            'importance': p.get('importance', 'medium'),
            'is_past': p['end_date'] < _today,
            'is_active': p['start_date'] <= _today <= p['end_date'],
        }
        for p in _all
    ])
    area_geojson_json = plan.area_geojson or 'null'

    return render(request, 'plan_detail.html', {
        'plan': plan,
        'results': results,
        'campaigns_json': campaigns_json,
        'fields_json': fields_json,
        'area_geojson_json': area_geojson_json,
        'phase_timeline_json': phase_timeline_json,
        'season_start': results['season_start'].isoformat(),
        'season_end':   results['season_end'].isoformat(),
        'season_start_label': results['season_start'].strftime('%d %b %Y'),
        'season_end_label':   results['season_end'].strftime('%d %b %Y'),
        'imgw_station':       results.get('imgw_station'),
        'center_lat':   results['center_lat'],
        'center_lon':   results['center_lon'],
    })


def measurement_plan_delete(request, plan_id):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('sign_in')
    plan = get_object_or_404(MeasurementPlan, pk=plan_id, user_id=user_id)
    if request.method == 'POST':
        plan.delete()
    return redirect('measurement_planner')


# ---------------------------------------------------------------------------
# SPECTROMETER VIEWER
# ---------------------------------------------------------------------------

# ASD FieldSpec binary format constants
_ASD_HEADER_BYTES = 484
_ASD_CHANNELS = 2151
_ASD_WAVELENGTHS = np.arange(350.0, 350.0 + _ASD_CHANNELS)   # 350–2500 nm
_SPECTRALON_REFL = 0.99

# Sentinel-2A band definitions: {name: (center_nm, fwhm_nm)}
_S2_BANDS = {
    'B4':  (664.9,  31.0),
    'B5':  (704.1,  14.9),
    'B6':  (740.5,  14.5),
    'B7':  (782.8,  21.5),
    'B8':  (832.8, 106.0),   # broad NIR – used for NDVI
    'B8A': (864.7,  20.5),
}

# Spectral shape thresholds for surface-type detection
_NDVI_VEGETATION_THRESHOLD = 0.20   # NDVI > this → vegetation, else water


def _read_asd_bytes(raw: bytes) -> np.ndarray:
    """Parse raw ASD binary data → float64 spectrum array (2151 channels)."""
    needed = _ASD_HEADER_BYTES + _ASD_CHANNELS * 8
    if len(raw) < needed:
        raise ValueError(f"File too short ({len(raw)} bytes, need {needed})")
    return np.frombuffer(raw[_ASD_HEADER_BYTES:_ASD_HEADER_BYTES + _ASD_CHANNELS * 8],
                         dtype='<f8').copy()


def _is_spectralon(spectrum: np.ndarray) -> bool:
    """Heuristic: returns True if the spectrum looks like a Spectralon 99% panel."""
    vis = spectrum[(_ASD_WAVELENGTHS >= 400) & (_ASD_WAVELENGTHS <= 900)]
    if len(vis) == 0 or vis.max() <= 0:
        return False
    return vis.max() > 2000 and vis.min() > 0 and vis.std() / vis.mean() < 0.5


def _simulate_s2_band(spectrum: np.ndarray, center_nm: float, fwhm_nm: float) -> float:
    """Convolve spectrum with a Gaussian SRF for one S2 band (uses ASD wavelength grid)."""
    return _simulate_s2_band_wl(spectrum, _ASD_WAVELENGTHS, center_nm, fwhm_nm)


def _compute_indices(b4: float, b5: float, b7: float) -> dict:
    """Compute 2BDA, NDCI, 3BDA chlorophyll indices."""
    indices = {}
    try:
        indices['2BDA'] = round(b5 / b4, 5) if b4 > 0 else None
        denom = b5 + b4
        indices['NDCI'] = round((b5 - b4) / denom, 5) if denom != 0 else None
        indices['3BDA'] = round((1.0 / b4 - 1.0 / b5) * b7, 5) if b4 > 0 and b5 > 0 else None
    except (ZeroDivisionError, OverflowError):
        pass
    return indices


def _compute_ndvi(s2_bands: dict) -> dict:
    """Compute NDVI vegetation indices from simulated S2 bands."""
    ndvi_results = {}
    try:
        b4  = s2_bands.get('B4',  0) or 0
        b8  = s2_bands.get('B8',  0) or 0
        b8a = s2_bands.get('B8A', 0) or 0
        if abs(b8 + b4) > 1e-9:
            ndvi_results['NDVI']     = round((b8 - b4) / (b8 + b4), 5)
        else:
            ndvi_results['NDVI'] = None
        if abs(b8a + b4) > 1e-9:
            ndvi_results['NDVI_B8A'] = round((b8a - b4) / (b8a + b4), 5)
        else:
            ndvi_results['NDVI_B8A'] = None
    except (ZeroDivisionError, OverflowError):
        pass
    return ndvi_results


def _detect_surface_type(s2_bands: dict) -> str:
    """
    Classify spectral signature as 'vegetation' or 'water' using NDVI.
    Vegetation: NDVI > _NDVI_VEGETATION_THRESHOLD
    Water     : otherwise
    """
    b4 = s2_bands.get('B4', 0) or 0
    b8 = s2_bands.get('B8', 0) or 0
    denom = b8 + b4
    if abs(denom) < 1e-9:
        return 'water'
    ndvi = (b8 - b4) / denom
    return 'vegetation' if ndvi > _NDVI_VEGETATION_THRESHOLD else 'water'


def _read_asd_txt(text: str) -> tuple[np.ndarray, list[tuple[str, np.ndarray]]]:
    """
    Parse ASD Indico Pro text export (.txt).

    The file has two sections:
      1. CSV header + metadata rows  (first column is a date string)
      2. A wavelength header row     (first value ≈ 350)
      3. Spectral data rows          (2151 float values per row)

    Returns
    -------
    wavelengths  : np.ndarray  shape (N_wl,)
    spectra      : list of (label, np.ndarray) pairs
    """
    import csv as _csv

    lines = text.splitlines()

    # Locate the wavelength-header row (first value ≈ 350, many columns)
    wl_row_idx = None
    for i, line in enumerate(lines):
        first = line.split(',')[0].strip()
        try:
            val = float(first)
            if 349 < val < 360:
                parts = [c for c in line.split(',') if c.strip()]
                if len(parts) > 100:
                    wl_row_idx = i
                    break
        except ValueError:
            pass

    if wl_row_idx is None:
        raise ValueError("ASD .txt: wavelength header row not found")

    # Parse wavelengths
    wl_parts = lines[wl_row_idx].split(',')
    wavelengths = np.array([float(c) for c in wl_parts if c.strip()])
    n_wl = len(wavelengths)

    # Parse metadata to build labels (use date string if available)
    meta_lines = lines[1:wl_row_idx]
    meta_labels = []
    for i, line in enumerate(meta_lines):
        if not line.strip():
            continue
        cols = line.split(',')
        # Try to use the Date Taken field (first column) as a short label
        date_str = cols[0].strip() if cols else f"M{i+1}"
        meta_labels.append(date_str)

    # Parse spectral rows
    spectra: list[tuple[str, np.ndarray]] = []
    for j, line in enumerate(lines[wl_row_idx + 1:]):
        if not line.strip():
            continue
        vals = [float(c) for c in line.split(',') if c.strip()]
        if len(vals) == n_wl:
            label = meta_labels[j] if j < len(meta_labels) else f"Spectrum_{j+1}"
            # Use a short label: "M{j+1}" prefixed by the time part of the date
            try:
                time_part = label.split(' ')[1] + label.split(' ')[2]  # e.g. "2:05:48PM"
                label = f"M{j+1} ({time_part})"
            except Exception:
                label = f"M{j+1}"
            spectra.append((label, np.array(vals, dtype=float)))

    if not spectra:
        raise ValueError("ASD .txt: no spectral data rows found")

    return wavelengths, spectra


def _process_spectra(spectra_dict: dict,
                     spectralon: np.ndarray | None,
                     wavelengths: np.ndarray | None = None) -> list:
    """
    Convert raw spectra to reflectance (if Spectralon available), compute S2 bands,
    auto-detect surface type and calculate relevant indices.

    For vegetation → NDVI (B8, B8A)
    For water      → chlorophyll indices (2BDA, NDCI, 3BDA)

    Returns a list of dicts ready for JSON serialisation.
    """
    results = []
    wl = wavelengths if wavelengths is not None else _ASD_WAVELENGTHS

    ref = spectralon.copy() if spectralon is not None else None
    if ref is not None:
        ref[ref <= 0] = np.nan

    for name, raw in spectra_dict.items():
        entry = {'name': name}

        if ref is not None:
            refl = (raw / ref) * _SPECTRALON_REFL
            refl = np.where(np.isfinite(refl), refl, None)
            entry['reflectance'] = [round(float(v), 6) if v is not None else None
                                    for v in refl]
            refl_arr = np.array([v if v is not None else np.nan for v in entry['reflectance']])
        else:
            entry['reflectance'] = [round(float(v), 4) for v in raw]
            refl_arr = raw.copy()

        # Simulated S2 bands
        s2_bands = {}
        for bname, (center, fwhm) in _S2_BANDS.items():
            val = _simulate_s2_band_wl(refl_arr, wl, center, fwhm)
            s2_bands[bname] = round(val, 6)
        entry['s2_bands'] = s2_bands

        # Auto-detect surface type
        surface_type = _detect_surface_type(s2_bands)
        entry['surface_type'] = surface_type

        if surface_type == 'vegetation':
            entry['indices'] = _compute_ndvi(s2_bands)
            entry['index_type'] = 'ndvi'
        else:
            b4 = s2_bands.get('B4', 0)
            b5 = s2_bands.get('B5', 0)
            b7 = s2_bands.get('B7', 0)
            entry['indices'] = _compute_indices(b4, b5, b7)
            entry['index_type'] = 'chlorophyll'

        results.append(entry)
    return results


def _simulate_s2_band_wl(spectrum: np.ndarray,
                          wavelengths: np.ndarray,
                          center_nm: float, fwhm_nm: float) -> float:
    """Convolve spectrum with a Gaussian SRF for one S2 band (arbitrary wavelength grid)."""
    sigma = fwhm_nm / (2.0 * math.sqrt(2.0 * math.log(2.0)))
    weights = np.exp(-0.5 * ((wavelengths - center_nm) / sigma) ** 2)
    weights /= weights.sum()
    valid = np.isfinite(spectrum)
    if valid.sum() == 0:
        return float('nan')
    return float(np.sum(spectrum[valid] * weights[valid]))


def spectrometer_view(request):
    """Render the Spectrometer Viewer page."""
    return render(request, 'spectrometer.html', {})


@csrf_exempt
def spectrometer_upload_api(request):
    """
    POST /api/spectrometer/upload/
    Accepts multipart/form-data with key 'files' (multiple .asd / .csv / .txt files).
    Returns JSON with parsed spectra, S2 bands, and vegetation/water indices.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    uploaded_files = request.FILES.getlist('files')
    if not uploaded_files:
        return JsonResponse({'error': 'No files uploaded'}, status=400)

    asd_raw: dict[str, np.ndarray] = {}
    spectralon: np.ndarray | None = None
    spectralon_name: str | None = None
    csv_spectra: dict[str, np.ndarray] = {}
    # .txt ASD exports carry their own wavelength grid
    txt_spectra: list[tuple[str, np.ndarray]] = []
    txt_wavelengths: np.ndarray | None = None
    errors: list[str] = []

    # ── Parse each uploaded file ──────────────────────────────────────────
    for f in uploaded_files:
        name = f.name
        raw_bytes = f.read()

        if name.lower().endswith('.asd'):
            try:
                spectrum = _read_asd_bytes(raw_bytes)
                if _is_spectralon(spectrum):
                    spectralon = spectrum
                    spectralon_name = name
                else:
                    asd_raw[name] = spectrum
            except Exception as exc:
                errors.append(f"{name}: {exc}")

        elif name.lower().endswith('.txt'):
            # ASD Indico Pro text export (multi-spectrum, own wavelength grid)
            try:
                text = raw_bytes.decode('utf-8', errors='replace')
                wl, spectra_list = _read_asd_txt(text)
                txt_wavelengths = wl
                for lbl, sp in spectra_list:
                    txt_spectra.append((lbl, sp))
            except Exception as exc:
                errors.append(f"{name}: {exc}")

        elif name.lower().endswith('.csv'):
            try:
                text = raw_bytes.decode('utf-8', errors='replace')
                import csv as _csv
                reader = _csv.reader(io.StringIO(text))
                rows = list(reader)

                # Auto-detect: first row header or data?
                headers = []
                data_rows = rows
                if rows and not _is_numeric(rows[0][0]):
                    headers = rows[0]
                    data_rows = rows[1:]

                if not data_rows:
                    errors.append(f"{name}: empty CSV")
                    continue

                # First column = wavelength, remaining = spectra
                wavelengths_csv = []
                columns = [[] for _ in range(len(data_rows[0]) - 1)]
                for row in data_rows:
                    if len(row) < 2:
                        continue
                    try:
                        wavelengths_csv.append(float(row[0]))
                        for ci in range(len(columns)):
                            columns[ci].append(float(row[ci + 1]) if ci + 1 < len(row) else np.nan)
                    except ValueError:
                        continue

                if not wavelengths_csv:
                    errors.append(f"{name}: no numeric data found")
                    continue

                wl_arr = np.array(wavelengths_csv)
                col_names = headers[1:] if len(headers) > 1 else \
                            [f"{name.replace('.csv','')}_{i+1}" for i in range(len(columns))]

                for ci, col in enumerate(columns):
                    col_arr = np.array(col)
                    interp = np.interp(_ASD_WAVELENGTHS, wl_arr, col_arr,
                                       left=np.nan, right=np.nan)
                    col_label = col_names[ci] if ci < len(col_names) else f"col_{ci+1}"
                    csv_spectra[col_label] = interp

            except Exception as exc:
                errors.append(f"{name}: {exc}")
        else:
            errors.append(f"{name}: unsupported format (.asd, .csv, .txt)")

    # ── Process .asd binary + .csv spectra (standard ASD wavelength grid) ─
    all_standard = {**asd_raw, **csv_spectra}
    processed: list[dict] = []

    if all_standard:
        processed.extend(_process_spectra(all_standard, spectralon,
                                          wavelengths=_ASD_WAVELENGTHS))

    # ── Process .txt spectra (native wavelength grid) ─────────────────────
    txt_wl = txt_wavelengths if txt_wavelengths is not None else _ASD_WAVELENGTHS
    if txt_spectra:
        txt_dict = {lbl: sp for lbl, sp in txt_spectra}
        processed.extend(_process_spectra(txt_dict, spectralon=None,
                                          wavelengths=txt_wl))

    if not processed:
        return JsonResponse({
            'error': 'No valid spectra found.',
            'details': errors,
        }, status=400)

    # ── Determine output wavelength grid for front-end ────────────────────
    if txt_spectra and not all_standard:
        out_wavelengths = txt_wl.tolist()
    else:
        out_wavelengths = _ASD_WAVELENGTHS.tolist()

    # ── Build response ────────────────────────────────────────────────────
    response = {
        'wavelengths': out_wavelengths,
        'spectra': processed,
        'spectralon_used': spectralon_name,
        'errors': errors,
        's2_band_centers': {k: v[0] for k, v in _S2_BANDS.items()},
    }
    return JsonResponse(response)


def _is_numeric(value: str) -> bool:
    """Return True if string can be parsed as a float."""
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False
