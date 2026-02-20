def school_branch_context(request):
    """
    Makes current_school and current_branch available in all templates.
    Uses middleware-set values first, falls back to user relationships.
    For principals, also checks session for branch switching.
    """
    school = getattr(request, 'current_school', None)
    branch = getattr(request, 'current_branch', None)

    if not school and hasattr(request, 'user') and request.user.is_authenticated:
        from accounts.utils import get_user_school, get_user_branch
        school = school or get_user_school(request.user, request)
        branch = branch or get_user_branch(request.user, request)

    # ── Principal branch switching via session ──────────────────────────
    # If a principal has chosen a branch via the sidebar dropdown,
    # override the default branch to keep sb_url links consistent.
    all_branches = []
    if (
        hasattr(request, 'user')
        and request.user.is_authenticated
        and getattr(request.user, 'user_type', '') == 'principal'
        and school
    ):
        all_branches = list(school.branches.filter(is_active=True).order_by('-is_main_branch', 'name'))
        session_branch_id = request.session.get('active_branch_id')
        if session_branch_id and not getattr(request, 'current_branch', None):
            # Only override if middleware didn't already set a branch from the URL
            from tenants.models import Branch
            try:
                branch = Branch.objects.get(id=session_branch_id, school=school, is_active=True)
            except Branch.DoesNotExist:
                # Session had stale branch, clear it
                request.session.pop('active_branch_id', None)
                if all_branches:
                    branch = all_branches[0]
        elif not branch and all_branches:
            branch = all_branches[0]

    return {
        'current_school': school,
        'current_branch': branch,
        'principal_branches': all_branches,
    }
