# sat_track/apis/n2yo_client.py
import requests

class N2YOTLEFetcher:
    BASE_URL = "https://api.n2yo.com/rest/v1/satellite"
    API_KEY = "9KS9FZ-ZUQC5U-QLTE6P-5HQX"  # ← zamień na swój klucz

    def __init__(self, sat_id):
        self.sat_id = sat_id

    def fetch_tle(self):
        url = f"{self.BASE_URL}/tle/{self.sat_id}&apiKey={self.API_KEY}"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            tle_lines = data["tle"].split("\r\n")
            return {
                "line1": tle_lines[0],
                "line2": tle_lines[1],
                "satname": data["info"]["satname"]
            }
        except Exception as e:
            return {
                "error": f"Błąd pobierania TLE: {e}"
            }
