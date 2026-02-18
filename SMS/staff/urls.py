from django.urls import path
from . import views

app_name = 'staff'

urlpatterns = [
    # Staff List
    path('', views.staff_list, name='staff_list'),

    # Create Staff Wizard
    path('create/', views.create_staff_wizard, name='create_staff_wizard'),

    # My Profile (Principal / Manager)
    path('profile/', views.my_profile, name='my_profile'),
    path('profile/edit/', views.edit_my_profile, name='edit_my_profile'),

    # Change Credentials (email/password) for any user
    path('credentials/<int:user_id>/', views.change_credentials, name='change_credentials'),

    # Staff Details (with type)
    path('<str:staff_type>/<int:staff_id>/', views.staff_detail, name='staff_detail'),
    path('<str:staff_type>/<int:staff_id>/edit/', views.edit_staff, name='edit_staff'),
    path('<str:staff_type>/<int:staff_id>/deactivate/', views.deactivate_staff, name='deactivate_staff'),
    path('<str:staff_type>/<int:staff_id>/activate/', views.activate_staff, name='activate_staff'),
]
