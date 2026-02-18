from django.contrib import admin
from .models import StudentAttendance, StaffAttendance


@admin.register(StudentAttendance)
class StudentAttendanceAdmin(admin.ModelAdmin):
    list_display = ('student', 'date', 'status', 'section', 'branch', 'marked_by')
    list_filter = ('status', 'date', 'branch', 'section')
    search_fields = ('student__first_name', 'student__last_name', 'student__admission_number')
    date_hierarchy = 'date'
    readonly_fields = ('created_at', 'updated_at')


@admin.register(StaffAttendance)
class StaffAttendanceAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'status', 'late_time', 'half_leave_time', 'branch', 'marked_by')
    list_filter = ('status', 'date', 'branch')
    search_fields = ('user__full_name', 'user__email')
    date_hierarchy = 'date'
    readonly_fields = ('created_at', 'updated_at')
