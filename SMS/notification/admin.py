from django.contrib import admin
from .models import Notification, Timetable


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'notification_type', 'visibility', 'branch', 'date', 'duration_days', 'is_active']
    list_filter = ['notification_type', 'visibility', 'is_active', 'branch']
    search_fields = ['title', 'message']
    date_hierarchy = 'date'
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Timetable)
class TimetableAdmin(admin.ModelAdmin):
    list_display = ['title', 'branch', 'is_active', 'created_by', 'created_at']
    list_filter = ['is_active', 'branch']
    search_fields = ['title']
    readonly_fields = ['created_at', 'updated_at']
