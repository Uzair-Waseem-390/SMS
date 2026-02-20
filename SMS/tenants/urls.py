from django.urls import path
from . import views

app_name = 'tenants'

urlpatterns = [
    # Setup wizard
    path('setup/', views.setup_wizard, name='setup_wizard'),

    # Legacy branch management
    path('branch/<int:branch_id>/manage/', views.manage_branch, name='manage_branch'),

    # ── School CRUD (Principal only) ─────────────────────────────────────────
    path('school/', views.school_detail, name='school_detail'),
    path('school/edit/', views.school_update, name='school_update'),

    # ── Branch CRUD (Principal only) ─────────────────────────────────────────
    path('school/branches/', views.branch_list, name='branch_list'),
    path('school/branches/create/', views.branch_create, name='branch_create'),
    path('school/branches/<int:branch_id>/edit/', views.branch_update, name='branch_update'),
    path('school/branches/<int:branch_id>/delete/', views.branch_delete, name='branch_delete'),

    # ── Branch Switching (session-based) ─────────────────────────────────
    path('switch-branch/', views.switch_branch, name='switch_branch'),
]