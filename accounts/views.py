from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from .forms import LoginForm, RegistrationForm
from .models import UserRole
from django.contrib.auth.decorators import login_required


def register_view(request):
    """
    Handles user registration. Automatically enforces the 'USER' role
    and redirects to the payment-complete/account setup pipeline.
    """
    if request.user.is_authenticated:
        return redirect('dashboard:redirect-dashboard')

    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = UserRole.USER
            user.save()
            
            # Log the user in immediately after successful registration
            login(request, user, backend='accounts.backends.EmailBackend')
            return redirect('dashboard:redirect-dashboard')
    else:
        form = RegistrationForm()

    context = {
        "form": form,
    }

    return render(request, 'registration/register.html', context)


def login_view(request):
    """
    Handles secure client and staff login using the custom LoginForm.
    """
    if request.user.is_authenticated:
        return redirect('dashboard:redirect-dashboard')

    error_message = None

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            # Retrieve the authenticated user attached during form cleaning
            user = form.cleaned_data.get('user')
            login(request, user, backend='accounts.backends.EmailBackend')
            return redirect('dashboard:redirect-dashboard')
        else:
            # Safely grab the validation error string
            error_message = form.non_field_errors().as_text() or "Invalid email or password."
    else:
        form = LoginForm()

    context = {
        "form": form,
        "error_message": error_message,
    }

    return render(request, "registration/login.html", context)

@login_required
def logout_view(request):
    """
    Logs out the user and safely drops them back at the home landing page.
    """
    logout(request)
    return redirect("core:home")