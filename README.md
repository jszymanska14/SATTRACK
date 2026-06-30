# SATTRACK

A web application for satellite trajectory prediction and weather-aware observation planning. Built to support field measurement campaigns that require coordination with Sentinel-2 and Landsat satellite overpasses.

## What it does

SATTRACK combines three things in one place: orbital prediction, acquisition status from the Spectator.earth API, and weather forecasts. You draw a study area on a map, pick a date, and the application tells you which satellites will pass over, whether they will actually collect imagery, and whether conditions on the ground will be good enough for optical remote sensing.


## Features

- **Satellite pass prediction** — computes overpass times for Sentinel-2A/B/C and Landsat 8/9 using the SGP4/SDP4 propagation model via the Skyfield library and TLE data from CelesTrak
- **Acquisition status** — integrates with the Spectator.earth API to show whether each pass will result in an actual image acquisition
- **Weather scoring** — retrieves forecasts from WeatherAPI.com and assigns an observation suitability score (0–100) based on visibility, precipitation probability, and wind speed
- **Observation log** — authenticated users can record completed field observations with GPS coordinates, satellite name, date, time, and notes
- **Observation calendar** — monthly view of logged observations and satellite analysis events
- **Spectrometer module** — upload ASD FieldSpec export files directly in the browser and compute vegetation (NDVI) and water quality (2BDA, NDCI, 3BDA) indices from Gaussian-simulated Sentinel-2 bands

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python 3.10, Django 5 |
| Orbital propagation | Skyfield, SGP4/SDP4 |
| Spatial processing | Shapely, PyProj |
| Frontend | Leaflet.js, Leaflet.Draw, FullCalendar.js, Bootstrap |
| Database | PostgreSQL (production), SQLite (development) |
| External APIs | N2YO, Spectator.earth, WeatherAPI.com, CelesTrak |

## Getting started

**Requirements:** Python 3.10+, pip

```bash
git clone https://github.com/jszymanska14/SATTRACK.git
cd SATTRACK
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in the project root with the following variables:

```
SECRET_KEY=your_django_secret_key
DEBUG=True
WEATHER_API_KEY=your_weatherapi_key
N2YO_API_KEY=your_n2yo_key
```

Run migrations and start the development server:

```bash
python manage.py migrate
python manage.py runserver
```

Open `http://127.0.0.1:8000` in your browser.

## Project structure

```
sat_track/
    apis.py               # clients for N2YO, Spectator.earth, WeatherAPI
    models.py             # UserAccountModel, Event, Observation, MeasurementPlan
    views.py              # all view logic
    urls.py               # URL routing
    templates/
        home.html         # map interface and satellite analysis
        event_detail.html # overpass results and weather scoring
        spectrometer.html # ASD file upload and index calculation
        weather_panel.html
        observation_calendar.html
        user_profile.html
        measurement_planner.html
project/
    settings.py
    urls.py
```

## API keys

The application requires three external API keys. All are available on free tiers sufficient for research use:

- **WeatherAPI.com** — https://www.weatherapi.com
- **N2YO** — https://www.n2yo.com/api
- **Spectator.earth** — https://spectator.earth


