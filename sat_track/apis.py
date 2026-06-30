import json
import math
import requests
from datetime import datetime, date, timedelta, timezone as dt_timezone


# Detailed trajectory analysis set (TLE + weather matching, small focused subset)
OPTICAL_SATELLITES = {
    'sentinel-2a': {'norad_id': 40697, 'name': 'Sentinel-2A', 'swath_km': 290, 'imaging': True, 'category': 'Optical Imaging (ESA)'},
    'sentinel-2b': {'norad_id': 42063, 'name': 'Sentinel-2B', 'swath_km': 290, 'imaging': True, 'category': 'Optical Imaging (ESA)'},
    'landsat-8':   {'norad_id': 39084, 'name': 'Landsat 8',   'swath_km': 185, 'imaging': True, 'category': 'Optical Imaging (NASA/USGS)'},
    'landsat-9':   {'norad_id': 49260, 'name': 'Landsat 9',   'swath_km': 185, 'imaging': True, 'category': 'Optical Imaging (NASA/USGS)'},
}

SATELLITE_CHOICES = [
    (key, info['name']) for key, info in OPTICAL_SATELLITES.items()
]

# NORAD IDs of known imaging satellites (Earth observation)
IMAGING_SATELLITE_NORAD_IDS = {
    39634,  # Sentinel-1A
    41456,  # Sentinel-1B
    40697,  # Sentinel-2A
    42063,  # Sentinel-2B
    60435,  # Sentinel-2C
    41335,  # Sentinel-3A
    43437,  # Sentinel-3B
    25682,  # Landsat 7
    39084,  # Landsat 8
    49260,  # Landsat 9
    25338,  # NOAA 15
    28654,  # NOAA 18
    33591,  # NOAA 19
    43013,  # NOAA 20 (JPSS-1)
    37849,  # Suomi NPP
    25994,  # Terra
    27424,  # Aqua
    40376,  # SMAP
    55155,  # SWOT
    36605,  # TanDEM-X
    39086,  # SARAL
    43641,  # SAOCOM-1A
    46265,  # SAOCOM-1B
    39150,  # Gaofen-1
    40118,  # Gaofen-2
    41788,  # Gaofen-3
    43461,  # Gaofen-5
    43484,  # Gaofen-6
    44703,  # Gaofen-7
    39070,  # KOMPSAT-3
    40536,  # KOMPSAT-3A
    39072,  # KOMPSAT-5
    43197,  # VRSS-2
    42901,  # VENµS
}

# Full catalog for N2YO pass queries (imaging + non-imaging for comparison)
SATELLITE_CATALOG = {
    # ── Copernicus / ESA ──────────────────────────────────────────────────────
    'sentinel-1a':  {'norad_id': 39634, 'name': 'Sentinel-1A',  'imaging': True,  'category': 'SAR Imaging (ESA)'},
    'sentinel-1b':  {'norad_id': 41456, 'name': 'Sentinel-1B',  'imaging': True,  'category': 'SAR Imaging (ESA)'},
    'sentinel-2a':  {'norad_id': 40697, 'name': 'Sentinel-2A',  'imaging': True,  'category': 'Optical Imaging (ESA)'},
    'sentinel-2b':  {'norad_id': 42063, 'name': 'Sentinel-2B',  'imaging': True,  'category': 'Optical Imaging (ESA)'},
    'sentinel-2c':  {'norad_id': 60435, 'name': 'Sentinel-2C',  'imaging': True,  'category': 'Optical Imaging (ESA)'},
    'sentinel-3a':  {'norad_id': 41335, 'name': 'Sentinel-3A',  'imaging': True,  'category': 'Ocean/Thermal Imaging (ESA)'},
    'sentinel-3b':  {'norad_id': 43437, 'name': 'Sentinel-3B',  'imaging': True,  'category': 'Ocean/Thermal Imaging (ESA)'},
    # ── Landsat / NASA-USGS ───────────────────────────────────────────────────
    'landsat-7':    {'norad_id': 25682, 'name': 'Landsat 7',    'imaging': True,  'category': 'Optical Imaging (NASA/USGS)'},
    'landsat-8':    {'norad_id': 39084, 'name': 'Landsat 8',    'imaging': True,  'category': 'Optical Imaging (NASA/USGS)'},
    'landsat-9':    {'norad_id': 49260, 'name': 'Landsat 9',    'imaging': True,  'category': 'Optical Imaging (NASA/USGS)'},
    # ── NOAA / JPSS ──────────────────────────────────────────────────────────
    'noaa-15':      {'norad_id': 25338, 'name': 'NOAA 15',      'imaging': True,  'category': 'Weather Imaging (NOAA)'},
    'noaa-18':      {'norad_id': 28654, 'name': 'NOAA 18',      'imaging': True,  'category': 'Weather Imaging (NOAA)'},
    'noaa-19':      {'norad_id': 33591, 'name': 'NOAA 19',      'imaging': True,  'category': 'Weather Imaging (NOAA)'},
    'noaa-20':      {'norad_id': 43013, 'name': 'NOAA 20',      'imaging': True,  'category': 'Weather Imaging (NOAA/JPSS)'},
    'suomi-npp':    {'norad_id': 37849, 'name': 'Suomi NPP',    'imaging': True,  'category': 'Weather Imaging (NASA/NOAA)'},
    # ── NASA Earth Observation ────────────────────────────────────────────────
    'terra':        {'norad_id': 25994, 'name': 'Terra',        'imaging': True,  'category': 'Multispectral Imaging (NASA)'},
    'aqua':         {'norad_id': 27424, 'name': 'Aqua',         'imaging': True,  'category': 'Multispectral Imaging (NASA)'},
    # ── Other imaging ─────────────────────────────────────────────────────────
    'smap':         {'norad_id': 40376, 'name': 'SMAP',         'imaging': True,  'category': 'Microwave Imaging (NASA)'},
    'swot':         {'norad_id': 55155, 'name': 'SWOT',         'imaging': True,  'category': 'Surface Water Imaging (NASA/CNES)'},
    'tandem-x':     {'norad_id': 36605, 'name': 'TanDEM-X',     'imaging': True,  'category': 'SAR Imaging (DLR)'},
    'saral':        {'norad_id': 39086, 'name': 'SARAL',        'imaging': True,  'category': 'Radar Altimetry (ISRO/CNES)'},
    'saocom-1a':    {'norad_id': 43641, 'name': 'SAOCOM-1A',   'imaging': True,  'category': 'SAR Imaging (CONAE)'},
    'saocom-1b':    {'norad_id': 46265, 'name': 'SAOCOM-1B',   'imaging': True,  'category': 'SAR Imaging (CONAE)'},
    'gaofen-1':     {'norad_id': 39150, 'name': 'Gaofen-1',    'imaging': True,  'category': 'Optical Imaging (CNSA)'},
    'gaofen-2':     {'norad_id': 40118, 'name': 'Gaofen-2',    'imaging': True,  'category': 'Optical Imaging (CNSA)'},
    'gaofen-3':     {'norad_id': 41788, 'name': 'Gaofen-3',    'imaging': True,  'category': 'SAR Imaging (CNSA)'},
    'gaofen-5':     {'norad_id': 43461, 'name': 'Gaofen-5',    'imaging': True,  'category': 'Hyperspectral Imaging (CNSA)'},
    'gaofen-6':     {'norad_id': 43484, 'name': 'Gaofen-6',    'imaging': True,  'category': 'Optical Imaging (CNSA)'},
    'gaofen-7':     {'norad_id': 44703, 'name': 'Gaofen-7',    'imaging': True,  'category': 'Stereo Imaging (CNSA)'},
    'kompsat-3':    {'norad_id': 39070, 'name': 'KOMPSAT-3',   'imaging': True,  'category': 'Optical Imaging (KARI)'},
    'kompsat-3a':   {'norad_id': 40536, 'name': 'KOMPSAT-3A',  'imaging': True,  'category': 'Optical/IR Imaging (KARI)'},
    'kompsat-5':    {'norad_id': 39072, 'name': 'KOMPSAT-5',   'imaging': True,  'category': 'SAR Imaging (KARI)'},
    'vrss-2':       {'norad_id': 43197, 'name': 'VRSS-2',      'imaging': True,  'category': 'Optical Imaging (VNSC)'},
    'venus':        {'norad_id': 42901, 'name': 'VENµS',       'imaging': True,  'category': 'Vegetation Imaging (ESA/CNES)'},
    # ── Non-imaging (reference only) ──────────────────────────────────────────
    'iss':          {'norad_id': 25544, 'name': 'ISS',                    'imaging': False, 'category': 'Space Station'},
    'hubble':       {'norad_id': 20580, 'name': 'Hubble Space Telescope', 'imaging': False, 'category': 'Space Telescope (not Earth)'},
    'jason-3':      {'norad_id': 41240, 'name': 'Jason-3',               'imaging': False, 'category': 'Radar Altimetry (CNES/EUMETSAT)'},
    'cryosat-2':    {'norad_id': 36508, 'name': 'CryoSat-2',             'imaging': False, 'category': 'Ice Altimetry (ESA)'},
    'grace-fo-1':   {'norad_id': 43476, 'name': 'GRACE-FO 1',            'imaging': False, 'category': 'Gravity Field (NASA/GFZ)'},
}


