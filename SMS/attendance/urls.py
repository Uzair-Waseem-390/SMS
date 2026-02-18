from django.urls import path
from . import views

app_name = 'attendance'

urlpatterns = [
    # Student Attendance
    path('students/section/<int:section_id>/', views.bulk_student_attendance, name='bulk_student_attendance'),
    path('students/<int:student_id>/', views.individual_student_attendance, name='individual_student_attendance'),
    path('students/section/<int:section_id>/report/', views.student_attendance_report, name='student_attendance_report'),

    # Staff Attendance
    path('staff/', views.bulk_staff_attendance, name='bulk_staff_attendance'),
    path('staff/<int:user_id>/', views.individual_staff_attendance, name='individual_staff_attendance'),
    path('staff/report/', views.staff_attendance_report, name='staff_attendance_report'),
]
