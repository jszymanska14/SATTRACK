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