class N2YOClient:
    """Client for N2YO REST API v1 – TLE, visual passes, radio passes, positions."""

    BASE_URL = "https://api.n2yo.com/rest/v1/satellite"
    API_KEY = "9KS9FZ-ZUQC5U-QLTE6P-5HQX"

    def __init__(self, sat_id):
        self.sat_id = sat_id

    def _get(self, endpoint):
        url = f"{self.BASE_URL}/{endpoint}&apiKey={self.API_KEY}"
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    # ------------------------------------------------------------------
    # TLE
    # ------------------------------------------------------------------

    def fetch_tle(self):
        data = self._get(f"tle/{self.sat_id}?")
        if "error" in data:
            return data
        try:
            tle_lines = data["tle"].split("\r\n")
            return {
                "line1": tle_lines[0],
                "line2": tle_lines[1],
                "satname": data["info"]["satname"],
            }
        except (KeyError, IndexError) as e:
            return {"error": f"TLE parse error: {e}"}

    # ------------------------------------------------------------------
    # Visual passes (satellite illuminated, observer in darkness)
    # ------------------------------------------------------------------

    def fetch_visual_passes(self, lat, lng, alt=0, days=10, min_visibility=30):
        endpoint = (
            f"visualpasses/{self.sat_id}/{lat}/{lng}/{alt}/{days}/{min_visibility}?"
        )
        data = self._get(endpoint)
        if "error" in data:
            return {"passes": [], "satname": "", "error": data.get("error")}

        raw_passes = data.get("passes") or []
        passes = []
        for p in raw_passes:
            passes.append({
                "startUTC": p.get("startUTC"),
                "startAzCompass": p.get("startAzCompass"),
                "startEl": p.get("startEl"),
                "maxUTC": p.get("maxUTC"),
                "maxAzCompass": p.get("maxAzCompass"),
                "maxEl": p.get("maxEl"),
                "endUTC": p.get("endUTC"),
                "endAzCompass": p.get("endAzCompass"),
                "endEl": p.get("endEl"),
                "mag": p.get("mag"),
                "duration": p.get("duration"),
                "start_dt": datetime.fromtimestamp(
                    p["startUTC"], tz=dt_timezone.utc
                ).strftime("%Y-%m-%d %H:%M:%S"),
                "max_dt": datetime.fromtimestamp(
                    p["maxUTC"], tz=dt_timezone.utc
                ).strftime("%Y-%m-%d %H:%M:%S"),
                "end_dt": datetime.fromtimestamp(
                    p["endUTC"], tz=dt_timezone.utc
                ).strftime("%Y-%m-%d %H:%M:%S"),
            })

        return {
            "satname": data.get("info", {}).get("satname", ""),
            "satid": self.sat_id,
            "passes": passes,
            "count": len(passes),
        }

    # ------------------------------------------------------------------
    # Radio passes (any pass above minimum elevation)
    # ------------------------------------------------------------------

    def fetch_radio_passes(self, lat, lng, alt=0, days=10, min_elevation=10):
        endpoint = (
            f"radiopasses/{self.sat_id}/{lat}/{lng}/{alt}/{days}/{min_elevation}?"
        )
        data = self._get(endpoint)
        if "error" in data:
            return {"passes": [], "satname": "", "error": data.get("error")}

        raw_passes = data.get("passes") or []
        passes = []
        for p in raw_passes:
            passes.append({
                "startUTC": p.get("startUTC"),
                "startAzCompass": p.get("startAzCompass"),
                "maxUTC": p.get("maxUTC"),
                "maxAzCompass": p.get("maxAzCompass"),
                "maxEl": p.get("maxEl"),
                "endUTC": p.get("endUTC"),
                "endAzCompass": p.get("endAzCompass"),
                "duration": p.get("duration"),
                "start_dt": datetime.fromtimestamp(
                    p["startUTC"], tz=dt_timezone.utc
                ).strftime("%Y-%m-%d %H:%M:%S"),
                "max_dt": datetime.fromtimestamp(
                    p["maxUTC"], tz=dt_timezone.utc
                ).strftime("%Y-%m-%d %H:%M:%S"),
                "end_dt": datetime.fromtimestamp(
                    p["endUTC"], tz=dt_timezone.utc
                ).strftime("%Y-%m-%d %H:%M:%S"),
            })

        return {
            "satname": data.get("info", {}).get("satname", ""),
            "satid": self.sat_id,
            "passes": passes,
            "count": len(passes),
        }

    # ------------------------------------------------------------------
    # Positions (real-time and short-term future)
    # ------------------------------------------------------------------

    def fetch_positions(self, lat, lng, alt=0, seconds=300):
        endpoint = (
            f"positions/{self.sat_id}/{lat}/{lng}/{alt}/{seconds}?"
        )
        data = self._get(endpoint)
        if "error" in data:
            return {"positions": [], "satname": ""}

        raw_pos = data.get("positions") or []
        positions = []
        for pos in raw_pos:
            positions.append({
                "timestamp": datetime.fromtimestamp(
                    pos["timestamp"], tz=dt_timezone.utc
                ).isoformat(),
                "latitude": pos.get("satlatitude"),
                "longitude": pos.get("satlongitude"),
                "altitude_km": pos.get("sataltitude"),
                "azimuth": pos.get("azimuth"),
                "elevation": pos.get("elevation"),
                "eclipsed": pos.get("eclipsed"),
            })

        return {
            "satname": data.get("info", {}).get("satname", ""),
            "positions": positions,
        }


