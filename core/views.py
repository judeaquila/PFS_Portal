from django.shortcuts import render

# Create your views here.
def home(request):
    return render(request, 'core/index.html')

def pricing(request):
    return render(request, 'core/pricing.html')

def journey(request):
    return render(request, 'core/journey.html')

def about(request):
    return render(request, 'core/about.html')

def services(request):
    return render(request, 'core/services.html')

def ambassadors(request):
    return render(request, 'core/ambassadors.html')

def consultants(request):
    return render(request, 'core/consultants.html')

def contact(request):
    return render(request, 'core/contact.html')

def faq(request):
    return render(request, 'core/faq.html')