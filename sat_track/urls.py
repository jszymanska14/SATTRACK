from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('input/', views.satellite_input_view, name='satellite_input'),
]