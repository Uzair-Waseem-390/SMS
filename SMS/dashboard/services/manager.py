from django.db.models import Count, Sum, F
from django.utils import timezone
from .base import BaseDashboardService
from students.models import Student
from staff.models import Teacher, Employee, Accountant
from academics.models import Section
from attendance.models import StudentAttendance

class ManagerDashboardService(BaseDashboardService):
    def _get_kpis(self):
        branch = self.branch
        if not branch:
            return {}

        # 1. Admissions This Month
        admissions_this_month = Student.objects.filter(
            section__class_obj__branch=branch,
            enrollment_date__month=self.current_month,
            enrollment_date__year=self.current_year
        ).count()

        # 2. Active Staff
        total_teachers = Teacher.objects.filter(branch=branch, is_active=True).count()
        total_employees = Employee.objects.filter(branch=branch, is_active=True).count()
        total_accountants = Accountant.objects.filter(branch=branch, is_active=True).count()
        active_staff = total_teachers + total_employees + total_accountants

        # 3. Class Capacity %
        capacity_stats = Section.objects.filter(class_obj__branch=branch, is_active=True).aggregate(
            total_capacity=Sum('capacity'),
            current_students=Count('students', filter=F('students__is_active')==True)
        )
        total_capacity = capacity_stats['total_capacity'] or 0
        current_students_count = capacity_stats['current_students'] or 0
        
        capacity_pct = 0
        if total_capacity > 0:
            capacity_pct = round((current_students_count / total_capacity) * 100, 1)

        # 4. Leave Requests Pending (Placeholder as model not found)
        leave_requests_pending = 0 

        return {
            'admissions_this_month': admissions_this_month,
            'active_staff': active_staff,
            'class_capacity_pct': capacity_pct,
            'leave_requests_pending': leave_requests_pending,
        }

    def _get_tables(self):
        branch = self.branch
        if not branch:
            return {}
            
        # Recent Admissions
        recent_admissions = Student.objects.filter(
            section__class_obj__branch=branch,
            is_active=True
        ).select_related('section', 'section__class_obj').order_by('-enrollment_date')[:5]
        
        return {
            'recent_admissions': recent_admissions
        }

    def _get_charts(self):
        # Similar logic to Principal but strictly for this branch
        # Omitting for brevity unless requested, focusing on specific Manager views
        return {}
