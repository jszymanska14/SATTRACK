from django.urls import path
from . import views
from .views import RegistrationView, SignInView

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', RegistrationView.as_view(), name='register'),
    path('sign-in/', SignInView.as_view(), name='sign_in'),
    path('profile/', views.user_profile, name='profile'),
    path('logout/', views.user_logout, name='logout'),
    path('weather/', views.weather_panel, name='weather_panel'),
    path('calendar/', views.observation_calendar, name='observation_calendar'),
    path('api/calendar-events/', views.calendar_events_api, name='calendar_events_api'),
    path('observation/delete/<int:obs_id>/', views.delete_observation, name='delete_observation'),
    path('event/<int:event_id>/', views.sentinel2_over_bbox, name='event_detail'),
    # Measurement Planning
    path('planner/', views.measurement_planner, name='measurement_planner'),
    path('planner/<int:plan_id>/', views.measurement_plan_detail, name='plan_detail'),
    path('planner/<int:plan_id>/delete/', views.measurement_plan_delete, name='plan_delete'),
    # Spectrometer Viewer
    path('spectrometer/', views.spectrometer_view, name='spectrometer'),
    path('api/spectrometer/upload/', views.spectrometer_upload_api, name='spectrometer_upload_api'),
]
