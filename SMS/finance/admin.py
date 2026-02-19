from django.contrib import admin
from .models import BranchFeeStructure, Scholarship, StudentFee


@admin.register(BranchFeeStructure)
class BranchFeeStructureAdmin(admin.ModelAdmin):
    list_display = ['branch', 'frequency', 'monthly_amount', 'yearly_amount', 'yearly_installments', 'installment_amount', 'is_active']
    list_filter = ['frequency', 'is_active', 'branch']
    readonly_fields = ['installment_amount', 'created_at', 'updated_at']


@admin.register(Scholarship)
class ScholarshipAdmin(admin.ModelAdmin):
    list_display = ['name', 'scholarship_type', 'percentage_amount', 'fixed_amount', 'branch', 'is_active', 'start_date']
    list_filter = ['scholarship_type', 'is_active', 'branch']
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(StudentFee)
class StudentFeeAdmin(admin.ModelAdmin):
    list_display = ['student', 'label', 'amount', 'scholarship_deduction', 'net_amount', 'amount_paid', 'status', 'due_date']
    list_filter = ['status', 'branch', 'due_date']
    search_fields = ['student__first_name', 'student__last_name', 'student__admission_number']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'due_date'
