def school_branch_context(request):
    """
    Makes current_school and current_branch available in all templates.
    Uses middleware-set values first, falls back to user relationships.
    """
    school = getattr(request, 'current_school', None)
    branch = getattr(request, 'current_branch', None)

    if not school and hasattr(request, 'user') and request.user.is_authenticated:
        from accounts.utils import get_user_school, get_user_branch
        school = school or get_user_school(request.user, request)
        branch = branch or get_user_branch(request.user, request)

    return {
        'current_school': school,
        'current_branch': branch,
    }
