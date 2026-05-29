from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    path("redirect/", views.redirect_dashboard, name="redirect-dashboard"),
    path("super-admin/", views.super_admin_dashboard, name="super-admin-dashboard"),
    path("supervisor/", views.supervisor_dashboard, name="supervisor-dashboard"),

    path("consultant/", views.consultant_dashboard, name="consultant-dashboard"),
    path("consultant/submissions/", views.consultant_client_submissions, name="client-submissions"),
    path("consultant/audit/client/<int:doc_id>/", views.process_audit_action, name="audit-action"),
    path("consultant/review/client/<int:client_id>/", views.review_client_portfolio, name='review-client'),
    path("consultant/clients/activities/update/<int:activity_id>/", views.update_activity_status, name='update-activity-status'),
    path("consultant/clients/start_project/<int:client_id>/", views.initiate_client_project, name='initiate-project'),
    path("consultant/clients/project_board/<int:project_id>/", views.project_service_board, name="project-board"),
    path("consultant/clients/global_board/", views.global_operations_boards, name="global-boards"),
    path("consultant/clients/project_board/add/<int:project_id>/", views.add_custom_project_subitem, name="add-custom-subitem"),
    path("consultant/clients/",views.consultant_companies_list, name='companies-list'),
    path("consultant/clients/<int:client_id>/overview/",views.consultant_company_overview, name='company-overview'),

    path("ambassador/", views.ambassador_dashboard, name="ambassador-dashboard"),

    path("user/", views.user_dashboard, name="user-dashboard"),
    path("user/profile/", views.user_profile, name="user-profile"),
    path("user/documents/", views.user_documents_vault, name="user-documents"),
    path("user/documents/supplementary/", views.create_supplementary_slot, name="create-supplementary-slot"),
    path("user/documents/supplementary/upload/<int:doc_id>/", views.upload_document_asset, name="upload-asset"),
]
