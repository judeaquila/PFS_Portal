from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from .forms import LoginForm
from .models import UserRole

# Login View
def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard:redirect-dashboard")
    
    form = LoginForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            user = form.cleaned_data["user"]
            login(request, user)
            return redirect("dashboard:redirect-dashboard")
        
    context = {
        "form": form,
    }

    return render(request, "registration/login.html", context)


# Logout View
def logout_view(request):
    logout(request)
    return redirect("accounts:login")