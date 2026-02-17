"""
Service Layer for RBAC Operations.
Contains business logic for permission checking and role management.
"""

from typing import Optional, List, Union
from django.db import transaction
from django.db.models import Q          # ← fixes Error #11 / #12: models.Q() was used
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.utils import timezone

from .models import Role, Permission, RolePermission, UserRole, PermissionAuditLog
from .permissions import Permissions

User = get_user_model()


class RBACService:
    """
    Centralized service for all RBAC operations.
    All permission checks should go through this service.
    """

    def __init__(self, user=None, tenant=None):
        self.user = user
        self.tenant = tenant

    # ═════════════════════════════════════════════════════════════
    # PERMISSION CHECKING
    # ═════════════════════════════════════════════════════════════

    def user_has_permission(self, user: User, permission_code: str, branch=None) -> bool:
        """
        Check if a user has a specific permission.

        Args:
            user:            The user to check.
            permission_code: The permission code (e.g. 'student.create').
            branch:          Optional branch context.

        Returns:
            bool: True if the user holds the permission.
        """
        if not user or not user.is_authenticated:
            self._log_permission_check(user, permission_code, False, "User not authenticated")
            return False

        # Superusers bypass all permission checks
        if user.is_superuser:
            self._log_permission_check(user, permission_code, True, "Superuser access")
            return True

        user_roles = self._get_valid_user_roles(user, branch)

        if not user_roles.exists():
            self._log_permission_check(user, permission_code, False, "No valid roles found")
            return False

        has_permission = RolePermission.objects.filter(
            role__in=user_roles.values('role'),
            permission__code=permission_code,
            permission__is_active=True,
        ).exists()

        self._log_permission_check(user, permission_code, has_permission)
        return has_permission

    def user_has_any_permission(
        self, user: User, permission_codes: List[str], branch=None
    ) -> bool:
        """Return True if the user holds at least one of the given permissions."""
        for code in permission_codes:
            if self.user_has_permission(user, code, branch):
                return True
        return False

    def user_has_all_permissions(
        self, user: User, permission_codes: List[str], branch=None
    ) -> bool:
        """Return True only if the user holds every one of the given permissions."""
        for code in permission_codes:
            if not self.user_has_permission(user, code, branch):
                return False
        return True

    def require_permission(self, user: User, permission_code: str, branch=None):
        """
        Require a specific permission; raise PermissionDenied if not granted.

        Raises:
            PermissionDenied: If the user does not hold the permission.
        """
        if not self.user_has_permission(user, permission_code, branch):
            raise PermissionDenied(
                f"User {user.email} does not have permission: {permission_code}"
            )

    def get_user_permissions(self, user: User, branch=None) -> List[str]:
        """
        Return all permission codes currently held by a user.

        Args:
            user:   The user to inspect.
            branch: Optional branch context.

        Returns:
            List[str]: Sorted list of permission code strings.
        """
        if user.is_superuser:
            return [p.value for p in Permissions]

        user_roles = self._get_valid_user_roles(user, branch)

        if not user_roles.exists():
            return []

        permissions = RolePermission.objects.filter(
            role__in=user_roles.values('role'),
            permission__is_active=True,
        ).select_related('permission')

        return [rp.permission.code for rp in permissions]

    # ═════════════════════════════════════════════════════════════
    # ROLE MANAGEMENT
    # ═════════════════════════════════════════════════════════════

    @transaction.atomic
    def assign_role(
        self,
        user: User,
        role: Role,
        branch=None,
        assigned_by=None,
        valid_until=None,
    ) -> UserRole:
        """
        Assign a role to a user.

        Args:
            user:        User to assign the role to.
            role:        Role instance to assign.
            branch:      Optional branch context (None = tenant-wide).
            assigned_by: User performing the assignment (None = system).
            valid_until: Optional datetime at which the assignment expires.

        Returns:
            UserRole: The newly created assignment record.

        Raises:
            PermissionDenied: If assigned_by lacks authority over the role.
        """
        if assigned_by and not self._can_manage_role(assigned_by, role):
            raise PermissionDenied(
                f"User {assigned_by.email} cannot assign role {role.name}"
            )

        # Deactivate any existing active assignment for the same user/role/branch
        UserRole.objects.filter(
            user=user, role=role, branch=branch, is_active=True
        ).update(is_active=False)

        user_role = UserRole.objects.create(
            user=user,
            role=role,
            branch=branch,
            assigned_by=assigned_by,
            valid_until=valid_until,
            is_active=True,
        )

        self._log_action('grant', user, role, assigned_by, branch)
        return user_role

    def revoke_role(self, user_role: UserRole, revoked_by=None):
        """
        Revoke an active role assignment.

        Args:
            user_role:  UserRole instance to deactivate.
            revoked_by: User performing the revocation (None = system).

        Raises:
            PermissionDenied: If revoked_by lacks authority over the role.
        """
        if revoked_by and not self._can_manage_role(revoked_by, user_role.role):
            raise PermissionDenied(
                f"User {revoked_by.email} cannot revoke role {user_role.role.name}"
            )

        user_role.deactivate()
        self._log_action('revoke', user_role.user, user_role.role, revoked_by, user_role.branch)

    def get_user_roles(self, user: User, branch=None, only_valid=True):
        """
        Return all role assignments for a user.

        Args:
            user:       The user to query.
            branch:     Optional branch filter.
            only_valid: When True, exclude expired/inactive assignments.

        Returns:
            QuerySet[UserRole]
        """
        queryset = UserRole.objects.filter(user=user)

        if branch:
            queryset = queryset.filter(Q(branch=branch) | Q(branch__isnull=True))

        if only_valid:
            now = timezone.now()
            queryset = queryset.filter(
                is_active=True,
                valid_from__lte=now,
            ).filter(Q(valid_until__isnull=True) | Q(valid_until__gte=now))

        return queryset.select_related('role', 'branch')

    # ═════════════════════════════════════════════════════════════
    # HIERARCHY CHECKS
    # ═════════════════════════════════════════════════════════════

    def _can_manage_role(self, manager: User, target_role: Role) -> bool:
        """
        Return True if *manager* has sufficient authority to assign/revoke
        *target_role*.  A manager can only act on roles ranked lower than
        their own highest-authority role.
        """
        if manager.is_superuser:
            return True

        manager_roles = self._get_valid_user_roles(manager)
        if not manager_roles.exists():
            return False

        # Lowest level_rank == highest authority
        highest_role = manager_roles.order_by('role__level_rank').first().role
        return highest_role.level_rank < target_role.level_rank

    def _get_valid_user_roles(self, user: User, branch=None):
        """
        Return the queryset of currently valid UserRole records for *user*.

        Optionally filtered to a specific branch (includes tenant-wide roles
        i.e. branch IS NULL).
        """
        now = timezone.now()
        queryset = UserRole.objects.filter(
            user=user,
            is_active=True,
            valid_from__lte=now,
        ).filter(Q(valid_until__isnull=True) | Q(valid_until__gte=now))

        if branch:
            queryset = queryset.filter(Q(branch=branch) | Q(branch__isnull=True))

        return queryset

    # ═════════════════════════════════════════════════════════════
    # AUDIT HELPERS
    # ═════════════════════════════════════════════════════════════

    def _log_permission_check(self, user, permission_code, granted, reason=""):
        """Record a permission check in the audit log (fail-silent)."""
        try:
            PermissionAuditLog.objects.create(
                user=user,
                action='check',
                permission_code=permission_code,
                granted=granted,
                reason=reason,
            )
        except Exception:
            pass  # Logging must never break the application

    def _log_action(self, action, user, role, performed_by, branch):
        """Record a role grant/revoke in the audit log (fail-silent)."""
        try:
            PermissionAuditLog.objects.create(
                user=user,
                action=action,
                permission_code=f"role.{action}",
                granted=True,
                reason=(
                    f"Role {role.name} {action}ed by "
                    f"{performed_by.email if performed_by else 'system'}"
                ),
            )
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# Module-level singleton — import and use directly in views / other services
# ─────────────────────────────────────────────────────────────────────────────

rbac_service = RBACService()


# ─────────────────────────────────────────────────────────────────────────────
# View decorators
# ─────────────────────────────────────────────────────────────────────────────

def require_permission(permission_code):
    """
    Decorator that enforces a single permission on a view function.

    Usage::

        @require_permission(Permissions.STUDENT_VIEW.value)
        def student_list(request):
            ...
    """
    from functools import wraps

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            RBACService().require_permission(request.user, permission_code)
            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator


def require_any_permission(permission_codes):
    """
    Decorator that requires at least one of the listed permissions.

    Usage::

        @require_any_permission([
            Permissions.STUDENT_VIEW.value,
            Permissions.STUDENT_EDIT.value,
        ])
        def student_dashboard(request):
            ...
    """
    from functools import wraps

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            service = RBACService()
            if not service.user_has_any_permission(request.user, permission_codes):
                raise PermissionDenied("User lacks any required permission")
            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator