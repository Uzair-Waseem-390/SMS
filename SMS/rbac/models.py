from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class Role(models.Model):
    """
    Role Model — Defines user roles within a tenant.
    Each role belongs to a specific school tenant for data isolation.
    """

    # 'superadmin' added so system roles created by seed_rbac pass validation.
    # (Error #15)
    ROLE_CHOICES = [
        ('superadmin', 'Super Administrator'),
        ('principal', 'Principal'),
        ('manager', 'Manager'),
        ('accountant', 'Accountant'),
        ('teacher', 'Teacher'),
        ('employee', 'Employee'),
        ('parent', 'Parent'),
        ('student', 'Student'),
    ]

    name = models.CharField(max_length=50, choices=ROLE_CHOICES)
    display_name = models.CharField(max_length=100, help_text="Human-readable role name")
    description = models.TextField(blank=True)

    # Hierarchy: lower number = higher authority
    level_rank = models.PositiveSmallIntegerField(
        help_text="Lower number = higher authority (0–100)"
    )

    # Tenant isolation — NULL for system-wide roles (e.g. superadmin)
    tenant = models.ForeignKey(
        'tenants.SchoolTenant',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='roles',
    )

    # Metadata
    is_system_role = models.BooleanField(
        default=False, help_text="System roles cannot be deleted"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['level_rank', 'name']
        unique_together = ['name', 'tenant']   # one role per name per tenant
        indexes = [
            models.Index(fields=['tenant', 'level_rank']),
            models.Index(fields=['name']),
        ]

    def __str__(self):
        return f"{self.get_name_display()} (Level {self.level_rank})"

    def clean(self):
        """Validate role hierarchy — allow rank 0 for superadmin."""
        if self.level_rank < 0 or self.level_rank > 100:
            raise ValidationError({'level_rank': 'Level rank must be between 0 and 100.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def has_higher_authority_than(self, other_role):
        """Return True if this role outranks another (lower level_rank)."""
        return self.level_rank < other_role.level_rank

    def can_manage_role(self, target_role):
        """
        Return True if this role can create/edit/delete *target_role*.
        A role can only manage roles with strictly lower authority.
        """
        return self.level_rank < target_role.level_rank


class Permission(models.Model):
    """
    Permission Model — Defines granular permissions for actions.
    Permissions are global and shared across all tenants.
    """

    CATEGORY_CHOICES = [
        ('student', 'Student Management'),
        ('academic', 'Academic Management'),
        ('attendance', 'Attendance Management'),
        ('finance', 'Finance Management'),
        ('exam', 'Exam & Result Management'),
        ('staff', 'Staff Management'),
        ('notification', 'Notification Management'),
        ('report', 'Report Generation'),
        ('system', 'System Administration'),
        ('branch', 'Branch Management'),
    ]

    # Unique permission code (e.g. 'student.create', 'fee.collect')
    code = models.CharField(max_length=100, unique=True, db_index=True)

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='system')

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['category', 'code']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['category']),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"

    @classmethod
    def get_by_category(cls, category):
        """Return all active permissions in *category*."""
        return cls.objects.filter(category=category, is_active=True)


class RolePermission(models.Model):
    """
    RolePermission Model — Many-to-many bridge between Role and Permission.
    Defines which permissions are granted to which roles.
    """

    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='role_permissions')
    permission = models.ForeignKey(
        Permission, on_delete=models.CASCADE, related_name='role_permissions'
    )

    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='assigned_permissions',
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['role', 'permission']
        indexes = [
            models.Index(fields=['role', 'permission']),
        ]

    def __str__(self):
        return f"{self.role} → {self.permission.code}"


class UserRole(models.Model):
    """
    UserRole Model — Assigns users to roles within a specific branch/tenant.
    This is the core model driving authorization decisions.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='user_roles',
    )
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='user_roles')

    # Which branch this role applies to (NULL = tenant-wide)
    branch = models.ForeignKey(
        'tenants.Branch',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='user_roles',
    )

    # Effective date range (supports temporary/time-limited roles)
    valid_from = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField(null=True, blank=True)

    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='assigned_roles',
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ['user', 'role', 'branch']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['role', 'branch']),
            models.Index(fields=['valid_from', 'valid_until']),
        ]
        ordering = ['-assigned_at']

    def __str__(self):
        context = f" at {self.branch.name}" if self.branch else " (Tenant-wide)"
        return f"{self.user.email} → {self.role.name}{context}"

    def is_valid(self):
        """Return True if this assignment is currently active and within its date range."""
        now = timezone.now()
        return (
            self.is_active
            and now >= self.valid_from
            and (self.valid_until is None or now <= self.valid_until)
        )

    def deactivate(self):
        """Soft-deactivate this role assignment."""
        self.is_active = False
        self.save(update_fields=['is_active', 'updated_at'])


class PermissionAuditLog(models.Model):
    """
    PermissionAuditLog Model — Records all permission checks and role changes.
    Used for debugging and security audits.
    """

    ACTION_CHOICES = [
        ('check', 'Permission Check'),
        ('grant', 'Permission Granted'),
        ('revoke', 'Permission Revoked'),
        ('deny', 'Permission Denied'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    permission_code = models.CharField(max_length=100)

    resource_type = models.CharField(max_length=100, blank=True)
    resource_id = models.PositiveIntegerField(null=True, blank=True)

    granted = models.BooleanField()
    reason = models.TextField(blank=True)

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    path = models.CharField(max_length=500, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['permission_code', 'granted']),
            models.Index(fields=['timestamp']),
        ]
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.timestamp}: {self.user} - {self.permission_code} - {self.granted}"