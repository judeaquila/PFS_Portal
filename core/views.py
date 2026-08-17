from django.shortcuts import render
from common.decorators import restrict_to_regular_users


@restrict_to_regular_users
def home(request):
    return render(request, 'core/index.html')

@restrict_to_regular_users
def pricing(request):
    return render(request, 'core/pricing.html')

@restrict_to_regular_users
def journey(request):
    return render(request, 'core/journey.html')

@restrict_to_regular_users
def about(request):
    return render(request, 'core/about.html')

@restrict_to_regular_users
def services(request):
    return render(request, 'core/services.html')

@restrict_to_regular_users
def ambassadors(request):
    return render(request, 'core/ambassadors.html')

@restrict_to_regular_users
def consultants(request):
    return render(request, 'core/consultants.html')

@restrict_to_regular_users
def contact(request):
    return render(request, 'core/contact.html')

@restrict_to_regular_users
def faq(request):
    return render(request, 'core/faq.html')