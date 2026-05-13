from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    path("redirect/", views.redirect_dashboard, name="redirect-dashboard"),
    path("super-admin/", views.super_admin_dashboard, name="super-admin-dashboard"),
    path("supervisor/", views.supervisor_dashboard, name="supervisor-dashboard"),
    path("consultant/", views.consultant_dashboard, name="consultant-dashboard"),
    path("user/", views.user_dashboard, name="user-dashboard"),
]
