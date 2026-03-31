import requests
from datetime import datetime, timezone as dt_timezone


OPTICAL_SATELLITES = {
    'sentinel-2a': {'norad_id': 40697, 'name': 'Sentinel-2A', 'swath_km': 290},
    'sentinel-2b': {'norad_id': 42063, 'name': 'Sentinel-2B', 'swath_km': 290},
    'landsat-8':   {'norad_id': 39084, 'name': 'Landsat 8',   'swath_km': 185},
    'landsat-9':   {'norad_id': 49260, 'name': 'Landsat 9',   'swath_km': 185},
}

SATELLITE_CHOICES = [
    (key, info['name']) for key, info in OPTICAL_SATELLITES.items()
]


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
