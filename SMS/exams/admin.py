from django.contrib import admin
from .models import Exam, ExamAttendance, ExamResult


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ['name', 'exam_type', 'subject', 'class_obj', 'section', 'date', 'total_marks', 'is_published', 'is_active']
    list_filter = ['exam_type', 'is_published', 'is_active', 'branch', 'date']
    search_fields = ['name', 'subject__name', 'class_obj__name']
    date_hierarchy = 'date'
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ExamAttendance)
class ExamAttendanceAdmin(admin.ModelAdmin):
    list_display = ['exam', 'student', 'status', 'marked_by', 'created_at']
    list_filter = ['status', 'exam__date']
    search_fields = ['student__first_name', 'student__last_name', 'exam__name']


@admin.register(ExamResult)
class ExamResultAdmin(admin.ModelAdmin):
    list_display = ['exam', 'student', 'obtained_marks', 'grade', 'is_absent', 'entered_by']
    list_filter = ['grade', 'is_absent', 'exam__date']
    search_fields = ['student__first_name', 'student__last_name', 'exam__name']
