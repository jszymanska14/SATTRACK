import json

from django.contrib.auth import authenticate, login
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth.views import LoginView
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View
from django.views.generic import CreateView
from .forms import SatelliteForm
from django.urls import reverse_lazy
from django.shortcuts import redirect



from sat_track.models import UserAccountModel


def home(request):
    return render(request, 'home.html')

#TODO dać to gdzieś sensownie pewnie do klasy USER?
def user_profile(request):
    return render(request, 'user_profile.html')

def user_logout(request):
    request.session.flush()  # clear all session data
    return redirect('home')  # or 'home' if you'd prefer


def satellite_input_view(request):
    if request.method == 'POST':
        form = SatelliteForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            return render(request, 'result.html', {'data': data})
    else:
        form = SatelliteForm()
    return render(request, 'form.html', {'form': form})


# class RegistrationView(CreateView):
#     model = UserAccountModel  # Your model for the user, change if necessary
#     template_name = 'registration.html'  # The template to render
#     success_url = reverse_lazy('profile')  # Redirect to /profile/
#     fields = ['email', 'password']
#
#     def form_valid(self, form):
#         email = form.cleaned_data.get('email')
#         password = form.cleaned_data.get('password')
#
#         if UserAccountModel.objects.filter(email=email).exists():
#             form.add_error('email', 'Ten e-mail jest już zarejestrowany. Proszę użyj innego adresu.')
#             return self.form_invalid(form)
#
#         # Hash password and create user manually
#         hashed_password = make_password(password)
#         self.object = UserAccountModel(email=email, password=hashed_password)
#         self.object.save()
#
#         return JsonResponse({
#             'status': 'success',
#             'redirect_url': str(reverse_lazy('profile'))
#         })

class RegistrationView(View):
    def post(self, request):
        data = json.loads(request.body)
        email = data.get("email")
        password = data.get("password")
        confirm_password = data.get("confirm_password")

        if UserAccountModel.objects.filter(email=email).exists():
            return JsonResponse({
                "status": "error",
                "field": "email",
                "message": "Ten e-mail jest już zarejestrowany."
            }, status=400)

        hashed_password = make_password(password)
        user = UserAccountModel(email=email, password=hashed_password)
        user.save()

        request.session["user_id"] = user.id
        request.session["user_email"] = user.email

        return JsonResponse({
            "status": "success",
            "redirect_url": str(reverse_lazy("profile"))
        })

    def get(self, request):
        return render(request, "registration.html")

class SignInView(View):
    def post(self, request):
            data = json.loads(request.body)
            print("DEBUG DATA:", data)

            email = data.get('email')
            password = data.get('password')

            try:
                user = UserAccountModel.objects.get(email=email)
            except UserAccountModel.DoesNotExist:
                return JsonResponse({
                    "status": "error",
                    "field": "email",
                    "message": "Nie znaleziono użytkownika o podanym adresie e-mail."
                }, status=400)

            if not check_password(password, user.password):
                return JsonResponse({
                    "status": "error",
                    "field": "password",
                    "message": "Nieprawidłowe hasło."
                }, status=400)

            # Simulate a session manually
            request.session["user_id"] = user.id
            request.session["user_email"] = user.email

            return JsonResponse({
                "status": "success",
                "redirect_url": str(reverse_lazy("profile"))
            })



    def get(self, request):
        # Just render the HTML page for non-AJAX GET requests
        return render(request, 'sign_in.html')