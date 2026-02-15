from django.contrib import admin
from django.utils import timezone
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import CustomUser

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """
    Custom admin interface for CustomUser model.
    Provides easy management of users and payment verification.
    """
    
    # Display fields in the admin list view
    list_display = (
        'email', 
        'full_name', 
        'phone_number', 
        'user_type', 
        'payment_verified', 
        'is_active',
        'created_at',
        'payment_status_badge'
    )
    
    # Add filters in the sidebar
    list_filter = (
        'user_type', 
        'payment_verified', 
        'is_active', 
        'is_staff',
        'created_at'
    )
    
    # Make fields searchable
    search_fields = ('email', 'full_name', 'phone_number', 'transaction_id')
    
    # Default ordering
    ordering = ('-created_at',)
    
    # Make list editable
    list_editable = ('payment_verified', 'is_active')
    
    # Add date hierarchy for better navigation
    date_hierarchy = 'created_at'
    
    # Add action buttons
    actions = ['verify_payments', 'activate_users', 'send_whatsapp_reminder']
    
    # Fieldsets for the detailed view
    fieldsets = (
        ('Basic Information', {
            'fields': ('email', 'full_name', 'phone_number', 'city')
        }),
        ('User Type & Status', {
            'fields': ('user_type', 'is_active', 'is_staff', 'is_superuser')
        }),
        ('Payment Verification', {
            'fields': ('payment_verified', 'transaction_id', 'payment_screenshot', 'payment_submitted_at'),
            'classes': ('wide',),
            'description': 'Payment verification details - manually verify after checking WhatsApp'
        }),
        ('Terms Acceptance', {
            'fields': ('accepted_terms', 'accepted_policies', 'terms_accepted_at'),
            'classes': ('collapse',)
        }),
        ('Important Dates', {
            'fields': ('last_login', 'date_joined', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    # Fields for adding new user in admin
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'full_name', 'phone_number', 'password1', 'password2', 
                      'user_type', 'payment_verified', 'is_active'),
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at', 'last_login', 'date_joined', 
                      'payment_submitted_at', 'terms_accepted_at')
    
    def payment_status_badge(self, obj):
        """
        Display payment status as colored badges.
        """
        if obj.payment_verified:
            return format_html(
                '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 20px;">{} Verified</span>',
                '#28a745', '✓'
            )
        elif obj.payment_screenshot:
            return format_html(
                '<span style="background-color: {}; color: black; padding: 3px 10px; border-radius: 20px;">{} Pending</span>',
                '#ffc107', '⏳'
            )
        else:
            return format_html(
                '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 20px;">{} Not Paid</span>',
                '#dc3545', '✗'
            )
    
    payment_status_badge.short_description = 'Payment Status'
    payment_status_badge.admin_order_field = 'payment_verified'
    
    def verify_payments(self, request, queryset):
        """
        Admin action to verify payments for selected users.
        """
        updated = queryset.update(payment_verified=True, is_active=True)
        self.message_user(request, f'{updated} user(s) have been verified and activated.')
    verify_payments.short_description = "Verify payment and activate selected users"
    
    def activate_users(self, request, queryset):
        """
        Admin action to activate users.
        """
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} user(s) have been activated.')
    activate_users.short_description = "Activate selected users"
    
    def send_whatsapp_reminder(self, request, queryset):
        """
        Admin action placeholder for WhatsApp reminders.
        In production, integrate with WhatsApp API.
        """
        self.message_user(request, 'WhatsApp reminder feature - integrate with WhatsApp API')
    send_whatsapp_reminder.short_description = "Send WhatsApp reminder"
    
    # Override save_model to handle terms acceptance in admin
    def save_model(self, request, obj, form, change):
        if not change:  # New user
            obj.accepted_terms = True
            obj.accepted_policies = True
            obj.terms_accepted_at = timezone.now()
        super().save_model(request, obj, form, change)
