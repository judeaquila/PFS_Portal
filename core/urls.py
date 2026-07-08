from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    path('', views.home, name="home"),
    path('pricing/', views.pricing, name="pricing"),
    path('journey/', views.journey, name="journey"),
    path('about/', views.about, name="about"),
    path('services/', views.services, name="services"),
    path('ambassadors/', views.ambassadors, name="ambassadors"),
    path('consultants/', views.consultants, name="consultants"),
    path('contact/', views.contact, name="contact"),
    path('faqs/', views.faq, name="faq"),
]
