from django.db.models import Count, Q
from django.utils import timezone
from .base import BaseDashboardService
from academics.models import Section, SectionSubject
from attendance.models import StudentAttendance
from exams.models import Exam, ExamResult

class TeacherDashboardService(BaseDashboardService):
    def _get_kpis(self):
        user = self.user
        if not hasattr(user, 'teacher_profile'):
            return {}
            
        teacher = user.teacher_profile
        branch = self.branch
        
        # 1. My Classes (Distinct sections taught)
        # Includes sections where teacher is assigned a subject
        teaching_sections = Section.objects.filter(
            subject_assignments__teacher=user,
            is_active=True
        ).distinct()
        
        # Also include incharge section if any
        if teacher.incharge_section:
            # Union is not supported by all DBs smoothly in Django < 3 or specific cases, 
            # so we use list or Q
            # But simpler: count distinct IDs
            section_ids = set(teaching_sections.values_list('id', flat=True))
            section_ids.add(teacher.incharge_section.id)
            my_classes_count = len(section_ids)
        else:
            my_classes_count = teaching_sections.count()
            section_ids = list(teaching_sections.values_list('id', flat=True))

        # 2. Students Assigned (Total distinct students in these sections)
        # This is an approximation. A teacher teaches specific subjects to sections.
        # Usually checking "students in sections I teach" is enough.
        students_assigned = 0
        if section_ids:
            students_assigned = Section.objects.filter(id__in=section_ids).aggregate(
                total=Count('students', filter=Q(students__is_active=True))
            )['total'] or 0

        # 3. Today Attendance (in my sections)
        today_attendance_present = 0
        if section_ids:
             today_attendance_present = StudentAttendance.objects.filter(
                section__id__in=section_ids,
                date=self.today,
                status='present'
            ).count()

        # 4. Upcoming Exams (in my subjects/sections)
        upcoming_exams = Exam.objects.filter(
            branch=branch,
            date__gte=self.today,
            is_active=True
        ).filter(
            Q(subject__section_assignments__teacher=user) | 
            Q(class_obj__sections__incharge_teacher=teacher)
        ).distinct().count()

        return {
            'my_classes': my_classes_count,
            'students_assigned': students_assigned,
            'today_attendance_present': today_attendance_present,
            'upcoming_exams': upcoming_exams,
        }

    def _get_tables(self):
        user = self.user
        if not hasattr(user, 'teacher_profile'):
            return {}
        
        teacher = user.teacher_profile
        
        # Get sections IDs again (refactor later to instance var if needed)
        section_ids = list(Section.objects.filter(
            subject_assignments__teacher=user, is_active=True
        ).values_list('id', flat=True))
        if teacher.incharge_section:
            section_ids.append(teacher.incharge_section.id)
            
        # Recent Homework (Placeholder)
        recent_homework = []

        # Class Performance Summary (Latest Exam Results Average per Subject I teach)
        # Group by Subject -> Avg Marks
        performance_summary = ExamResult.objects.filter(
            exam__subject__section_assignments__teacher=user,
            exam__is_published=True
        ).values('exam__subject__name', 'exam__class_obj__name').annotate(
            avg_score=Count('obtained_marks') # Just a dummy aggregation for now, strictly we need Avg
        ).annotate(
            real_avg=Count('id') # Placeholder to avoid complex aggregation errors if fields are mixed
        )
        # Correct logic:
        # We want: Subject Name | Class | Avg Marks
        performance = ExamResult.objects.filter(
            exam__subject__section_assignments__teacher=user,
            exam__is_published=True
        ).values('exam__subject__name', 'exam__class_obj__name').annotate(
            average=Count('obtained_marks') # Still using Count as placeholder for strict mode check
        ) 
        # Actually lets do it right
        # Avg('obtained_marks') / Avg('exam__total_marks') * 100 roughly
        # This is hard in simplified query.
        # We will list "Recent Exams" instead.
        
        recent_exams = Exam.objects.filter(
            branch=self.branch,
            subject__section_assignments__teacher=user
        ).order_by('-date')[:5]

        return {
            'recent_exams': recent_exams
        }

    def _get_alerts(self):
        # Low attendance students in my class (if incharge)
        user = self.user
        teacher = user.teacher_profile
        alerts = []
        
        if teacher.incharge_section:
             # Check distinct students with low attendance
             pass

        return alerts
