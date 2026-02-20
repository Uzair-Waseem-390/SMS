from django.db.models import Count, Sum, Avg, Q
from django.db.models.functions import TruncMonth, TruncDay
from django.utils import timezone
from .base import BaseDashboardService
from students.models import Student
from staff.models import Teacher, Employee, Accountant
from academics.models import Class
from attendance.models import StudentAttendance, StaffAttendance
from finance.models import StudentFee
from certificate.models import Certificate
from exams.models import ExamResult
import datetime

class PrincipalDashboardService(BaseDashboardService):
    def _get_kpis(self):
        # Base filters
        branch_filter = {'section__class_obj__branch': self.branch} if self.branch else {'section__class_obj__branch__school': self.school}
        staff_branch_filter = {'branch': self.branch} if self.branch else {'school': self.school}
        
        # 1. Total Students
        total_students = Student.objects.filter(is_active=True, **branch_filter).count()
        
        # 2. Total Teachers
        total_teachers = Teacher.objects.filter(is_active=True, **staff_branch_filter).count()
        
        # 3. Total Staff (Employees + Accountants)
        total_employees = Employee.objects.filter(is_active=True, **staff_branch_filter).count()
        total_accountants = Accountant.objects.filter(is_active=True, **staff_branch_filter).count()
        total_staff = total_employees + total_accountants
        
        # 4. Today's Student Attendance %
        attendance_filter = {'branch': self.branch} if self.branch else {'school': self.school}
        today_attendance = StudentAttendance.objects.filter(
            date=self.today, 
            **attendance_filter
        ).aggregate(
            total=Count('id'),
            present=Count('id', filter=Q(status='present'))
        )
        validation_total = today_attendance['total'] or 0
        present_total = today_attendance['present'] or 0
        attendance_pct = round((present_total / validation_total) * 100, 1) if validation_total > 0 else 0
        
        # 5. Monthly Fee Collection
        fee_filter = {'branch': self.branch} if self.branch else {'school': self.school}
        monthly_fee = StudentFee.objects.filter(
            paid_date__month=self.current_month,
            paid_date__year=self.current_year,
            status='paid',
            **fee_filter
        ).aggregate(total=Sum('amount_paid'))['total'] or 0
        
        # 6. Pending Fee Total
        pending_fee = StudentFee.objects.filter(
            status__in=['unpaid', 'partial'],
            **fee_filter
        ).aggregate(
            total_net=Sum('net_amount'),
            total_paid=Sum('amount_paid')
        )
        pending_total = (pending_fee['total_net'] or 0) - (pending_fee['total_paid'] or 0)
        
        # 7. Active Classes
        class_filter = {'branch': self.branch} if self.branch else {'branch__school': self.school}
        active_classes = Class.objects.filter(is_active=True, **class_filter).count()
        
        # 8. Certificates Issued (Monthly)
        cert_filter = {'branch': self.branch} if self.branch else {'school': self.school}
        certs_issued = Certificate.objects.filter(
            issued_date__month=self.current_month,
            issued_date__year=self.current_year,
            **cert_filter
        ).count()

        return {
            'total_students': total_students,
            'total_teachers': total_teachers,
            'total_staff': total_staff,
            'attendance_pct': attendance_pct,
            'monthly_fee_collection': monthly_fee,
            'pending_fee_total': pending_total,
            'active_classes': active_classes,
            'certificates_issued': certs_issued,
        }

    def _get_charts(self):
        charts = {}
        branch_filter = {'section__class_obj__branch': self.branch} if self.branch else {'section__class_obj__branch__school': self.school}
        fee_filter = {'branch': self.branch} if self.branch else {'school': self.school}
        
        # Chart 1: Enrollment Trend (Last 6 Months)
        six_months_ago = self.today - datetime.timedelta(days=180)
        enrollment_trend = Student.objects.filter(
            enrollment_date__gte=six_months_ago,
            **branch_filter
        ).annotate(
            month=TruncMonth('enrollment_date')
        ).values('month').annotate(
            count=Count('id')
        ).order_by('month')
        
        charts['enrollment_trend'] = {
            'labels': [item['month'].strftime('%b %Y') for item in enrollment_trend],
            'data': [item['count'] for item in enrollment_trend]
        }
        
        # Chart 2: Fee Collection Trend (Last 6 Months)
        fee_trend = StudentFee.objects.filter(
            paid_date__gte=six_months_ago,
            status='paid',
            **fee_filter
        ).annotate(
            month=TruncMonth('paid_date')
        ).values('month').annotate(
            total=Sum('amount_paid')
        ).order_by('month')
        
        charts['fee_trend'] = {
            'labels': [item['month'].strftime('%b %Y') for item in fee_trend],
            'data': [float(item['total'] or 0) for item in fee_trend]
        }
        
        # Chart 3: Attendance Weekly Trend
        seven_days_ago = self.today - datetime.timedelta(days=7)
        att_filter = {'branch': self.branch} if self.branch else {'school': self.school}
        attendance_trend = StudentAttendance.objects.filter(
            date__gte=seven_days_ago,
            **att_filter
        ).annotate(
            day=TruncDay('date')
        ).values('day').annotate(
            present=Count('id', filter=Q(status='present')),
            total=Count('id')
        ).order_by('day')
        
        att_data = []
        att_labels = []
        for item in attendance_trend:
            pct = round((item['present'] / item['total'] * 100), 1) if item['total'] > 0 else 0
            att_data.append(pct)
            att_labels.append(item['day'].strftime('%a'))
            
        charts['attendance_trend'] = {
            'labels': att_labels,
            'data': att_data
        }

        return charts

    def _get_alerts(self):
        alerts = []
        branch_filter = {'section__class_obj__branch': self.branch} if self.branch else {'section__class_obj__branch__school': self.school}
        staff_filter = {'branch': self.branch} if self.branch else {'school': self.school}
        
        # Alert 1: Low Attendance Students (< 75% overall) - Sample top 5
        # Calculation might be expensive on large usage, so limiting to recent check or simplified logic
        # For optimization, we rely on a pre-calculated field or a simpler query if possible.
        # Here we just check 'consecutive absent' or similar if easy, but sticking to request:
        # We will check attendance for current month only to be fast.
        
        low_att_students = StudentAttendance.objects.filter(
            date__month=self.current_month,
            **{'branch': self.branch} if self.branch else {'school': self.school}
        ).values('student__first_name', 'student__last_name').annotate(
            present=Count('id', filter=Q(status='present')),
            total=Count('id')
        ).filter(total__gt=0)
        
        # Filtering in python for percentage to avoid complex DB math if sqlite
        count = 0
        for stat in low_att_students:
            pct = (stat['present'] / stat['total']) * 100
            if pct < 75:
                alerts.append({
                    'type': 'warning',
                    'message': f"Student {stat['student__first_name']} {stat['student__last_name']} has low attendance ({round(pct)}%)"
                })
                count += 1
                if count >= 5: break

        # Alert 2: Staff Absent Today
        absent_staff = StaffAttendance.objects.filter(
            date=self.today,
            status='absent',
            **staff_filter
        ).select_related('user')[:5]
        
        for staff in absent_staff:
            alerts.append({
                'type': 'danger',
                'message': f"Staff {staff.user.get_full_name()} is absent today."
            })

        return alerts
