import uuid

from django.db import models
from django.conf import settings
from django.utils import timezone


EXAM_TYPE_CHOICES = [
    ('mid_term', 'Mid Term'),
    ('final', 'Final'),
    ('unit_test', 'Unit Test'),
    ('monthly_test', 'Monthly Test'),
    ('quarterly_test', 'Quarterly Test'),
    ('yearly_test', 'Yearly Test'),
    ('annual_test', 'Annual Test'),
    ('other', 'Other'),
]

EXAM_ATTENDANCE_CHOICES = [
    ('present', 'Present'),
    ('absent', 'Absent'),
    ('leave', 'Leave'),
]


class Exam(models.Model):
    """An exam scheduled for a specific subject in a specific section."""

    name = models.CharField(max_length=200, verbose_name="Exam Name")
    exam_type = models.CharField(max_length=20, choices=EXAM_TYPE_CHOICES, verbose_name="Exam Type")

    date = models.DateField(verbose_name="Exam Date")
    start_time = models.TimeField(verbose_name="Start Time")
    duration_minutes = models.PositiveIntegerField(verbose_name="Duration (minutes)", help_text="Duration in minutes")

    subject = models.ForeignKey(
        'academics.Subject', on_delete=models.CASCADE,
        related_name='exams', verbose_name="Subject"
    )
    class_obj = models.ForeignKey(
        'academics.Class', on_delete=models.CASCADE,
        related_name='exams', verbose_name="Class"
    )
    section = models.ForeignKey(
        'academics.Section', on_delete=models.CASCADE,
        related_name='exams', verbose_name="Section"
    )

    total_marks = models.PositiveIntegerField(default=100, verbose_name="Total Marks")
    passing_marks = models.PositiveIntegerField(default=33, verbose_name="Passing Marks")

    description = models.TextField(blank=True, verbose_name="Description / Instructions")

    branch = models.ForeignKey(
        'tenants.Branch', on_delete=models.CASCADE,
        related_name='exams', verbose_name="Branch"
    )
    school = models.ForeignKey(
        'tenants.SchoolTenant', on_delete=models.CASCADE,
        related_name='exams', verbose_name="School"
    )

    batch_id = models.UUIDField(
        null=True, blank=True, db_index=True,
        verbose_name="Batch ID",
        help_text="Groups exams created together across multiple sections"
    )

    is_published = models.BooleanField(default=False, verbose_name="Results Published")
    is_active = models.BooleanField(default=True, verbose_name="Is Active")

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='created_exams'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Exam"
        verbose_name_plural = "Exams"
        ordering = ['-date', 'start_time']
        indexes = [
            models.Index(fields=['date', 'section']),
            models.Index(fields=['branch', 'is_active']),
        ]

    def __str__(self):
        return f"{self.name} - {self.subject.name} ({self.section})"

    @property
    def duration_display(self):
        h, m = divmod(self.duration_minutes, 60)
        return f"{h}h {m}m" if h else f"{m}m"

    @property
    def student_count(self):
        return self.section.students.filter(is_active=True).count()

    @property
    def sibling_exams(self):
        """Other exams created in the same batch."""
        if self.batch_id:
            return Exam.objects.filter(batch_id=self.batch_id, is_active=True).exclude(id=self.id)
        return Exam.objects.none()


class ExamAttendance(models.Model):
    """Attendance record for a student in a specific exam."""

    exam = models.ForeignKey(
        Exam, on_delete=models.CASCADE,
        related_name='attendance_records', verbose_name="Exam"
    )
    student = models.ForeignKey(
        'students.Student', on_delete=models.CASCADE,
        related_name='exam_attendance', verbose_name="Student"
    )
    status = models.CharField(
        max_length=10, choices=EXAM_ATTENDANCE_CHOICES,
        default='present', verbose_name="Attendance Status"
    )
    remarks = models.CharField(max_length=255, blank=True, verbose_name="Remarks")

    marked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='marked_exam_attendance'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Exam Attendance"
        verbose_name_plural = "Exam Attendance"
        unique_together = ['exam', 'student']
        ordering = ['student__first_name']

    def __str__(self):
        return f"{self.student.full_name} - {self.exam.name} - {self.get_status_display()}"


class ExamResult(models.Model):
    """Result / marks for a student in a specific exam."""

    exam = models.ForeignKey(
        Exam, on_delete=models.CASCADE,
        related_name='results', verbose_name="Exam"
    )
    student = models.ForeignKey(
        'students.Student', on_delete=models.CASCADE,
        related_name='exam_results', verbose_name="Student"
    )
    obtained_marks = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True,
        verbose_name="Obtained Marks"
    )
    grade = models.CharField(max_length=5, blank=True, verbose_name="Grade")
    remarks = models.CharField(max_length=255, blank=True, verbose_name="Remarks")
    is_absent = models.BooleanField(default=False, verbose_name="Absent (no marks)")

    entered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='entered_results'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Exam Result"
        verbose_name_plural = "Exam Results"
        unique_together = ['exam', 'student']
        ordering = ['student__first_name']

    def __str__(self):
        return f"{self.student.full_name} - {self.exam.name} - {self.obtained_marks}/{self.exam.total_marks}"

    @property
    def percentage(self):
        if self.obtained_marks is not None and self.exam.total_marks:
            return round(float(self.obtained_marks) / self.exam.total_marks * 100, 1)
        return 0

    @property
    def is_passed(self):
        if self.is_absent:
            return False
        if self.obtained_marks is not None:
            return float(self.obtained_marks) >= self.exam.passing_marks
        return False

    def compute_grade(self):
        pct = self.percentage
        if self.is_absent:
            return 'AB'
        if pct >= 90:
            return 'A+'
        elif pct >= 80:
            return 'A'
        elif pct >= 70:
            return 'B'
        elif pct >= 60:
            return 'C'
        elif pct >= 50:
            return 'D'
        elif pct >= 33:
            return 'E'
        return 'F'

    def save(self, *args, **kwargs):
        if not self.grade:
            self.grade = self.compute_grade()
        super().save(*args, **kwargs)
