from django.urls import path
from . import views

app_name = "payments"

urlpatterns = [
    path(
        "initiate/<str:package_code>/",
        views.initiate_package_payment,
        name="initiate-payment",
    ),
    path(
        "verify/<str:ref>/",
        views.verify_payment,
        name="verify-payment",
    ),
    path(
        "success/",
        views.booking_success,
        name="booking-success",
    ),
]