# Backward-compatible alias
class N2YOTLEFetcher(N2YOClient):
    pass


# ---------------------------------------------------------------------------
# IMGW (Polish Institute of Meteorology and Water Management) API client
# ---------------------------------------------------------------------------

class IMGWClient:
    """
    Client for IMGW public data API (danepubliczne.imgw.pl).
    Provides current synoptic measurements from Polish meteorological stations.
    """

    BASE_URL = "https://danepubliczne.imgw.pl/api/data"

    # Known major IMGW synoptic station coordinates (lat, lon, station name in API)
    STATION_COORDS = {
        'WARSZAWA-OKĘCIE':  (52.17, 20.97),
        'KRAKÓW-OBSERWATORIUM': (50.07, 19.97),
        'WROCŁAW':          (51.10, 16.89),
        'GDAŃSK':           (54.38, 18.47),
        'POZNAŃ':           (52.42, 16.83),
        'KATOWICE':         (50.25, 19.03),
        'LUBLIN':           (51.22, 22.40),
        'RZESZÓW':          (50.11, 22.03),
        'ŁÓDŹ':             (51.73, 19.40),
        'BYDGOSZCZ':        (53.13, 18.00),
        'KIELCE':           (50.87, 20.63),
        'BIAŁYSTOK':        (53.10, 23.17),
        'OLSZTYN':          (53.78, 20.43),
        'SZCZECIN':         (53.40, 14.62),
        'OPOLE':            (50.67, 17.97),
        'ZIELONA GÓRA':     (51.93, 15.50),
        'TORUŃ':            (53.05, 18.57),
        'ZAMOŚĆ':           (50.72, 23.25),
        'SUWAŁKI':          (54.13, 22.93),
        'ZAKOPANE':         (49.30, 19.95),
    }

    def get_synoptic_data(self):
        """Fetch current synoptic measurements from all stations."""
        try:
            r = requests.get(f"{self.BASE_URL}/synop/", timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            return {"error": str(e)}

    def get_nearest_station(self, lat, lon):
        """Return synoptic data for the IMGW station nearest to (lat, lon)."""
        nearest_name = None
        min_dist = float('inf')
        for name, (slat, slon) in self.STATION_COORDS.items():
            dist = math.sqrt((slat - lat) ** 2 + (slon - lon) ** 2)
            if dist < min_dist:
                min_dist = dist
                nearest_name = name

        if not nearest_name:
            return None

        all_data = self.get_synoptic_data()
        if isinstance(all_data, dict) and "error" in all_data:
            return {"error": all_data["error"], "station_name": nearest_name}

        if isinstance(all_data, list):
            for station in all_data:
                station_name_api = str(station.get('stacja', '')).upper()
                nearest_upper = nearest_name.upper()
                # Fuzzy match on first word
                if nearest_upper.split('-')[0].split()[0] in station_name_api:
                    station['_distance_deg'] = round(min_dist, 3)
                    return station

        return {"station_name": nearest_name, "distance_deg": round(min_dist, 3), "note": "Station found but data not matched"}

    def get_station_summary(self, station_data):
        """Convert raw IMGW station dict to a clean summary dict."""
        if not station_data or "error" in station_data:
            return None
        return {
            'station': station_data.get('stacja', 'Unknown'),
            'date': station_data.get('data_pomiaru', ''),
            'hour': station_data.get('godzina_pomiaru', ''),
            'temperature_c': station_data.get('temperatura'),
            'wind_speed_ms': station_data.get('predkosc_wiatru'),
            'wind_dir': station_data.get('kierunek_wiatru'),
            'humidity_pct': station_data.get('wilgotnosc_wzgledna'),
            'precipitation_mm': station_data.get('suma_opadu'),
            'pressure_hpa': station_data.get('cisnienie'),
        }


# ---------------------------------------------------------------------------
# Phenological calendar for Polish agricultural conditions  (~52 N)
# ---------------------------------------------------------------------------
# Phases defined as (month, day) start/end relative to the growing season.
# year_offset = -1 means the date belongs to the year before season_year
#               (used for winter crops sown in autumn).
# cross_year = True  when start is in year_offset year and end is in season_year.
# importance: 'very_high' | 'high' | 'medium' | 'low'

PHENOLOGICAL_CALENDAR = {
    # ── Winter Wheat ──────────────────────────────────────
    'winter_wheat': [
        {
            'key': 'bbch_0',
            'name': 'Germination',
            'bbch': 'BBCH 0',
            'color': '#8B4513',
            'start': (10, 1), 'end': (10, 25), 'year_offset': -1,
            'importance': 'medium',
            'icon': 'fas fa-seedling',
            'measurements': [],
            'description': 'Grain germination after autumn sowing.',
        },
        {
            'key': 'bbch_1',
            'name': 'Leaf Development',
            'bbch': 'BBCH 1',
            'color': '#90EE90',
            'start': (10, 20), 'end': (11, 20), 'year_offset': -1,
            'importance': 'medium',
            'icon': 'fas fa-leaf',
            'measurements': [],
            'description': 'Development of first leaves after emergence.',
        },
        {
            'key': 'bbch_2',
            'name': 'Tillering',
            'bbch': 'BBCH 2',
            'color': '#228B22',
            'start': (11, 10), 'end': (3, 15), 'year_offset': -1, 'cross_year': True,
            'importance': 'high',
            'icon': 'fas fa-layer-group',
            'measurements': [],
            'description': 'Autumn and winter tillering; plant tolerates low temperatures.',
        },
        {
            'key': 'bbch_3',
            'name': 'Stem Elongation',
            'bbch': 'BBCH 3',
            'color': '#ADFF2F',
            'start': (3, 10), 'end': (5, 5), 'year_offset': 0,
            'importance': 'very_high',
            'icon': 'fas fa-arrow-up',
            'measurements': [],
            'description': 'Rapid stem extension; critical stage for yield formation.',
        },
        {
            'key': 'bbch_4',
            'name': 'Booting',
            'bbch': 'BBCH 4',
            'color': '#7CFC00',
            'start': (4, 25), 'end': (5, 25), 'year_offset': 0,
            'importance': 'high',
            'icon': 'fas fa-circle',
            'measurements': [],
            'description': 'Ear forms inside the leaf sheath.',
        },
        {
            'key': 'bbch_5',
            'name': 'Heading',
            'bbch': 'BBCH 5',
            'color': '#FFD700',
            'start': (5, 15), 'end': (6, 10), 'year_offset': 0,
            'importance': 'very_high',
            'icon': 'fas fa-spa',
            'measurements': [],
            'description': 'Ear emergence from leaf sheath; maximum canopy LAI.',
        },
        {
            'key': 'bbch_6',
            'name': 'Flowering',
            'bbch': 'BBCH 6',
            'color': '#FFA500',
            'start': (6, 1), 'end': (6, 25), 'year_offset': 0,
            'importance': 'high',
            'icon': 'fas fa-sun',
            'measurements': [],
            'description': 'Flowering and pollination; heat or drought reduce grain number.',
        },
        {
            'key': 'bbch_7',
            'name': 'Grain Development',
            'bbch': 'BBCH 7',
            'color': '#FF8C00',
            'start': (6, 15), 'end': (7, 15), 'year_offset': 0,
            'importance': 'high',
            'icon': 'fas fa-cube',
            'measurements': [],
            'description': 'Grain filling with starch and protein.',
        },
        {
            'key': 'bbch_8',
            'name': 'Ripening',
            'bbch': 'BBCH 8',
            'color': '#DAA520',
            'start': (7, 5), 'end': (8, 10), 'year_offset': 0,
            'importance': 'medium',
            'icon': 'fas fa-star',
            'measurements': [],
            'description': 'Grain drying; NDVI decreases as maturity progresses.',
        },
        {
            'key': 'bbch_9',
            'name': 'Senescence',
            'bbch': 'BBCH 9',
            'color': '#A0522D',
            'start': (7, 25), 'end': (8, 25), 'year_offset': 0,
            'importance': 'low',
            'icon': 'fas fa-hourglass-end',
            'measurements': [],
            'description': 'Natural plant senescence after harvest.',
        },
    ],

    # ── Spring Barley ──────────────────────────────────────────────────────
    'spring_barley': [
        {
            'key': 'bbch_0',
            'name': 'Germination',
            'bbch': 'BBCH 0',
            'color': '#8B4513',
            'start': (3, 20), 'end': (4, 20), 'year_offset': 0,
            'importance': 'medium',
            'icon': 'fas fa-seedling',
            'measurements': [],
            'description': 'Grain germination after spring sowing.',
        },
        {
            'key': 'bbch_1',
            'name': 'Leaf Development',
            'bbch': 'BBCH 1',
            'color': '#90EE90',
            'start': (4, 10), 'end': (5, 5), 'year_offset': 0,
            'importance': 'medium',
            'icon': 'fas fa-leaf',
            'measurements': [],
            'description': 'Development of successive leaves after emergence.',
        },
        {
            'key': 'bbch_2',
            'name': 'Tillering',
            'bbch': 'BBCH 2',
            'color': '#228B22',
            'start': (4, 25), 'end': (5, 20), 'year_offset': 0,
            'importance': 'high',
            'icon': 'fas fa-layer-group',
            'measurements': [],
            'description': 'Formation of side shoots (spring tillering).',
        },
        {
            'key': 'bbch_3',
            'name': 'Stem Elongation',
            'bbch': 'BBCH 3',
            'color': '#ADFF2F',
            'start': (5, 10), 'end': (6, 10), 'year_offset': 0,
            'importance': 'very_high',
            'icon': 'fas fa-arrow-up',
            'measurements': [],
            'description': 'Rapid stem elongation; fastest biomass accumulation.',
        },
        {
            'key': 'bbch_4',
            'name': 'Booting',
            'bbch': 'BBCH 4',
            'color': '#7CFC00',
            'start': (5, 25), 'end': (6, 20), 'year_offset': 0,
            'importance': 'high',
            'icon': 'fas fa-circle',
            'measurements': [],
            'description': 'Ear forms inside the leaf sheath.',
        },
        {
            'key': 'bbch_5',
            'name': 'Heading',
            'bbch': 'BBCH 5',
            'color': '#FFD700',
            'start': (6, 5), 'end': (6, 28), 'year_offset': 0,
            'importance': 'very_high',
            'icon': 'fas fa-spa',
            'measurements': [],
            'description': 'Ear emergence; maximum canopy cover.',
        },
        {
            'key': 'bbch_6',
            'name': 'Flowering',
            'bbch': 'BBCH 6',
            'color': '#FFA500',
            'start': (6, 15), 'end': (7, 5), 'year_offset': 0,
            'importance': 'high',
            'icon': 'fas fa-sun',
            'measurements': [],
            'description': 'Flowering and pollination.',
        },
        {
            'key': 'bbch_7',
            'name': 'Grain Development',
            'bbch': 'BBCH 7',
            'color': '#FF8C00',
            'start': (6, 25), 'end': (7, 22), 'year_offset': 0,
            'importance': 'high',
            'icon': 'fas fa-cube',
            'measurements': [],
            'description': 'Grain filling.',
        },
        {
            'key': 'bbch_8',
            'name': 'Ripening',
            'bbch': 'BBCH 8',
            'color': '#DAA520',
            'start': (7, 15), 'end': (8, 15), 'year_offset': 0,
            'importance': 'medium',
            'icon': 'fas fa-star',
            'measurements': [],
            'description': 'Grain drying and ripening.',
        },
        {
            'key': 'bbch_9',
            'name': 'Senescence',
            'bbch': 'BBCH 9',
            'color': '#A0522D',
            'start': (8, 5), 'end': (8, 30), 'year_offset': 0,
            'importance': 'low',
            'icon': 'fas fa-hourglass-end',
            'measurements': [],
            'description': 'Natural plant senescence after harvest.',
        },
    ],

    # ── Winter Rapeseed ─────────────────────────────────────
    'rapeseed': [
        {
            'key': 'bbch_0',
            'name': 'Germination',
            'bbch': 'BBCH 0',
            'color': '#8B4513',
            'start': (8, 15), 'end': (9, 15), 'year_offset': -1,
            'importance': 'medium',
            'icon': 'fas fa-seedling',
            'measurements': [],
            'description': 'Rapeseed germination after summer sowing.',
        },
        {
            'key': 'bbch_1',
            'name': 'Leaf Development (Rosette)',
            'bbch': 'BBCH 1',
            'color': '#90EE90',
            'start': (9, 10), 'end': (11, 20), 'year_offset': -1,
            'importance': 'high',
            'icon': 'fas fa-leaf',
            'measurements': [],
            'description': 'Development of leaf rosette before winter.',
        },
        {
            'key': 'bbch_2',
            'name': 'Side Shoot Formation',
            'bbch': 'BBCH 2',
            'color': '#228B22',
            'start': (10, 15), 'end': (12, 1), 'year_offset': -1,
            'importance': 'medium',
            'icon': 'fas fa-layer-group',
            'measurements': [],
            'description': 'Side shoot formation before winter dormancy.',
        },
        {
            'key': 'bbch_3',
            'name': 'Main Stem Elongation',
            'bbch': 'BBCH 3',
            'color': '#ADFF2F',
            'start': (2, 15), 'end': (4, 10), 'year_offset': 0,
            'importance': 'very_high',
            'icon': 'fas fa-arrow-up',
            'measurements': [],
            'description': 'Spring elongation of the main stem after winter dormancy.',
        },
        {
            'key': 'bbch_5',
            'name': 'Flower Bud Development',
            'bbch': 'BBCH 5',
            'color': '#FFD700',
            'start': (3, 15), 'end': (4, 25), 'year_offset': 0,
            'importance': 'very_high',
            'icon': 'fas fa-spa',
            'measurements': [],
            'description': 'Formation of flower buds.',
        },
        {
            'key': 'bbch_6',
            'name': 'Flowering',
            'bbch': 'BBCH 6',
            'color': '#FFA500',
            'start': (4, 10), 'end': (5, 15), 'year_offset': 0,
            'importance': 'very_high',
            'icon': 'fas fa-sun',
            'measurements': [],
            'description': 'Rapeseed flowering; best spectral contrast in satellite imagery.',
        },
        {
            'key': 'bbch_7',
            'name': 'Pod Development',
            'bbch': 'BBCH 7',
            'color': '#FF8C00',
            'start': (5, 10), 'end': (6, 15), 'year_offset': 0,
            'importance': 'high',
            'icon': 'fas fa-cube',
            'measurements': [],
            'description': 'Pod filling and oil accumulation.',
        },
        {
            'key': 'bbch_8',
            'name': 'Ripening',
            'bbch': 'BBCH 8',
            'color': '#DAA520',
            'start': (6, 10), 'end': (7, 15), 'year_offset': 0,
            'importance': 'medium',
            'icon': 'fas fa-star',
            'measurements': [],
            'description': 'Pod drying; harvest timing monitoring.',
        },
        {
            'key': 'bbch_9',
            'name': 'Senescence',
            'bbch': 'BBCH 9',
            'color': '#A0522D',
            'start': (7, 1), 'end': (7, 25), 'year_offset': 0,
            'importance': 'low',
            'icon': 'fas fa-hourglass-end',
            'measurements': [],
            'description': 'Natural plant senescence after harvest.',
        },
    ],

    # ── Corn (Maize) ────────────────────────────────────────────
    'corn': [
        {
            'key': 'bbch_0',
            'name': 'Germination',
            'bbch': 'BBCH 0',
            'color': '#8B4513',
            'start': (4, 20), 'end': (5, 20), 'year_offset': 0,
            'importance': 'medium',
            'icon': 'fas fa-seedling',
            'measurements': [],
            'description': 'Maize germination; soil temperature >10°C required.',
        },
        {
            'key': 'bbch_1',
            'name': 'Leaf Development',
            'bbch': 'BBCH 1',
            'color': '#90EE90',
            'start': (5, 15), 'end': (6, 25), 'year_offset': 0,
            'importance': 'high',
            'icon': 'fas fa-leaf',
            'measurements': [],
            'description': 'Intensive development of successive leaves (V1-V6).',
        },
        {
            'key': 'bbch_3',
            'name': 'Main Stem Elongation',
            'bbch': 'BBCH 3',
            'color': '#ADFF2F',
            'start': (6, 20), 'end': (7, 20), 'year_offset': 0,
            'importance': 'very_high',
            'icon': 'fas fa-arrow-up',
            'measurements': [],
            'description': 'Maximum height increase; best window for biomass measurement.',
        },
        {
            'key': 'bbch_5',
            'name': 'Tasseling',
            'bbch': 'BBCH 5',
            'color': '#FFD700',
            'start': (7, 10), 'end': (8, 5), 'year_offset': 0,
            'importance': 'very_high',
            'icon': 'fas fa-spa',
            'measurements': [],
            'description': 'Tasseling; critical stage for yield determination.',
        },
        {
            'key': 'bbch_6',
            'name': 'Flowering',
            'bbch': 'BBCH 6',
            'color': '#FFA500',
            'start': (7, 20), 'end': (8, 15), 'year_offset': 0,
            'importance': 'high',
            'icon': 'fas fa-sun',
            'measurements': [],
            'description': 'Tassel and cob flowering; drought reduces grain set.',
        },
        {
            'key': 'bbch_7',
            'name': 'Grain Development',
            'bbch': 'BBCH 7',
            'color': '#FF8C00',
            'start': (8, 5), 'end': (9, 15), 'year_offset': 0,
            'importance': 'high',
            'icon': 'fas fa-cube',
            'measurements': [],
            'description': 'Grain filling with starch.',
        },
        {
            'key': 'bbch_8',
            'name': 'Grain Ripening',
            'bbch': 'BBCH 8',
            'color': '#DAA520',
            'start': (9, 10), 'end': (10, 15), 'year_offset': 0,
            'importance': 'medium',
            'icon': 'fas fa-star',
            'measurements': [],
            'description': 'Grain ripening and drying.',
        },
        {
            'key': 'bbch_9',
            'name': 'Senescence',
            'bbch': 'BBCH 9',
            'color': '#A0522D',
            'start': (10, 10), 'end': (11, 5), 'year_offset': 0,
            'importance': 'low',
            'icon': 'fas fa-hourglass-end',
            'measurements': [],
            'description': 'Natural plant senescence after harvest.',
        },
    ],

    # ── Sugar Beet ──────────────────────────────────────────
    'sugar_beet': [
        {
            'key': 'bbch_0',
            'name': 'Germination and Emergence',
            'bbch': 'BBCH 0',
            'color': '#8B4513',
            'start': (3, 20), 'end': (4, 25), 'year_offset': 0,
            'importance': 'medium',
            'icon': 'fas fa-seedling',
            'measurements': [],
            'description': 'Germination and emergence; soil temperature >4°C required.',
        },
        {
            'key': 'bbch_1',
            'name': 'Leaf Development (Rosette)',
            'bbch': 'BBCH 1',
            'color': '#90EE90',
            'start': (4, 20), 'end': (6, 20), 'year_offset': 0,
            'importance': 'high',
            'icon': 'fas fa-leaf',
            'measurements': [],
            'description': 'Intensive development of the leaf rosette.',
        },
        {
            'key': 'bbch_3',
            'name': 'Row Closing',
            'bbch': 'BBCH 3',
            'color': '#ADFF2F',
            'start': (6, 15), 'end': (7, 31), 'year_offset': 0,
            'importance': 'very_high',
            'icon': 'fas fa-arrow-up',
            'measurements': [],
            'description': 'Row closing; maximum radiation interception.',
        },
        {
            'key': 'bbch_4',
            'name': 'Root Development',
            'bbch': 'BBCH 4',
            'color': '#FF8C00',
            'start': (7, 15), 'end': (9, 30), 'year_offset': 0,
            'importance': 'high',
            'icon': 'fas fa-cube',
            'measurements': [],
            'description': 'Beet root growth and sugar accumulation.',
        },
        {
            'key': 'bbch_49',
            'name': 'End of Vegetative Development',
            'bbch': 'BBCH 49',
            'color': '#DAA520',
            'start': (9, 15), 'end': (11, 15), 'year_offset': 0,
            'importance': 'high',
            'icon': 'fas fa-chart-line',
            'measurements': [],
            'description': 'Technological maturity achieved; optimal harvest window.',
        },
    ],

    # ── Potato ───────────────────────────────────────────────────
    'potato': [
        {
            'key': 'bbch_0',
            'name': 'Germination (Sprout Development)',
            'bbch': 'BBCH 0',
            'color': '#8B4513',
            'start': (4, 10), 'end': (5, 15), 'year_offset': 0,
            'importance': 'medium',
            'icon': 'fas fa-seedling',
            'measurements': [],
            'description': 'Tuber sprouting and sprout development; temperature >8°C required.',
        },
        {
            'key': 'bbch_1',
            'name': 'Leaf Development',
            'bbch': 'BBCH 1',
            'color': '#90EE90',
            'start': (5, 10), 'end': (6, 1), 'year_offset': 0,
            'importance': 'medium',
            'icon': 'fas fa-leaf',
            'measurements': [],
            'description': 'Leaf development after emergence.',
        },
        {
            'key': 'bbch_2',
            'name': 'Side Shoot Formation',
            'bbch': 'BBCH 2',
            'color': '#228B22',
            'start': (5, 20), 'end': (6, 15), 'year_offset': 0,
            'importance': 'high',
            'icon': 'fas fa-layer-group',
            'measurements': [],
            'description': 'Side shoot formation and plant architecture development.',
        },
        {
            'key': 'bbch_3',
            'name': 'Main Stem Growth (Row Closing)',
            'bbch': 'BBCH 3',
            'color': '#ADFF2F',
            'start': (6, 1), 'end': (6, 30), 'year_offset': 0,
            'importance': 'very_high',
            'icon': 'fas fa-arrow-up',
            'measurements': [],
            'description': 'Row closing by the developing haulm.',
        },
        {
            'key': 'bbch_4',
            'name': 'Tuber Development',
            'bbch': 'BBCH 4',
            'color': '#7CFC00',
            'start': (6, 15), 'end': (7, 31), 'year_offset': 0,
            'importance': 'very_high',
            'icon': 'fas fa-circle',
            'measurements': [],
            'description': 'Tuber initiation and intensive tuber growth.',
        },
        {
            'key': 'bbch_5',
            'name': 'Flower Bud Development',
            'bbch': 'BBCH 5',
            'color': '#FFD700',
            'start': (6, 25), 'end': (7, 20), 'year_offset': 0,
            'importance': 'high',
            'icon': 'fas fa-spa',
            'measurements': [],
            'description': 'Formation of flower buds.',
        },
        {
            'key': 'bbch_6',
            'name': 'Flowering',
            'bbch': 'BBCH 6',
            'color': '#FFA500',
            'start': (7, 5), 'end': (7, 31), 'year_offset': 0,
            'importance': 'high',
            'icon': 'fas fa-sun',
            'measurements': [],
            'description': 'Potato flowering; late blight monitoring.',
        },
        {
            'key': 'bbch_7',
            'name': 'Fruit Development',
            'bbch': 'BBCH 7',
            'color': '#FF8C00',
            'start': (7, 20), 'end': (8, 20), 'year_offset': 0,
            'importance': 'medium',
            'icon': 'fas fa-cube',
            'measurements': [],
            'description': 'Fruit (berry) development; haulm starts to decline.',
        },
        {
            'key': 'bbch_8',
            'name': 'Ripening',
            'bbch': 'BBCH 8',
            'color': '#DAA520',
            'start': (8, 10), 'end': (9, 20), 'year_offset': 0,
            'importance': 'medium',
            'icon': 'fas fa-star',
            'measurements': [],
            'description': 'Tuber ripening and skin set.',
        },
        {
            'key': 'bbch_9',
            'name': 'Senescence',
            'bbch': 'BBCH 9',
            'color': '#A0522D',
            'start': (9, 10), 'end': (10, 20), 'year_offset': 0,
            'importance': 'low',
            'icon': 'fas fa-hourglass-end',
            'measurements': [],
            'description': 'Natural haulm senescence; tuber harvest.',
        },
    ],
}

# Orbital repeat periods (days) for Central Poland ~52°N
SATELLITE_REPEAT_PERIODS = {
    'Sentinel-2A': 10,
    'Sentinel-2B': 10,
    'Sentinel-2C': 10,
    'Landsat-8': 16,
    'Landsat-9': 16,
}


def build_phases_with_dates(crop_type, season_year):
    """
    Convert PHENOLOGICAL_CALENDAR entries to dicts with actual date objects.
    Handles cross-year phases for winter crops.
    """
    raw_phases = PHENOLOGICAL_CALENDAR.get(crop_type, [])
    phases = []
    for p in raw_phases:
        start_m, start_d = p['start']
        end_m, end_d = p['end']
        year_offset = p.get('year_offset', 0)
        cross_year = p.get('cross_year', False)

        start_y = season_year + year_offset
        if cross_year:
            # Phase starts in start_y and ends in season_year
            start_date = date(start_y, start_m, start_d)
            end_date = date(season_year, end_m, end_d)
        else:
            start_date = date(start_y, start_m, start_d)
            end_date = date(start_y, end_m, end_d)
            if end_date < start_date:
                # End wraps to next year
                end_date = date(start_y + 1, end_m, end_d)

        phase = {k: v for k, v in p.items() if k not in ('start', 'end', 'year_offset', 'cross_year')}
        phase['start_date'] = start_date
        phase['end_date'] = end_date
        phases.append(phase)
    return phases


def get_phase_for_date(phases, check_date):
    """Return the phenological phase active on check_date, or None."""
    for phase in phases:
        if phase['start_date'] <= check_date <= phase['end_date']:
            return phase
    return None


def generate_satellite_calendar_for_season(bbox, season_start, season_end, center_lat, center_lon):
    """
    Generate expected satellite pass dates for the full season.

    Uses Spectator.earth real data for the next ≤7 days,
    then extrapolates using known orbital repeat cycles.
    Returns sorted list of pass dicts.
    """
    today = date.today()

    # --- Fetch real Spectator passes ---
    sp = SpectatorClient()
    real_result = sp.fetch_overpasses(
        bbox,
        satellites=["Sentinel-2A", "Sentinel-2B", "Sentinel-2C", "Landsat-8", "Landsat-9"],
        days_before=0,
        days_after=7,
    )
    real_passes_raw = real_result.get('overpasses', []) if 'error' not in real_result else []

    # Build set of real (date, satellite) pairs to avoid duplicates
    real_set = set()
    all_passes = []
    sat_anchors = {}

    for op in real_passes_raw:
        date_str = op.get('date_only', '')
        sat = op.get('satellite', '')
        if not date_str or not sat:
            continue
        try:
            d = date.fromisoformat(date_str)
        except ValueError:
            continue
        key = (date_str, sat)
        if key not in real_set:
            real_set.add(key)
            all_passes.append({
                'date': date_str,
                'date_obj': d,
                'satellite': sat,
                'acquisition_status': op.get('acquisition_status', 'unknown'),
                'is_real': True,
                'source': 'Spectator.earth',
            })
        if sat not in sat_anchors:
            sat_anchors[sat] = d

    # --- Default anchors for extrapolation (typical Central Poland 2026) ---
    DEFAULT_OFFSETS = {
        'Sentinel-2A': 2,
        'Sentinel-2B': 7,
        'Sentinel-2C': 5,
        'Landsat-8':   3,
        'Landsat-9':  11,
    }

    for sat, period in SATELLITE_REPEAT_PERIODS.items():
        anchor = sat_anchors.get(sat, today + timedelta(days=DEFAULT_OFFSETS.get(sat, 5)))

        # Walk backwards to season_start
        d = anchor
        while d > season_start:
            d -= timedelta(days=period)
        if d < season_start:
            d += timedelta(days=period)

        while d <= season_end:
            date_str = d.isoformat()
            key = (date_str, sat)
            if key not in real_set:
                # Determine acquisition status estimate:
                # Passes within the next 7 days may be verified by Spectator but weren't returned
                days_from_today = (d - today).days
                if 0 <= days_from_today <= 7:
                    acq_status = 'unknown'
                else:
                    acq_status = 'estimated'

                all_passes.append({
                    'date': date_str,
                    'date_obj': d,
                    'satellite': sat,
                    'acquisition_status': acq_status,
                    'is_real': False,
                    'source': 'Orbital repeat cycle estimate',
                })
            d += timedelta(days=period)

    all_passes.sort(key=lambda x: x['date'])
    return all_passes


# ---------------------------------------------------------------------------
# Spectator.earth API client
# ---------------------------------------------------------------------------

class SpectatorClient:
    """
    Client for the Spectator.earth API.

    Key endpoint: /overpass/ — returns satellite passes over a given area,
    including `acquisition` (True / False / None) that tells whether the
    satellite's sensor will actually collect imagery during that pass.

    acquisition = True  → satellite confirmed to acquire image
    acquisition = False → satellite passes but NOT imaging this area
    acquisition = None  → no acquisition plan available for this satellite
    """

    BASE_URL = "https://api.spectator.earth"
    API_KEY = "KqYE8GghNk4axnarArhQ5b"

    # Satellites for which Spectator provides detailed acquisition plans.
    # Other satellites may appear in results but with acquisition=None.
    SUPPORTED_SATELLITES = [
        "Sentinel-1A", "Sentinel-1B", "Sentinel-1C",
        "Sentinel-2A", "Sentinel-2B", "Sentinel-2C",
        "Sentinel-3A", "Sentinel-3B",
        "Landsat-8", "Landsat-9",
    ]

    def _get(self, endpoint, params=None):
        params = params or {}
        params["api_key"] = self.API_KEY
        try:
            r = requests.get(
                f"{self.BASE_URL}/{endpoint}",
                params=params,
                timeout=30,
            )
            r.raise_for_status()
            return r.json()
        except Exception as e:
            return {"error": str(e)}

    # ------------------------------------------------------------------
    # Overpasses
    # ------------------------------------------------------------------

    def fetch_overpasses(self, bbox, satellites=None, days_before=0, days_after=7):
        """
        Fetch satellite overpasses over a bounding box.

        bbox: (min_lon, min_lat, max_lon, max_lat)

        Each returned overpass dict contains:
            date, satellite, acquisition_status, acquisition,
            lat, lon, alt_km, footprints
        """
        params = {
            "bbox": f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}",
            "days_before": days_before,
            "days_after": min(days_after, 7),   # free-plan cap
        }
        if satellites:
            params["satellites"] = (
                ",".join(satellites) if isinstance(satellites, list) else satellites
            )

        data = self._get("overpass/", params)
        if "error" in data:
            return {"overpasses": [], "frequency": None, "error": data["error"]}

        overpasses = []
        for op in data.get("overpasses", []):
            # Determine acquisition status from footprint features
            acquisition = None
            for feat in op.get("footprints", {}).get("features", []):
                acq = feat.get("properties", {}).get("acquisition")
                if acq is True:
                    acquisition = True
                    break
                if acq is False:
                    acquisition = False   # keep looking for True

            # Map to a simple string status for templates
            if acquisition is True:
                acq_status = "imaging"
            elif acquisition is False:
                acq_status = "no_image"
            else:
                acq_status = "unknown"

            # Parse date to a nice display string
            raw_date = op.get("date", "")
            try:
                dt_obj = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
                date_display = dt_obj.strftime("%Y-%m-%d %H:%M:%S UTC")
                date_only = dt_obj.strftime("%Y-%m-%d")
            except Exception:
                date_display = raw_date
                date_only = raw_date[:10] if len(raw_date) >= 10 else raw_date

            # Satellite position
            geom = op.get("geometry", {})
            coords = geom.get("coordinates", []) if geom else []
            lon = coords[0] if len(coords) > 0 else None
            lat = coords[1] if len(coords) > 1 else None
            alt_km = round(coords[2] / 1000, 1) if len(coords) > 2 else None

            overpasses.append({
                "id": op.get("id"),
                "date": raw_date,
                "date_display": date_display,
                "date_only": date_only,
                "satellite": op.get("satellite", ""),
                "acquisition": acquisition,
                "acquisition_status": acq_status,
                "lat": lat,
                "lon": lon,
                "alt_km": alt_km,
                "footprints": op.get("footprints"),
            })

        return {
            "frequency": data.get("frequency"),
            "overpasses": overpasses,
        }
