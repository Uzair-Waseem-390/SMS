from django.db.models import Count, Sum, Q
from .base import BaseDashboardService
from attendance.models import StudentAttendance
from finance.models import StudentFee
from exams.models import ExamResult
from notification.models import Notification

class ParentDashboardService(BaseDashboardService):
    def get_context(self):
        # Override to add children list
        context = super().get_context()
        if hasattr(self.user, 'parent_profile'):
            context['children'] = self.user.parent_profile.students.filter(is_active=True)
        return context

    def _get_kpis(self):
        user = self.user
        if not hasattr(user, 'parent_profile'):
            return {}
            
        parent = user.parent_profile
        # Logic: Aggregate for all children
        students = parent.students.filter(is_active=True)
        
        # 1. Attendance % (Average across all children)
        total_att_pct = 0
        count_att = 0
        for student in students:
            stats = StudentAttendance.objects.filter(student=student).aggregate(
                total=Count('id'),
                present=Count('id', filter=Q(status='present'))
            )
            if stats['total'] and stats['total'] > 0:
                total_att_pct += (stats['present'] / stats['total']) * 100
                count_att += 1
        
        avg_attendance = round(total_att_pct / count_att, 1) if count_att > 0 else 0

        # 2. Key Academic Average (Average across all children)
        # Simplified: average of latest exam results
        total_grade_pct = 0
        count_grade = 0
        for student in students:
             results = ExamResult.objects.filter(
                 student=student, exam__is_published=True
             ).select_related('exam')
             # limit to recent? or all?
             # let's take average of all time for now as "cumulative GPA" style
             s_total_pct = 0
             s_count = 0
             for res in results:
                 if res.exam.total_marks > 0:
                     s_total_pct += (float(res.obtained_marks or 0) / res.exam.total_marks) * 100
                     s_count += 1
             if s_count > 0:
                 total_grade_pct += (s_total_pct / s_count)
                 count_grade += 1
                 
        avg_grade = round(total_grade_pct / count_grade, 1) if count_grade > 0 else 0

        # 3. Fee Status (Total Pending)
        pending_fees = StudentFee.objects.filter(
            student__in=students,
            status__in=['unpaid', 'partial']
        ).aggregate(
            total_net=Sum('net_amount'),
            total_paid=Sum('amount_paid')
        )
        total_pending = (pending_fees['total_net'] or 0) - (pending_fees['total_paid'] or 0)

        return {
            'avg_attendance_pct': avg_attendance,
            'avg_grade': avg_grade,
            'total_pending_fees': total_pending,
        }

    def _get_tables(self):
        user = self.user
        if not hasattr(user, 'parent_profile'):
            return {}
            
        parent = user.parent_profile
        students = parent.students.filter(is_active=True)
        
        # Payment History (Recent for all children)
        payment_history = StudentFee.objects.filter(
            student__in=students
        ).select_related('student').order_by('-paid_date', '-due_date')[:5]
        
        # Performance Trend (Latest results)
        recent_performance = ExamResult.objects.filter(
            student__in=students,
            exam__is_published=True
        ).select_related('student', 'exam', 'exam__subject').order_by('-exam__date')[:5]
        
        # Notices (Parents Only or Public or Private)
        notices = Notification.objects.filter(
            branch=self.branch, # Assumes main branch of first child or resolved branch
            is_active=True,
            date__lte=self.today
        ).filter(
            Q(visibility='public') | 
            Q(visibility='parents') |
            Q(visibility='private')
        ).order_by('-date')[:5]

        return {
            'payment_history': payment_history,
            'recent_performance': recent_performance,
            'notices': notices,
        }
