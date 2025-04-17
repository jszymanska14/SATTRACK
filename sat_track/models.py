
from django.db import models

class UserAccountModel(models.Model):
    id = models.IntegerField(primary_key=True)
    email = models.CharField(max_length=65)
    password = models.CharField(max_length=255)

class Event(models.Model):
    timestamp = models.DateTimeField()
    area_geojson = models.TextField()