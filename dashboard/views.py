from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from accounts.models import UserRole
from common.decorators import role_required

# Dashboard Redirect
@login_required
def redirect_dashboard(request):
    user = request.user
    role = str(user.role)

    if role == UserRole.SUPER_ADMIN:
        return redirect("dashboard:super-admin-dashboard")
    
    elif role == UserRole.SUPERVISOR:
        return redirect("dashboard:supervisor-dashboard")
    
    elif role == UserRole.CONSULTANT:
        return redirect("dashboard:consultant-dashboard")
    
    elif role == UserRole.USER:
        return redirect("dashboard:user-dashboard")
    
    raise PermissionError("You do not have a valid role assigned!")


# SUPER ADMIN Dashboard
@login_required
@role_required([UserRole.SUPER_ADMIN])
def super_admin_dashboard(request):
    return render(request, "dashboards/super_admin.html")


# SUPERVISOR Dashboard
@login_required
@role_required([UserRole.SUPERVISOR])
def supervisor_dashboard(request):
    return render(request, "dashboards/supervisor.html")


# CONSULTANT Dashboard
@login_required
@role_required([UserRole.CONSULTANT])
def consultant_dashboard(request):
    return render(request, "dashboards/consultant.html")


# USER Dashboard
@login_required
@role_required([UserRole.USER])
def user_dashboard(request):
    return render(request, "dashboards/user.html")