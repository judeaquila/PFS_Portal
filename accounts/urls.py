from django.urls import path
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
]
