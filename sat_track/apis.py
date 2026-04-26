import json
import requests
from datetime import datetime, timezone as dt_timezone


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
    # ── Non-imaging (dla porównania) ──────────────────────────────────────────
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
