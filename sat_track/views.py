from django.contrib.auth.hashers import make_password
from django.shortcuts import render
from django.views.generic import CreateView

from sat_track.models import UserAccountModel


def home(request):
    return render(request, 'home.html')

class RegistrationView(CreateView):
    model = UserAccountModel  # Your model for the user, change if necessary
    template_name = 'registration.html'  # The template to render
    success_url = '/'  # Redirect on success, change as needed
    fields = ['email', 'password']

    def form_valid(self, form):
        # Get the cleaned data from the form
        email = form.cleaned_data.get('email')
        password = form.cleaned_data.get('password')

        # Debugging: Check if email exists before saving
        if UserAccountModel.objects.filter(email=email).exists():
            print(f"Email {email} already exists.")  # Debugging print
            form.add_error('email', 'Email already exists. Please use a different email.')
            return self.form_invalid(form)  # Return the form with the error message

        # Hash the password before saving it to the database
        hashed_password = make_password(password)

        # Create the user instance manually (to set the hashed password) and save it
        user = UserAccountModel(email=email, password=hashed_password)  # Creating the user manually
        user.save()  # Save the user with the hashed password

        return super().form_valid(form)