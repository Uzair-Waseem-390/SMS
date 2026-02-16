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