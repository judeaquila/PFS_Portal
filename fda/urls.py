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

    path('dashboard/associate-3/client-submissions/', views.associate_three_client_submissions, name='associate-three-client-submissions'),
    path("dashboard/associate-3/client-documents-review/<int:client_id>/", views.associate_three_review_client_documents, name='associate-three-review-client-documents'),
    path("dashboard/associate-3/client-documents-review/action/<int:doc_id>/", views.associate_three_document_review_action, name="associate-three-document-review-action"),
    path("dashboard/associate-3/client/start_project/<int:client_id>/", views.associate_three_initiate_client_project, name='associate-three-initiate-client-project'),
    path("dashboard/associate-3/client/project_board/<int:project_id>/", views.associate_three_project_board, name="associate-three-project-board"),
    path("dashboard/associate-3/client/global-projects-board/", views.associate_three_global_projects_board, name="associate-three-global-projects-board"),

    # FDA Core Workspace Sheets
    path('matrix/', views.tracker_list_view, name='tracker_list'),
    path('tasks/', views.team_tasks_view, name='team_tasks'),
    path('payments/', views.payment_register_view, name='payment_register'),
]