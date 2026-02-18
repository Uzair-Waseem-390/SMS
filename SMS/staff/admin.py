from django.contrib import admin
from .models import Employee, Teacher, Accountant


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'employee_id', 'employee_type', 'branch', 'is_active', 'joining_date')
    list_filter = ('employee_type', 'branch', 'is_active')
    search_fields = ('first_name', 'last_name', 'employee_id', 'phone_number')
    readonly_fields = ('employee_id', 'employee_code', 'created_at', 'updated_at')


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'employee_code', 'branch', 'specialization', 'is_active', 'incharge_section')
    list_filter = ('branch', 'is_active')
    search_fields = ('user__full_name', 'user__email', 'employee_code')
    readonly_fields = ('employee_code', 'created_at', 'updated_at')
    filter_horizontal = ('subjects',)


@admin.register(Accountant)
class AccountantAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'employee_code', 'branch', 'qualification', 'is_active')
    list_filter = ('branch', 'is_active')
    search_fields = ('user__full_name', 'user__email', 'employee_code')
    readonly_fields = ('employee_code', 'created_at', 'updated_at')
