from django.http import Http404
from django.core.exceptions import PermissionDenied


class SchoolBranchMiddleware:
    """
    Middleware that extracts school_id and branch_id from URL kwargs,
    validates them, and attaches the objects to the request.
    Pops the kwargs so views don't need to accept them.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.current_school = None
        request.current_branch = None
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        school_id = view_kwargs.pop('school_id', None)
        branch_id = view_kwargs.pop('branch_id', None)

        if school_id is None or branch_id is None:
            return None

        from tenants.models import SchoolTenant, Branch

        try:
            school = SchoolTenant.objects.get(id=school_id, is_active=True)
        except SchoolTenant.DoesNotExist:
            raise Http404("School not found.")

        try:
            branch = Branch.objects.get(id=branch_id, school=school, is_active=True)
        except Branch.DoesNotExist:
            raise Http404("Branch not found.")

        if request.user.is_authenticated:
            if not _user_has_access(request.user, school, branch):
                raise PermissionDenied("You don't have access to this school/branch.")

        request.current_school = school
        request.current_branch = branch
        return None


def _user_has_access(user, school, branch):
    """Validate that the user has access to the given school and branch."""
    if user.is_superuser:
        return True

    utype = getattr(user, 'user_type', '')

    if utype == 'principal':
        try:
            return user.owned_school.id == school.id
        except Exception:
            return False

    if utype == 'manager':
        try:
            return user.managed_branch.id == branch.id
        except Exception:
            return False

    if utype in ('teacher', 'accountant'):
        try:
            from rbac.models import UserRole
            return UserRole.objects.filter(
                user=user, branch=branch, is_active=True
            ).exists()
        except Exception:
            return False

    return False
