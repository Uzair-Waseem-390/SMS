# accounts/utils.py
from django.contrib.auth import get_user_model
from django.urls import reverse
from tenants.models import SchoolTenant, Branch

User = get_user_model()


def get_school_and_branch(request):
    """
    Get school and branch from URL context (middleware) first,
    falling back to user relationships.
    """
    school = getattr(request, 'current_school', None)
    branch = getattr(request, 'current_branch', None)
    if school and branch:
        return school, branch
    return get_user_school(request.user, request), get_user_branch(request.user, request)


def branch_url(request, viewname, **kwargs):
    """Reverse a URL, injecting school_id and branch_id from request context."""
    school = getattr(request, 'current_school', None)
    branch = getattr(request, 'current_branch', None)
    if not school or not branch:
        school, branch = get_school_and_branch(request)
    if school and branch:
        kwargs['school_id'] = school.id
        kwargs['branch_id'] = branch.id
    return reverse(viewname, kwargs=kwargs)

def has_school_setup(user):
    """
    Check if a user has completed the school setup process.
    
    Args:
        user: User instance to check
    
    Returns:
        bool: True if user has school setup, False otherwise
    """
    if not user.is_authenticated:
        return False
    
    try:
        if user.user_type == 'principal':
            # Check if principal has an owned school
            return hasattr(user, 'owned_school')
        elif user.user_type == 'manager':
            # Check if manager is assigned to a branch
            return hasattr(user, 'managed_branch')
        else:
            # Other user types don't need setup
            return True
    except:
        return False


def get_user_school(user, request=None):
    """
    Get the school associated with a user.
    Prefers the URL-provided school (from middleware) when available.
    """
    if request:
        url_school = getattr(request, 'current_school', None)
        if url_school:
            return url_school
    try:
        if user.user_type == 'principal':
            return user.owned_school
        elif user.user_type == 'manager':
            return user.managed_branch.school
        else:
            return None
    except:
        return None


def get_user_branches(user):
    """
    Get all branches accessible to a user.
    
    Args:
        user: User instance
    
    Returns:
        QuerySet: Branches queryset
    """
    school = get_user_school(user)
    if school:
        return school.branches.all()
    return Branch.objects.none()






def get_user_branch(user, request=None):
    """
    Get the branch associated with a user.
    Prefers the URL-provided branch (from middleware) when available.
    Falls back to user relationships.
    """
    if request:
        url_branch = getattr(request, 'current_branch', None)
        if url_branch:
            return url_branch

    if not user.is_authenticated:
        return None

    try:
        if user.user_type == 'principal':
            school = get_user_school(user)
            if not school:
                return None
            branches = school.branches.filter(is_active=True)
            if not branches.exists():
                return None
            if request and branches.count() > 1:
                branch_id = request.GET.get('branch_id') or request.session.get('academics_branch_id')
                if branch_id:
                    try:
                        return branches.get(id=int(branch_id))
                    except (ValueError, Branch.DoesNotExist):
                        pass
            return branches.first()
        elif user.user_type == 'manager':
            return getattr(user, 'managed_branch', None)
        elif user.user_type == 'teacher':
            from rbac.models import UserRole
            ur = UserRole.objects.filter(
                user=user, is_active=True
            ).select_related('branch').exclude(branch__isnull=True).first()
            return ur.branch if ur else None
        else:
            return getattr(user, 'branch', None)
    except Exception:
        return None


def can_manage_academics(user):
    """
    Check if user can create/edit classes, sections, and subjects.
    Only managers and principals can perform these actions.
    
    Args:
        user: User instance
    
    Returns:
        bool: True if user is principal or manager
    """
    if not user or not user.is_authenticated:
        return False
    return user.user_type in ('principal', 'manager')