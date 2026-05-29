from django.shortcuts import render

# PURE HTML Page Test
def monday_dashboard(request):
    return render(request, 'common/index.html')