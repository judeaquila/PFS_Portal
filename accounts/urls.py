from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.register_view, name="register"),

    # Associate
    path('register/associate/', views.ambassador_register, name="ambassador-register"),

    # Consultant
    path('register/consultant', views.consultant_register, name="consultant-register"),

    # Password Reset
    path("password-reset/", views.password_reset_request_view, name="password_reset"),
    path("password-reset/done/", views.password_reset_done_view, name="password_reset_done"),
    path("reset/<uidb64>/<token>/", views.password_reset_confirm_view, name="password_reset_confirm"),
    path("reset/done/", views.password_reset_complete_view, name="password_reset_complete"),
]
