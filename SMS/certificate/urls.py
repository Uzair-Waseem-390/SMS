from django.urls import path
from . import views

app_name = 'certificate'

urlpatterns = [
    path('', views.template_list, name='template_list'),
    path('templates/seed-defaults/', views.seed_default_templates, name='seed_default_templates'),
    path('templates/create/', views.template_create, name='template_create'),
    path('templates/<int:pk>/edit/', views.template_edit, name='template_edit'),
    path('templates/<int:pk>/delete/', views.template_delete, name='template_delete'),
    path('issued/', views.certificate_list, name='certificate_list'),
    path('generate/', views.generate_certificate, name='generate_certificate'),
    path('issued/<int:pk>/', views.certificate_detail, name='certificate_detail'),
    # path('issued/<int:pk>/download/', views.certificate_download, name='certificate_download'),
    path('issued/<int:pk>/print/', views.certificate_print, name='certificate_print'),
]
