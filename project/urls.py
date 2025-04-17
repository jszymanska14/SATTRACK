"""
URL configuration for project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include

from sat_track import views
from sat_track.views import RegistrationView, SignInView, user_profile

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('sat_track.urls')),path('register/', RegistrationView.as_view(), name='register'),
    path('login/', SignInView.as_view(), name='login'),
    path('profile/', user_profile, name='profile'),
    path('event/<int:event_id>/', views.event_detail, name='event_detail'),

]

