from django.contrib import admin
from .models import CertificateTemplate, Certificate


@admin.register(CertificateTemplate)
class CertificateTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'template_type', 'branch', 'is_active']
    list_filter = ['template_type', 'is_active']
    search_fields = ['name']


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ['serial_number', 'template', 'recipient_name', 'issued_date', 'issued_by', 'branch']
    list_filter = ['issued_date', 'template__template_type']
    search_fields = ['serial_number']
    readonly_fields = ['serial_number', 'custom_data', 'created_at']

    def recipient_name(self, obj):
        return obj.recipient_name
    recipient_name.short_description = 'Recipient'
