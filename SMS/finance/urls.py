from django.urls import path
from . import views

app_name = 'finance'

urlpatterns = [
    path('', views.finance_dashboard, name='dashboard'),

    # Fee Structure
    path('fee-structure/', views.fee_structure_detail, name='fee_structure_detail'),
    path('fee-structure/create/', views.edit_fee_structure, name='create_fee_structure'),
    path('fee-structure/<int:fs_id>/edit/', views.edit_fee_structure, name='edit_fee_structure'),

    # Scholarships
    path('scholarships/', views.scholarship_list, name='scholarship_list'),
    path('scholarships/create/', views.create_scholarship, name='create_scholarship'),
    path('scholarships/<int:pk>/edit/', views.edit_scholarship, name='edit_scholarship'),
    path('scholarships/<int:pk>/delete/', views.delete_scholarship, name='delete_scholarship'),

    # AJAX
    path('api/sections-for-class/', views.api_sections_for_class, name='api_sections_for_class'),

    # Fee Generation & List
    path('fees/', views.fee_list, name='fee_list'),
    path('fees/generate/', views.generate_fees, name='generate_fees'),
    path('fees/<int:fee_id>/', views.fee_detail, name='fee_detail'),
    path('fees/<int:fee_id>/pay/', views.record_payment, name='record_payment'),
    path('fees/<int:fee_id>/receipt/', views.fee_receipt, name='fee_receipt'),

    # Special fee edit/delete
    path('fees/<int:fee_id>/edit-special/', views.edit_special_fee, name='edit_special_fee'),
    path('fees/<int:fee_id>/delete-special/', views.delete_special_fee, name='delete_special_fee'),

    # Expenses
    path('expenses/', views.expense_list, name='expense_list'),
    path('expenses/add/', views.create_expense, name='create_expense'),
    path('expenses/<int:pk>/edit/', views.edit_expense, name='edit_expense'),
    path('expenses/<int:pk>/delete/', views.delete_expense, name='delete_expense'),

    # Salary
    path('salary/', views.salary_list, name='salary_list'),
    path('salary/generate/', views.generate_salary, name='generate_salary'),
    path('salary/<int:pk>/edit/', views.edit_salary, name='edit_salary'),
    path('salary/<int:pk>/delete/', views.delete_salary, name='delete_salary'),
    path('salary/pay/', views.pay_salary, name='pay_salary'),

    # Financial Reports
    path('reports/', views.financial_report, name='financial_report'),
]
