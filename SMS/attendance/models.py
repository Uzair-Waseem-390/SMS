from django.db import models
from django.conf import settings
from django.utils import timezone


STUDENT_STATUS_CHOICES = [
    ('present', 'Present'),
    ('late', 'Late'),
    ('absent', 'Absent'),
    ('leave', 'Leave'),
    ('halfleave', 'Half Leave'),
]

STAFF_STATUS_CHOICES = [
    ('present', 'Present'),
    ('late', 'Late'),
    ('absent', 'Absent'),
    ('leave', 'Leave'),
    ('halfleave', 'Half Leave'),
]


class StudentAttendance(models.Model):
    """Attendance record for a single student on a single date."""

    student = models.ForeignKey(
        'students.Student', on_delete=models.CASCADE,
        related_name='attendance_records', verbose_name="Student"
    )
    section = models.ForeignKey(
        'academics.Section', on_delete=models.CASCADE,
        related_name='student_attendance', verbose_name="Section"
    )
    date = models.DateField(default=timezone.now, verbose_name="Date")
    status = models.CharField(
        max_length=10, choices=STUDENT_STATUS_CHOICES,
        default='present', verbose_name="Status"
    )
    remarks = models.CharField(max_length=255, blank=True, verbose_name="Remarks")

    branch = models.ForeignKey(
        'tenants.Branch', on_delete=models.CASCADE,
        related_name='student_attendance', verbose_name="Branch"
    )
    school = models.ForeignKey(
        'tenants.SchoolTenant', on_delete=models.CASCADE,
        related_name='student_attendance', verbose_name="School"
    )

    marked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='marked_student_attendance'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Student Attendance"
        verbose_name_plural = "Student Attendance"
        unique_together = ['student', 'date']
        ordering = ['-date', 'student__first_name']
        indexes = [
            models.Index(fields=['date', 'section']),
            models.Index(fields=['student', 'date']),
        ]

    def __str__(self):
        return f"{self.student.full_name} - {self.date} - {self.get_status_display()}"


class StaffAttendance(models.Model):
    """
    Attendance record for a staff member on a single date.
    Covers teachers (via user FK), accountants, and employees.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='staff_attendance_records', verbose_name="Staff User"
    )
    date = models.DateField(default=timezone.now, verbose_name="Date")
    status = models.CharField(
        max_length=10, choices=STAFF_STATUS_CHOICES,
        default='present', verbose_name="Status"
    )
    late_time = models.TimeField(
        null=True, blank=True, verbose_name="Late Arrival Time",
        help_text="The time the staff member arrived (if late)"
    )
    half_leave_time = models.TimeField(
        null=True, blank=True, verbose_name="Half Leave Time",
        help_text="The time the staff member left on half leave"
    )
    remarks = models.CharField(max_length=255, blank=True, verbose_name="Remarks")

    branch = models.ForeignKey(
        'tenants.Branch', on_delete=models.CASCADE,
        related_name='staff_attendance', verbose_name="Branch"
    )
    school = models.ForeignKey(
        'tenants.SchoolTenant', on_delete=models.CASCADE,
        related_name='staff_attendance', verbose_name="School"
    )

    marked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='marked_staff_attendance'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Staff Attendance"
        verbose_name_plural = "Staff Attendance"
        unique_together = ['user', 'date']
        ordering = ['-date', 'user__full_name']
        indexes = [
            models.Index(fields=['date', 'branch']),
            models.Index(fields=['user', 'date']),
        ]

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.date} - {self.get_status_display()}"
