from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from .forms import LoginForm, RegistrationForm, AmbassadorRegistrationForm, ConsultantRegistrationForm
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods


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
            user = form.save()
            
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
            next_url = request.GET.get('next') or 'dashboard:redirect-dashboard'
            return redirect(next_url)
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
@require_http_methods(["GET", "POST"])
def logout_view(request):
    """
    Logs out the user and safely drops them back at the home landing page.
    """
    logout(request)
    return redirect("core:home")


def ambassador_register(request):
    """
    Handles Ambassador registration. Automatically enforces the 'AMBASSADOR' role
    and redirects to the appropriate dashboard workspace.
    """
    if request.user.is_authenticated:
        return redirect('dashboard:ambassador-dashboard')

    if request.method == 'POST':
        form = AmbassadorRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend='accounts.backends.EmailBackend')
            return redirect('dashboard:ambassador-dashboard')
    else:
        form = AmbassadorRegistrationForm()

    context = {
        "form": form,
    }

    return render(request, 'registration/ambassador_register.html', context)


def consultant_register(request):
    """
    Handles Consultant registration. Automatically maps the secure 
    CONSULTANT role via the model form save architecture.
    """
    if request.user.is_authenticated:
        return redirect('dashboard:consultant-dashboard')

    if request.method == 'POST':
        form = ConsultantRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            login(request, user, backend='accounts.backends.EmailBackend')
            return redirect('dashboard:consultant-dashboard')
    else:
        form = ConsultantRegistrationForm()

    return render(request, 'registration/consultant_register.html', {"form": form})
