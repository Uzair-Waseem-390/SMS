from django.urls import path
from . import views

app_name = 'tenants'

urlpatterns = [
    # Setup wizard
    path('setup/', views.setup_wizard, name='setup_wizard'),
    
    # Test page after setup
    path('test/', views.test_page, name='test_page'),
    
    # Branch management
    path('branch/<int:branch_id>/manage/', views.manage_branch, name='manage_branch'),
]