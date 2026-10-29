from django.urls import path
from . import views

app_name = 'bookings'

urlpatterns = [
    path('dashboard/associate-2/availability/', views.associate_two_availability_list, name='associate-two-availability'),
    path('dashboard/associate-2/availability/create/', views.associate_two_create_slot, name='associate-two-create-slot'),
    path('dashboard/associate-2/availability/bulk/', views.associate_two_bulk_create_slots, name='associate-two-bulk-slots'),
    path('dashboard/associate-2/availability/<int:slot_id>/delete/', views.associate_two_delete_slot, name='associate-two-delete-slot'),
    path('dashboard/associate-2/appointments/', views.associate_two_appointments_list, name='associate-two-appointments'),
    path('dashboard/associate-2/appointments/<int:appointment_id>/', views.associate_two_appointment_detail, name='associate-two-appointment-detail'),
    path('dashboard/associate-2/appointments/<int:appointment_id>/action-item/add/', views.associate_two_add_action_item, name='associate-two-add-action-item'),
    path('dashboard/associate-2/action-item/<int:item_id>/toggle/', views.associate_two_toggle_action_item, name='associate-two-toggle-action-item'),
    path('dashboard/associate-2/action-item/<int:item_id>/delete/', views.associate_two_delete_action_item, name='associate-two-delete-action-item'),
    path('dashboard/associate-2/projects/', views.associate_two_projects_list, name='associate-two-projects-list'),

    path('dashboard/associate-2/initiate-project/', views.associate_two_initiate_project, name='associate-two-initiate-project'),
    path('dashboard/associate-2/initiate-project/<int:client_id>/', views.associate_two_initiate_project, name='associate-two-initiate-project-client'),
    path('dashboard/associate-2/project/<int:project_id>/', views.associate_two_project_detail, name='associate-two-project-detail'),
    path('dashboard/associate-2/activity/<int:activity_id>/update/', views.update_project_activity_status, name='update-project-activity-status'),
    path('dashboard/associate-2/project/<int:project_id>/edit/', views.associate_two_edit_project, name='associate-two-edit-project'),
    path('dashboard/associate-2/project/<int:project_id>/delete/', views.associate_two_delete_project, name='associate-two-delete-project'),
    path('dashboard/associate-2/packages/comparison-matrix/', views.package_comparison_matrix_view, name='package-comparison-matrix'),

    path('booking/', views.client_booking_view, name='client-booking'),
    path('booking/<int:slot_id>/', views.client_confirm_booking, name='client-confirm-booking'),
    path('booking/my-appointments/', views.client_booking_dashboard, name='client-booking-dashboard'),
    path('booking/my-appointments/<int:appointment_id>/', views.client_appointment_detail, name='client-appointment-detail'),


    path('notifications/unread-count/', views.unread_notifications_count, name='unread_notifications_count'),
    path('notifications/mark-as-read/', views.mark_notifications_as_read, name='mark_notifications_as_read'),
]