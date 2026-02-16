from django.contrib import admin
from django.utils.html import format_html
from .models import SchoolTenant, Branch


# ----------------------------
# Branch Inline (Inside School)
# ----------------------------
class BranchInline(admin.TabularInline):
    model = Branch
    extra = 0
    fields = (
        'name',
        'code',
        'city',
        'phone',
        'is_main_branch',
        'is_active',
    )
    readonly_fields = ('code',)
    show_change_link = True


# ----------------------------
# SchoolTenant Admin
# ----------------------------
@admin.register(SchoolTenant)
class SchoolTenantAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'city',
        'owner',
        'get_branch_count',
        'max_branches',
        'is_active',
        'created_at',
    )

    list_filter = (
        'city',
        'is_active',
        'created_at',
    )

    search_fields = (
        'name',
        'city',
        'email',
        'owner__username',
    )

    readonly_fields = (
        'slug',
        'created_at',
        'updated_at',
    )

    prepopulated_fields = {}  # slug is auto-generated in model

    inlines = [BranchInline]

    fieldsets = (
        ("Basic Information", {
            "fields": ("name", "slug", "owner")
        }),
        ("Location", {
            "fields": ("city", "address")
        }),
        ("Contact Info", {
            "fields": ("phone", "email")
        }),
        ("School Details", {
            "fields": ("established_year", "registration_number")
        }),
        ("Subscription", {
            "fields": ("max_branches", "is_active")
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
        }),
    )


# ----------------------------
# Branch Admin
# ----------------------------
@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'school',
        'code',
        'city',
        'manager',
        'is_main_branch',
        'is_active',
        'created_at',
    )

    list_filter = (
        'school',
        'is_main_branch',
        'is_active',
        'city',
    )

    search_fields = (
        'name',
        'code',
        'school__name',
        'manager__username',
        'email',
    )

    readonly_fields = (
        'code',
        'manager_temp_email',
        'manager_temp_password',
        'created_at',
        'updated_at',
    )

    fieldsets = (
        ("Basic Information", {
            "fields": ("name", "school", "code")
        }),
        ("Location", {
            "fields": ("city", "address")
        }),
        ("Contact Info", {
            "fields": ("phone", "email")
        }),
        ("Management", {
            "fields": (
                "manager",
                "is_main_branch",
                "is_active",
            )
        }),
        ("Temporary Credentials", {
            "fields": (
                "manager_temp_email",
                "manager_temp_password",
            )
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at")
        }),
    )
