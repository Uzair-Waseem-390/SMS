"""
Selector Layer for RBAC - Handles data retrieval with optimized queries.
Separates read operations from business logic.
"""

from django.db.models import Q, Count   # import Q and Count directly — no need for 'models'
from django.utils import timezone
from typing import Optional, List, Dict

from .models import Role, Permission, UserRole, RolePermission


class RoleSelector:
    """Selector for role-related queries."""

    @staticmethod
    def get_tenant_roles(tenant, include_system=True):
        """
        Get all roles for a tenant.

        Args:
            tenant:         SchoolTenant instance
            include_system: Include system-wide roles (tenant IS NULL)

        Returns:
            QuerySet: Role queryset ordered by level_rank
        """
        queryset = Role.objects.filter(is_active=True)

        if tenant:
            if include_system:
                queryset = queryset.filter(Q(tenant=tenant) | Q(tenant__isnull=True))
            else:
                queryset = queryset.filter(tenant=tenant)

        return queryset.order_by('level_rank', 'name')

    @staticmethod
    def get_role_by_name(tenant, role_name):
        """
        Get a role by name for a specific tenant.

        Args:
            tenant:    SchoolTenant instance
            role_name: Name of the role

        Returns:
            Role or None
        """
        try:
            return Role.objects.get(
                Q(tenant=tenant) | Q(tenant__isnull=True),
                name=role_name,
                is_active=True,
            )
        except Role.DoesNotExist:
            return None

    @staticmethod
    def get_role_permissions(role):
        """
        Get all permissions assigned to a role.

        Args:
            role: Role instance

        Returns:
            QuerySet: Permission queryset
        """
        return Permission.objects.filter(
            role_permissions__role=role,
            is_active=True,
        ).order_by('category', 'code')


class PermissionSelector:
    """Selector for permission-related queries."""

    @staticmethod
    def get_all_permissions():
        """Get all active permissions."""
        return Permission.objects.filter(is_active=True).order_by('category', 'code')

    @staticmethod
    def get_permissions_by_category(category):
        """Get permissions filtered by category."""
        return Permission.objects.filter(category=category, is_active=True)

    @staticmethod
    def get_permission_matrix():
        """
        Get permissions organised by category.

        Returns:
            Dict: {category: [{'code': ..., 'name': ..., 'description': ...}]}
        """
        permissions = Permission.objects.filter(is_active=True).order_by('category', 'code')
        matrix = {}
        for perm in permissions:
            if perm.category not in matrix:
                matrix[perm.category] = []
            matrix[perm.category].append({
                'code': perm.code,
                'name': perm.name,
                'description': perm.description,
            })
        return matrix


class UserRoleSelector:
    """Selector for user role assignments."""

    @staticmethod
    def get_user_roles(user, branch=None, only_valid=True):
        """
        Get all roles assigned to a user.

        Args:
            user:       User instance
            branch:     Optional branch filter
            only_valid: Only return currently valid roles

        Returns:
            QuerySet: UserRole queryset
        """
        queryset = UserRole.objects.filter(user=user)

        if branch:
            queryset = queryset.filter(Q(branch=branch) | Q(branch__isnull=True))

        if only_valid:
            now = timezone.now()
            # FIX (line 135): Q() objects cannot be mixed with keyword args
            # inside the same .filter() call as positional arguments.
            # Chain a second .filter() instead.
            queryset = (
                queryset
                .filter(is_active=True, valid_from__lte=now)
                .filter(Q(valid_until__isnull=True) | Q(valid_until__gte=now))
            )

        return queryset.select_related('role', 'branch')

    @staticmethod
    def get_users_by_role(role, branch=None, only_valid=True):
        """
        Get all users that hold a specific role.

        Args:
            role:       Role instance
            branch:     Optional branch filter
            only_valid: Only return currently valid assignments

        Returns:
            QuerySet: UserRole queryset with user data prefetched
        """
        queryset = UserRole.objects.filter(role=role)

        if branch:
            queryset = queryset.filter(branch=branch)

        if only_valid:
            now = timezone.now()
            # FIX (line 163): same issue — split into two chained .filter() calls
            queryset = (
                queryset
                .filter(is_active=True, valid_from__lte=now)
                .filter(Q(valid_until__isnull=True) | Q(valid_until__gte=now))
            )

        return queryset.select_related('user')

    @staticmethod
    def get_role_summary_for_branch(branch):
        """
        Return a count of active role assignments for a branch.

        Args:
            branch: Branch instance

        Returns:
            Dict: {role_name: user_count}
        """
        now = timezone.now()

        # FIX (line 184): Q() objects mixed with keyword args in one .filter()
        # call — split into two chained .filter() calls.
        assignments = (
            UserRole.objects
            .filter(Q(branch=branch) | Q(branch__isnull=True))
            .filter(is_active=True, valid_from__lte=now)
            .filter(Q(valid_until__isnull=True) | Q(valid_until__gte=now))
            .values('role__name')
            .annotate(count=Count('user'))
        )

        return {item['role__name']: item['count'] for item in assignments}