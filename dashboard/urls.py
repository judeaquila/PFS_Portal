from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    path("redirect/", views.redirect_dashboard, name="redirect-dashboard"),

    path("super-admin/", views.superadmin_dashboard, name="super-admin-dashboard"),
    path('super-admin/associates/', views.superadmin_ambassadors, name='superadmin-ambassadors'),
    path('super-admin/associates/verify/<int:profile_id>/<str:action>/', views.superadmin_process_verification, name='superadmin-process-verification'),
    path('super-admin/consultants/', views.superadmin_consultants, name="superadmin-consultants"),
    path('super-admin/consultants/verify/<int:profile_id>/<str:action>/', views.superadmin_consultant_verification, name="superadmin-consultant-verification"),
    path('super-admin/users/', views.admin_user_list, name='admin-user-list'),
    path('super-admin/users/<int:pk>/', views.admin_user_detail, name='admin-user-detail'),
    path('super-admin/users/<int:pk>/edit/', views.admin_user_update, name='admin-user-update'),
    path('super-admin/users/<int:pk>/toggle-active/', views.admin_user_toggle_active, name='admin-user-toggle-active'),
    path('super-admin/users/<int:pk>/delete/', views.admin_user_delete, name='admin-user-delete'),

    path("supervisor/", views.supervisor_dashboard, name="supervisor-dashboard"),

    path("consultant/", views.consultant_dashboard, name="consultant-dashboard"),
    path("consultant/submissions/", views.consultant_client_submissions, name="client-submissions"),
    path("consultant/audit/client/<int:doc_id>/", views.process_audit_action, name="audit-action"),
    path("consultant/review/client/<int:client_id>/", views.review_client_portfolio, name='review-client'),
    path("consultant/clients/activities/update/<int:activity_id>/", views.update_activity_status, name='update-activity-status'),
    path("consultant/clients/start_project/<int:client_id>/", views.initiate_client_project, name='initiate-project'),
    path("consultant/clients/project_board/<int:project_id>/", views.project_service_board, name="project-board"),
    path("consultant/clients/global_board/", views.global_operations_boards, name="global-boards"),
   # path("consultant/clients/project_board/add/<int:project_id>/", views.add_custom_project_subitem, name="add-custom-subitem"),
    path("consultant/clients/",views.consultant_companies_list, name='companies-list'),
    path("consultant/clients/<int:client_id>/overview/",views.consultant_company_overview, name='company-overview'),
    path("consultant/profile", views.consultant_profile, name="consultant-profile"),
    path("consultant/availability", views.consultant_availability, name="consultant-availability"),
    path("consultant/availability/<int:pk>/edit/", views.edit_availability, name="edit-consultant-availability"),
    path("consultant/availability/<int:pk>/delete/", views.delete_availability, name="delete-consultant-availability"),

    path("associate/", views.ambassador_dashboard, name="ambassador-dashboard"),
    path('associate/board/', views.ambassador_dashboard, name='ambassador-boards'),
   # path('associate/claim/', views.ambassador_claim_client, name='ambassador-claim-client'),
    path('associate/clients/', views.ambassador_clients, name='ambassador-clients'),
    path('associate/clients/workbench/<int:client_id>/', views.ambassador_client_workbench, name='ambassador-client-workbench'),
    path('associate/toggle/<int:assignment_id>/', views.ambassador_toggle_complete, name='ambassador-toggle-complete'),
    path('associate/profile/', views.ambassador_profile, name='ambassador-profile'),
    path("associate/availability/", views.associate_availability, name="associate-availability"),
    path("associate/availability/<int:pk>/edit/", views.associate_edit_availability, name="edit-associate-availability"),
    path("associate/availability/<int:pk>/delete/", views.associate_delete_availability, name="delete-associate-availability"),

    path("user/", views.user_dashboard, name="user-dashboard"),
    path("user/profile/", views.user_profile, name="user-profile"),
    path('user/business-profile/', views.business_profile_view, name='business-profile'),
    path("user/documents/", views.user_documents_vault, name="user-documents"),
    path("user/documents/supplementary/", views.create_supplementary_slot, name="create-supplementary-slot"),
    path("user/documents/supplementary/upload/<int:doc_id>/", views.upload_document_asset, name="upload-asset"),
    path('user/projects/<int:project_id>/', views.client_project_dashboard, name='user-project-dashboard'),
    path('user/my-associate/', views.assigned_associate_detail, name='assigned-associate-detail'),
    path('user/associate/assignment/<int:assignment_id>/complete/', views.user_toggle_assignment_completion, name='user-toggle-assignment-complete'),
    path('user/associate/assignment/<int:assignment_id>/cancel/', views.user_request_change_associate, name='user-request-change-associate'),
]
