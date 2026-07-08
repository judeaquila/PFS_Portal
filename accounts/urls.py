from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.register_view, name="register"),

    # Ambassador
    path('login/ambassador/', views.ambassador_login, name="ambassador-login"),
    path('register/ambassador/', views.ambassador_register, name="ambassador-register"),

    # Consultant
    path('login/consultant', views.consultant_login, name="consultant-login"),
    path('register/consultant', views.consultant_register, name="consultant-register"),
]
