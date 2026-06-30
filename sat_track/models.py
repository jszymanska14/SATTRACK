import json
from django.db import models


class UserAccountModel(models.Model):
    email = models.CharField(max_length=65, unique=True)
    username = models.CharField(max_length=50, blank=True, null=True)
    password = models.CharField(max_length=255, blank=True, null=True)
    provider = models.CharField(max_length=20, default='local')
    provider_id = models.CharField(max_length=255, blank=True, null=True)
    avatar_url = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.username or self.email


class Event(models.Model):
    timestamp = models.DateTimeField()
    area_geojson = models.TextField()
    satellite_key = models.CharField(max_length=30, default='sentinel-2a')
    user = models.ForeignKey(
        UserAccountModel, on_delete=models.SET_NULL, null=True, blank=True
    )

    def __str__(self):
        return f"Event #{self.pk} - {self.timestamp}"


class Observation(models.Model):
    user = models.ForeignKey(
        UserAccountModel, on_delete=models.CASCADE, related_name='observations'
    )
    latitude = models.FloatField()
    longitude = models.FloatField()
    date = models.DateField()
    time = models.TimeField()
    satellite_name = models.CharField(max_length=100)
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-time']

    def __str__(self):
        return f"{self.satellite_name} - {self.date} {self.time}"


class MeasurementPlan(models.Model):
    CROP_CHOICES = [
        ('winter_wheat', 'Winter Wheat'),
        ('spring_barley', 'Spring Barley'),
        ('rapeseed', 'Winter Rapeseed'),
        ('corn', 'Corn (Maize)'),
        ('sugar_beet', 'Sugar Beet'),
        ('potato', 'Potato'),
    ]

    user = models.ForeignKey(
        UserAccountModel, on_delete=models.CASCADE, related_name='measurement_plans'
    )
    name = models.CharField(max_length=100)
    crop_type = models.CharField(max_length=30, choices=CROP_CHOICES, default='winter_wheat')
    season_year = models.IntegerField(default=2026)
    area_geojson = models.TextField(blank=True, default='')
    fields_json = models.TextField(blank=True, default='[]')
    home_lat = models.FloatField(null=True, blank=True)
    home_lon = models.FloatField(null=True, blank=True)
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.get_crop_type_display()}, {self.season_year})"

    def get_fields(self):
        try:
            return json.loads(self.fields_json) if self.fields_json else []
        except Exception:
            return []

    def get_area_center(self):
        """Returns (lat, lon) center of the area or fields."""
        if self.area_geojson:
            try:
                data = json.loads(self.area_geojson)
                coords = data.get('geometry', data).get('coordinates', [[]])[0]
                lats = [c[1] for c in coords]
                lons = [c[0] for c in coords]
                if lats:
                    return sum(lats) / len(lats), ((sum(lons) / len(lons) + 180) % 360) - 180
            except Exception:
                pass
        fields = self.get_fields()
        if fields:
            lats = [f['lat'] for f in fields]
            lons = [f['lon'] for f in fields]
            return sum(lats) / len(lats), sum(lons) / len(lons)
        return 52.0, 20.0  # Default: central Poland
