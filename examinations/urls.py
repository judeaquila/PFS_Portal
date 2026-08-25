from django.urls import path
from . import views

app_name = 'examination'

urlpatterns = [
    path('super-admin/questions/', views.question_list, name='question_list'),
    path('super-admin/questions/add/', views.question_create, name='question_create'),
    path('super-admin/questions/<int:pk>/edit/', views.question_update, name='question_update'),
    path('super-admin/questions/<int:pk>/delete/', views.question_delete, name='question_delete'),

    path('supervisor/questions/', views.supervisor_question_list, name='supervisor_question_list'),
    path('supervisor/questions/add/', views.supervisor_question_create, name='supervisor_question_create'),
    path('supervisor/questions/<int:pk>/edit/', views.supervisor_question_update, name='supervisor_question_update'),
    path('supervisor/questions/<int:pk>/delete/', views.supervisor_question_delete, name='supervisor_question_delete'),

    path('associate/examinations/', views.exam_landing, name='ambassador_landing'),
    path('associate/examinations/take/', views.take_exam, name='take_exam'),
    path('associate/examinations/submit/', views.submit_exam, name='submit_exam'),
]