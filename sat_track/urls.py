from django.urls import path

from . import views
from .views import home, RegistrationView

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', RegistrationView.as_view(), name='register'),
    path('input/', views.satellite_input_view, name='satellite_input'),

]