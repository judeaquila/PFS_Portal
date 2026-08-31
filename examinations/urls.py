from django.urls import path
from . import views

app_name = 'examination'

urlpatterns = [
    # Super Admin Global Questions
    path('super-admin/questions/', views.question_list, name='question_list'),
    path('super-admin/questions/add/', views.general_question_create, name='general_question_create'),
    path('super-admin/questions/<int:pk>/edit/', views.question_update, name='question_update'),
    path('super-admin/questions/<int:pk>/delete/', views.question_delete, name='question_delete'),

    # Super Admin Exams
    path('super-admin/exams/', views.exam_list, name='exam_list'),
    path('super-admin/exams/add/', views.exam_create, name='exam_create'),
    path('super-admin/exams/<int:exam_id>/toggle-lock/', views.exam_toggle_lock, name='exam_toggle_lock'),

    # Super Admin Exam-Specific Questions
    path('super-admin/exams/<int:exam_id>/questions/', views.exam_question_list, name='exam_question_list'),
    path('super-admin/exams/<int:exam_id>/questions/add/', views.question_create, name='question_create'),
    path('super-admin/exams/<int:exam_id>/questions/bulk-upload/', views.question_bulk_upload, name='question_bulk_upload'),
    path('super-admin/questions/sample-csv/', views.download_sample_question_csv, name='download_sample_question_csv'),

    # Supervisor Exams
    path('supervisor/exams/', views.supervisor_exam_list, name='supervisor_exam_list'),
    path('supervisor/exams/add/', views.supervisor_exam_create, name='supervisor_exam_create'),
    path('supervisor/exams/<int:exam_id>/toggle-lock/', views.supervisor_exam_toggle_lock, name='supervisor_exam_toggle_lock'),

    # Supervisor Global Questions
    path('supervisor/questions/', views.supervisor_question_list, name='supervisor_question_list'),
    path('supervisor/questions/add/', views.supervisor_general_question_create, name='supervisor_general_question_create'),
    path('supervisor/questions/<int:pk>/edit/', views.supervisor_question_update, name='supervisor_question_update'),
    path('supervisor/questions/<int:pk>/delete/', views.supervisor_question_delete, name='supervisor_question_delete'),

    # Supervisor Exam-Specific Questions
    path('supervisor/exams/<int:exam_id>/questions/', views.supervisor_exam_question_list, name='supervisor_exam_question_list'),
    path('supervisor/exams/<int:exam_id>/questions/add/', views.supervisor_question_create, name='supervisor_question_create'),
    path('supervisor/exams/<int:exam_id>/questions/bulk-upload/', views.supervisor_question_bulk_upload, name='supervisor_question_bulk_upload'),

    # Associate Routes
    path('associate/examinations/', views.exam_landing, name='ambassador_landing'),
    path('associate/examinations/<int:exam_id>/take/', views.take_exam, name='take_exam'),
    path('associate/examinations/<int:exam_id>/submit/', views.submit_exam, name='submit_exam'),
]