from django.urls import path
from . import views

app_name = 'exams'

urlpatterns = [
    # Exam CRUD
    path('', views.exam_list, name='exam_list'),
    path('create/', views.create_exam, name='create_exam'),
    path('<int:exam_id>/', views.exam_detail, name='exam_detail'),
    path('<int:exam_id>/edit/', views.edit_exam, name='edit_exam'),
    path('<int:exam_id>/delete/', views.delete_exam, name='delete_exam'),

    # Exam Attendance & Results
    path('<int:exam_id>/attendance/', views.exam_attendance, name='exam_attendance'),
    path('<int:exam_id>/results/', views.exam_results_entry, name='exam_results_entry'),
    path('<int:exam_id>/publish/', views.publish_results, name='publish_results'),

    # AJAX
    path('ajax/sections/', views.get_sections_for_class, name='get_sections_for_class'),

    # Reports
    path('reports/', views.exam_report, name='exam_report'),
    path('reports/student/<int:student_id>/', views.student_result_report, name='student_result_report'),
]
