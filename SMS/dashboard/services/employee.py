from django.db.models import Count, Q
from .base import BaseDashboardService
from attendance.models import StaffAttendance
from finance.models import SalaryRecord
from notification.models import Notification

class EmployeeDashboardService(BaseDashboardService):
    def _get_kpis(self):
        user = self.user
        branch = self.branch
        if not branch:
            return {}
            
        # 1. Attendance This Month
        attendance_stats = StaffAttendance.objects.filter(
            user=user,
            date__month=self.current_month,
            date__year=self.current_year
        ).aggregate(
            present=Count('id', filter=Q(status='present')),
            leaves=Count('id', filter=Q(status__in=['leave', 'halfleave']))
        )
        
        present_count = attendance_stats['present'] or 0
        leaves_taken = attendance_stats['leaves'] or 0
        
        department = "Staff"
        if hasattr(user, 'employee_profile'):
            department = user.employee_profile.get_employee_type_display()
        elif hasattr(user, 'accountant_profile'):
            department = "Accounts"

        return {
            'present_days': present_count,
            'leaves_taken': leaves_taken,
            'department': department,
        }

    def _get_tables(self):
        user = self.user
        branch = self.branch
        if not branch:
            return {}
            
        # Salary Slips (Paid)
        salary_slips = SalaryRecord.objects.filter(
            employee=user,
            status='paid'
        ).order_by('-year', '-month')[:6]
        
        # Announcements (Staff or Public or Private)
        announcements = Notification.objects.filter(
            branch=branch,
            is_active=True,
            date__lte=self.today
        ).filter(
            Q(visibility='public') | 
            Q(visibility='staff') |
            Q(visibility='private')
        ).order_by('-date')[:5]

        return {
            'salary_slips': salary_slips,
            'announcements': announcements
        }
