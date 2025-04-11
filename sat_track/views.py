from django.contrib.auth.hashers import make_password
from django.http import JsonResponse
from django.shortcuts import render
from django.views.generic import CreateView
from .forms import SatelliteForm
from django.urls import reverse_lazy


from sat_track.models import UserAccountModel


def home(request):
    return render(request, 'home.html')


def user_profile(request):
    return render(request, 'user_profile.html')


def satellite_input_view(request):
    if request.method == 'POST':
        form = SatelliteForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            return render(request, 'result.html', {'data': data})
    else:
        form = SatelliteForm()
    return render(request, 'form.html', {'form': form})


class RegistrationView(CreateView):
    model = UserAccountModel  # Your model for the user, change if necessary
    template_name = 'registration.html'  # The template to render
    success_url = reverse_lazy('profile')  # Redirect to /profile/
    fields = ['email', 'password']

    def form_valid(self, form):
        email = form.cleaned_data.get('email')
        password = form.cleaned_data.get('password')

        if UserAccountModel.objects.filter(email=email).exists():
            form.add_error('email', 'Ten e-mail jest już zarejestrowany. Proszę użyj innego adresu.')
            return self.form_invalid(form)
        # Hash the password before saving it to the database
        hashed_password = make_password(password)

        # Create the user instance manually (to set the hashed password) and save it
        user = UserAccountModel(email=email, password=hashed_password)  # Creating the user manually
        user.save()  # Save the user with the hashed password

        return super().form_valid(form)
