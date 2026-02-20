from django.utils import timezone
from django.db.models import Sum, Count, Avg, F, Q
from django.core.exceptions import ObjectDoesNotExist
import datetime

class BaseDashboardService:
    """
    Base service for dashboard data retrieval.
    Enforces tenant and branch isolation.
    """
    
    def __init__(self, user):
        self.user = user
        self.today = timezone.now().date()
        self.current_month = self.today.month
        self.current_year = self.today.year
        
        # Resolve Tenant (School)
        if hasattr(user, 'owned_school'):
            self.school = user.owned_school
        elif hasattr(user, 'managed_branch'):
            self.school = user.managed_branch.school
        else:
            # Try to resolve through profile relationships
            self.school = self._resolve_school()
            
        # Resolve Branch
        self.branch = self._resolve_branch()

    def _resolve_school(self):
        """Helper to resolve school for non-owner/manager roles."""
        user = self.user
        if hasattr(user, 'teacher_profile'):
            return user.teacher_profile.school
        elif hasattr(user, 'accountant_profile'):
            return user.accountant_profile.school
        elif hasattr(user, 'employee_profile'):
            return user.employee_profile.school
        elif hasattr(user, 'student_profile'):
            return user.student_profile.section.branch.school
        elif hasattr(user, 'parent_profile'):
            # Parent might be linked to multiple students in same school (assumption)
            student = user.parent_profile.students.first()
            return student.section.branch.school if student else None
        return None

    def _resolve_branch(self):
        """Helper to resolve branch."""
        user = self.user
        if hasattr(user, 'managed_branch'):
            return user.managed_branch
        elif hasattr(user, 'teacher_profile'):
            return user.teacher_profile.branch
        elif hasattr(user, 'accountant_profile'):
            return user.accountant_profile.branch
        elif hasattr(user, 'employee_profile'):
            return user.employee_profile.branch
        elif hasattr(user, 'student_profile'):
            return user.student_profile.section.branch
        return None  # Principal might look at all or specific, handled in PrincipalService

    def get_context(self):
        """
        Main entry point for views.
        Returns a dictionary with kpis, charts, alerts, and tables.
        """
        return {
            'role': self.user.user_type,
            'school': self.school,
            'branch': self.branch,
            'kpis': self._get_kpis(),
            'charts': self._get_charts(),
            'alerts': self._get_alerts(),
            'tables': self._get_tables(),
            'greeting': self._get_greeting(),
        }

    def _get_greeting(self):
        hour = timezone.now().hour
        if hour < 12:
            return "Good Morning"
        elif 12 <= hour < 18:
            return "Good Afternoon"
        else:
            return "Good Evening"

    # Abstract methods to be implemented by subclasses
    def _get_kpis(self):
        return {}

    def _get_charts(self):
        return {}

    def _get_alerts(self):
        return []

    def _get_tables(self):
        return {}
