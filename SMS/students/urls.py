from django.urls import path
from . import views

app_name = 'students'

urlpatterns = [
    # Student URLs
    path('', views.student_list, name='student_list'),
    path('create/', views.create_student_wizard, name='create_student_wizard'),
    path('<int:student_id>/', views.student_detail, name='student_detail'),
    path('<int:student_id>/edit/', views.edit_student, name='edit_student'),
    path('<int:student_id>/delete/', views.delete_student, name='delete_student'),
    
    # Parent URLs
    path('parents/', views.parent_list, name='parent_list'),
    path('parents/<int:parent_id>/', views.parent_detail, name='parent_detail'),
    path('parents/<int:parent_id>/edit/', views.edit_parent, name='edit_parent'),
    
    # AJAX endpoints
    path('ajax/get-sections/', views.get_sections_by_class, name='get_sections'),
]