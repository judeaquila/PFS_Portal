from django.urls import path
from . import views

app_name = 'fda'

urlpatterns = [
    # Dashboard Routes per Associate Tier
    path('dashboard/associate-1/', views.associate_one_dashboard, name='associate-one-dashboard'),
    path('dashboard/associate-2/', views.associate_two_dashboard, name='associate-two-dashboard'),
    path('dashboard/associate-3/', views.associate_three_dashboard, name='associate-three-dashboard'),
    path('dashboard/associate-4/', views.associate_four_dashboard, name='associate-four-dashboard'),
    path('dashboard/associate-5/', views.associate_five_dashboard, name='associate-five-dashboard'),

    # FDA Core Workspace Sheets
    path('matrix/', views.tracker_list_view, name='tracker_list'),
    path('tasks/', views.team_tasks_view, name='team_tasks'),
    path('payments/', views.payment_register_view, name='payment_register'),
]