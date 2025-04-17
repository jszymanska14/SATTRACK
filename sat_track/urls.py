from django.urls import path

from . import views
from .views import RegistrationView, SignInView, user_logout, weather_panel

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', RegistrationView.as_view(), name='register'),
    path('sign-in/', SignInView.as_view(), name='sign_in'),
    path('profile/', views.user_profile, name='profile'),
    path('logout/', user_logout, name='logout'),
    path('weather/', weather_panel, name='weather_panel'),

]