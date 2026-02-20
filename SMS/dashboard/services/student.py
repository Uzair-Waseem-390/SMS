from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from .base import BaseDashboardService
from attendance.models import StudentAttendance
from finance.models import StudentFee
from exams.models import Exam, ExamResult
from notification.models import Notification
from certificate.models import Certificate

class StudentDashboardService(BaseDashboardService):
    def _get_kpis(self):
        user = self.user
        if not hasattr(user, 'student_profile'):
            return {}
            
        student = user.student_profile
        branch = self.branch
        
        # 1. Attendance %
        attendance_stats = StudentAttendance.objects.filter(
            student=student
        ).aggregate(
            total=Count('id'),
            present=Count('id', filter=Q(status='present'))
        )
        total_att = attendance_stats['total'] or 0
        present_att = attendance_stats['present'] or 0
        
        attendance_pct = 0
        if total_att > 0:
            attendance_pct = round((present_att / total_att) * 100, 1)

        # 2. Grade Average
        # This is tricky as exams have different total marks.
        # Simple AVG of percentage if stored, or Sum(obtained)/Sum(total).
        # We'll do a simple iteration for now if not huge, or DB annotation.
        # Let's try to do it in python for accuracy with weighted average if needed, 
        # but here simple average of percentages is requested usually.
        # ExamResult has a property percentage but not a DB field (unless I missed it).
        # It calculates in python. So we fetch results.
        results = ExamResult.objects.filter(student=student, exam__is_published=True).select_related('exam')
        total_pct = 0
        count = 0
        for res in results:
            if res.exam.total_marks > 0:
                pct = (float(res.obtained_marks or 0) / res.exam.total_marks) * 100
                total_pct += pct
                count += 1
        
        grade_avg = round(total_pct / count, 1) if count > 0 else 0

        # 3. Pending Fees
        pending_fees = StudentFee.objects.filter(
            student=student,
            status__in=['unpaid', 'partial']
        ).aggregate(
            total_net=Sum('net_amount'),
            total_paid=Sum('amount_paid')
        )
        pending_total = (pending_fees['total_net'] or 0) - (pending_fees['total_paid'] or 0)

        # 4. Upcoming Exams
        upcoming_exams = Exam.objects.filter(
            section=student.section,
            date__gte=self.today,
            is_active=True
        ).count()

        return {
            'attendance_pct': attendance_pct,
            'grade_avg': grade_avg,
            'pending_fees': pending_total,
            'upcoming_exams': upcoming_exams,
        }

    def _get_tables(self):
        user = self.user
        if not hasattr(user, 'student_profile'):
            return {}
        
        student = user.student_profile
        
        # Recent Results
        recent_results = ExamResult.objects.filter(
            student=student,
            exam__is_published=True
        ).select_related('exam', 'exam__subject').order_by('-exam__date')[:5]

        # Fee History
        fee_history = StudentFee.objects.filter(
            student=student
        ).order_by('-due_date')[:5]

        # Announcements
        # Logic: Public OR Students Only OR Private OR (Staff?? No)
        # We filter by branch and validity
        # Notification visibility: public, students, private
        announcements = Notification.objects.filter(
            branch=self.branch,
            is_active=True,
            date__lte=self.today
        ).filter(
            Q(visibility='public') | 
            Q(visibility='students') |
            Q(visibility='private')
        ).order_by('-date', '-time')[:5]
        
        # Filter expired in python or annotation? Model has expires_on property but not DB field.
        # We can just show them for now. Or use duration_days logic if supported by DB func.
        # Keeping it simple: show latest active ones.

        # Certificates
        certificates = Certificate.objects.filter(
            student=student
        ).order_by('-issued_date')[:5]

        return {
            'recent_results': recent_results,
            'fee_history': fee_history,
            'announcements': announcements,
            'certificates': certificates,
        }
