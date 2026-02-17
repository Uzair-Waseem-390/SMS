from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse

from .models import Role, Permission, RolePermission, UserRole, PermissionAuditLog


# ─────────────────────────────────────────────────────────────────────────────
# Permission must be registered FIRST because RolePermissionInline uses
# autocomplete_fields = ['permission'], which requires PermissionAdmin to
# already be registered with search_fields. (Error #6)
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'category', 'is_active']
    list_filter = ['category', 'is_active']
    search_fields = ['code', 'name', 'description']   # required for autocomplete
    list_editable = ['is_active']
    ordering = ['category', 'code']

    fieldsets = (
        ('Permission Details', {
            'fields': ('code', 'name', 'description')
        }),
        ('Category & Status', {
            'fields': ('category', 'is_active')
        }),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Inline — safe to define after PermissionAdmin is registered
# ─────────────────────────────────────────────────────────────────────────────

class RolePermissionInline(admin.TabularInline):
    model = RolePermission
    extra = 1
    autocomplete_fields = ['permission']   # PermissionAdmin registered above ✓


# ─────────────────────────────────────────────────────────────────────────────
# Role
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'display_name', 'level_rank', 'tenant',
        'is_system_role', 'is_active', 'permission_count',
    ]
    list_filter = ['is_system_role', 'is_active', 'tenant']
    search_fields = ['name', 'display_name', 'description']
    # 'name' is the first column and acts as the clickable link, so it must NOT
    # appear in list_editable.  'level_rank' and 'is_active' are safe to edit
    # inline.  (Error #2)
    list_editable = ['level_rank', 'is_active']
    inlines = [RolePermissionInline]

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'display_name', 'description')
        }),
        ('Hierarchy', {
            'fields': ('level_rank',)
        }),
        ('Tenant & Status', {
            'fields': ('tenant', 'is_system_role', 'is_active')
        }),
    )

    def permission_count(self, obj):
        count = obj.role_permissions.count()
        url = (
            reverse('admin:rbac_rolepermission_changelist')
            + f'?role__id__exact={obj.id}'
        )
        return format_html('<a href="{}">{} Permissions</a>', url, count)

    permission_count.short_description = 'Permissions'


# ─────────────────────────────────────────────────────────────────────────────
# RolePermission
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    list_display = ['role', 'permission', 'assigned_at']
    list_filter = ['role__tenant', 'role', 'permission__category']
    search_fields = ['role__name', 'permission__code', 'permission__name']
    # 'role' needs RoleAdmin with search_fields (defined above ✓)
    # 'assigned_by' needs UserAdmin with search_fields — handled in accounts app
    autocomplete_fields = ['role', 'permission', 'assigned_by']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('role', 'permission')


# ─────────────────────────────────────────────────────────────────────────────
# UserRole
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'branch', 'validity_status', 'assigned_at']
    list_filter = ['role', 'is_active', 'branch']
    search_fields = ['user__email', 'user__full_name', 'role__name']
    # 'branch' needs BranchAdmin registered with search_fields in tenants app
    # 'user'   needs UserAdmin  registered with search_fields in accounts app
    autocomplete_fields = ['user', 'role', 'branch', 'assigned_by']
    date_hierarchy = 'assigned_at'

    # 'assigned_at' is auto_now_add → non-editable → must be in readonly_fields
    # (Error #4)
    readonly_fields = ['assigned_at']

    fieldsets = (
        ('Assignment', {
            'fields': ('user', 'role', 'branch')
        }),
        ('Validity Period', {
            'fields': ('valid_from', 'valid_until', 'is_active')
        }),
        ('Audit', {
            'fields': ('assigned_by', 'assigned_at'),
            'classes': ('collapse',)
        }),
    )

    # Renamed from 'is_valid' to 'validity_status' to avoid shadowing the
    # model's own is_valid() method inside the admin class. (Error #5)
    def validity_status(self, obj):
        return obj.is_valid()

    validity_status.boolean = True
    validity_status.short_description = 'Currently Valid'


# ─────────────────────────────────────────────────────────────────────────────
# PermissionAuditLog  (read-only)
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(PermissionAuditLog)
class PermissionAuditLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'user', 'permission_code', 'action', 'granted']
    list_filter = ['action', 'granted', 'timestamp']
    search_fields = ['user__email', 'permission_code']
    readonly_fields = ['timestamp', 'user', 'permission_code', 'action', 'granted', 'reason']
    date_hierarchy = 'timestamp'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False