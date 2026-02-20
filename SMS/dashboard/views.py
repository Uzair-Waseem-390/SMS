from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, get_object_or_404
import logging

from .services.principal import PrincipalDashboardService
from .services.manager import ManagerDashboardService
from .services.accountant import AccountantDashboardService
from .services.teacher import TeacherDashboardService
from .services.student import StudentDashboardService
from .services.parent import ParentDashboardService
from .services.employee import EmployeeDashboardService
from .services.base import BaseDashboardService

logger = logging.getLogger(__name__)


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/index.html"

    def get_service(self, user):
        """Factory method to get the correct service based on user role."""
        if user.is_superuser:
            return PrincipalDashboardService(user)

        role = getattr(user, 'user_type', None)
        service_map = {
            'principal': PrincipalDashboardService,
            'manager': ManagerDashboardService,
            'accountant': AccountantDashboardService,
            'teacher': TeacherDashboardService,
            'student': StudentDashboardService,
            'parent': ParentDashboardService,
            'employee': EmployeeDashboardService,
        }

        service_class = service_map.get(role, BaseDashboardService)
        return service_class(user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        service = self.get_service(user)

        # ── Principal branch-switching support ────────────────────────────
        selected_branch = None
        all_branches = []

        if getattr(user, 'user_type', None) == 'principal':
            try:
                school = user.owned_school
                all_branches = list(school.branches.filter(is_active=True).order_by('-is_main_branch', 'name'))

                branch_param = self.request.GET.get('branch', 'all')

                if branch_param != 'all' and branch_param.isdigit():
                    # Try to find a valid branch by id belonging to this school
                    try:
                        from tenants.models import Branch
                        selected_branch = Branch.objects.get(id=int(branch_param), school=school, is_active=True)
                    except Exception:
                        selected_branch = None

                # Override the service branch so principal can view single or all branches
                service.branch = selected_branch

            except Exception:
                pass

        try:
            dashboard_data = service.get_context()
            context.update(dashboard_data)
        except Exception as e:
            logger.error(f"Error generating dashboard for user {user}: {e}", exc_info=True)
            context['error'] = "An error occurred while loading the dashboard."

        # Inject branch switcher data (principal only)
        context['all_branches'] = all_branches
        context['selected_branch_id'] = selected_branch.id if selected_branch else 'all'

        return context
