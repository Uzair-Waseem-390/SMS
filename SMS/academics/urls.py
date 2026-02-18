from django.urls import path
from . import views

app_name = 'academics'

urlpatterns = [
    # Class Management
    path('classes/', views.class_list, name='class_list'),
    path('classes/create/', views.create_class_wizard, name='create_class_wizard'),
    path('classes/<int:class_id>/edit/', views.edit_class, name='edit_class'),
    path('classes/<int:class_id>/delete/', views.delete_class, name='delete_class'),
    
    # Section Management
    path('sections/', views.section_list, name='section_list'),
    path('sections/class/<int:class_id>/', views.section_list, name='sections_by_class'),
    path('sections/<int:section_id>/edit/', views.edit_section, name='edit_section'),
    path('sections/<int:section_id>/delete/', views.delete_section, name='delete_section'),
    path('sections/<int:section_id>/students/', views.section_students, name='section_students'),
    path('sections/<int:section_id>/assign-subjects/', views.assign_subjects_to_section, name='assign_subjects'),
    path('assignments/<int:assignment_id>/remove/', views.remove_subject_from_section, name='remove_subject'),
    
    # Subject Management
    path('subjects/', views.subject_list, name='subject_list'),
    path('subjects/create/', views.create_subject, name='create_subject'),
    path('subjects/<int:subject_id>/edit/', views.edit_subject, name='edit_subject'),
    path('subjects/<int:subject_id>/delete/', views.delete_subject, name='delete_subject'),
]