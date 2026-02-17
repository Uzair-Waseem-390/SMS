# accounts/utils.py
from django.contrib.auth import get_user_model
from tenants.models import SchoolTenant, Branch

User = get_user_model()

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


def get_user_school(user):
    """
    Get the school associated with a user.
    
    Args:
        user: User instance
    
    Returns:
        SchoolTenant or None: The user's school if exists
    """
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
    
    For principals with multiple branches, supports branch selection via:
    - request.GET.get('branch_id')
    - request.session.get('academics_branch_id')
    
    Args:
        user: User instance
        request: Optional HttpRequest for branch selection (principals with multiple branches)
    
    Returns:
        Branch or None: The user's branch if exists
    """
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
            # Branch selection for principals with multiple branches
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
            # Teacher branch from UserRole (rbac)
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