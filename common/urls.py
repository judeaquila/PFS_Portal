from django.urls import path
from . import views

urlpatterns = [
    path("", views.monday_dashboard, name="test-page"),
]
