from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings

class Class(models.Model):
    """
    Class Model - Represents a grade/class level in a school branch.
    Example: Grade 1, Grade 2, etc.
    """
    
    # Basic Information
    name = models.CharField(max_length=100, verbose_name="Class Name")
    code = models.CharField(max_length=20, blank=True, verbose_name="Class Code")
    
    # Relationships
    branch = models.ForeignKey(
        'tenants.Branch',
        on_delete=models.CASCADE,
        related_name='classes',
        verbose_name="Branch"
    )
    
    # Class Details
    numeric_level = models.PositiveSmallIntegerField(
        null=True, 
        blank=True,
        verbose_name="Numeric Level",
        help_text="e.g., 1 for Grade 1, 2 for Grade 2"
    )
    
    description = models.TextField(blank=True, verbose_name="Description")
    
    # Status
    is_active = models.BooleanField(default=True, verbose_name="Is Active")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_classes'
    )
    
    class Meta:
        verbose_name = "Class"
        verbose_name_plural = "Classes"
        ordering = ['numeric_level', 'name']
        unique_together = ['name', 'branch']  # One class name per branch
        
    def __str__(self):
        return f"{self.name} - {self.branch.name}"
    
    def save(self, *args, **kwargs):
        if not self.code:
            # Generate class code (e.g., CLS-1 for Grade 1)
            branch_code = self.branch.code[:3].upper() if self.branch.code else 'BR'
            class_num = self.numeric_level or Class.objects.filter(branch=self.branch).count() + 1
            self.code = f"{branch_code}-CLS-{class_num:02d}"
        super().save(*args, **kwargs)
    
    def get_section_count(self):
        """Return number of sections in this class."""
        return self.sections.count()


class Section(models.Model):
    """
    Section Model - Represents a division within a class.
    Example: Grade 1-A, Grade 1-B, etc.
    """
    
    # Basic Information
    name = models.CharField(max_length=50, verbose_name="Section Name")
    code = models.CharField(max_length=20, blank=True, verbose_name="Section Code")
    
    # Relationships
    class_obj = models.ForeignKey(
        Class,
        on_delete=models.CASCADE,
        related_name='sections',
        verbose_name="Class"
    )
    
    # Section Details
    capacity = models.PositiveSmallIntegerField(
        default=30,
        verbose_name="Student Capacity",
        help_text="Maximum number of students"
    )
    
    room_number = models.CharField(max_length=20, blank=True, verbose_name="Room Number")
    description = models.TextField(blank=True, verbose_name="Description")
    
    # Status
    is_active = models.BooleanField(default=True, verbose_name="Is Active")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_sections'
    )
    
    class Meta:
        verbose_name = "Section"
        verbose_name_plural = "Sections"
        ordering = ['class_obj__numeric_level', 'name']
        unique_together = ['name', 'class_obj']  # One section name per class
        
    def __str__(self):
        return f"{self.class_obj.name} - Section {self.name}"
    
    def save(self, *args, **kwargs):
        if not self.code:
            # Generate section code (e.g., 1A for Grade 1 Section A)
            class_code = str(self.class_obj.numeric_level) if self.class_obj.numeric_level else self.class_obj.code[:2]
            self.code = f"{class_code}{self.name.upper()}"
        super().save(*args, **kwargs)
    
    @property
    def branch(self):
        """Get the branch through class."""
        return self.class_obj.branch
    
    def get_subject_count(self):
        """Return number of subjects assigned to this section."""
        return self.subject_assignments.count()


class Subject(models.Model):
    """
    Subject Model - Represents a subject taught in the school.
    Subjects are independent and can be assigned to multiple sections.
    """
    
    # Basic Information
    name = models.CharField(max_length=100, verbose_name="Subject Name")
    code = models.CharField(max_length=20, unique=True, verbose_name="Subject Code")
    
    # Relationships - Subjects belong to a branch
    branch = models.ForeignKey(
        'tenants.Branch',
        on_delete=models.CASCADE,
        related_name='subjects',
        verbose_name="Branch"
    )
    
    # Subject Details
    subject_type = models.CharField(
        max_length=20,
        choices=[
            ('core', 'Core Subject'),
            ('elective', 'Elective'),
            ('language', 'Language'),
            ('science', 'Science'),
            ('arts', 'Arts'),
            ('sports', 'Sports'),
        ],
        default='core',
        verbose_name="Subject Type"
    )
    
    description = models.TextField(blank=True, verbose_name="Description")
    
    # Academic Details
    total_marks = models.PositiveSmallIntegerField(
        default=100,
        verbose_name="Total Marks",
        help_text="Maximum marks for this subject"
    )
    pass_marks = models.PositiveSmallIntegerField(
        default=33,
        verbose_name="Passing Marks",
        help_text="Minimum marks required to pass"
    )
    
    # Status
    is_active = models.BooleanField(default=True, verbose_name="Is Active")
    is_optional = models.BooleanField(default=False, verbose_name="Is Optional")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_subjects'
    )
    
    class Meta:
        verbose_name = "Subject"
        verbose_name_plural = "Subjects"
        ordering = ['name']
        unique_together = ['code', 'branch']  # Unique code per branch
        
    def __str__(self):
        return f"{self.name} ({self.code})"
    
    def clean(self):
        """Validate subject data."""
        if self.pass_marks > self.total_marks:
            raise ValidationError({
                'pass_marks': 'Passing marks cannot be greater than total marks.'
            })
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class SectionSubject(models.Model):
    """
    SectionSubject Model - Many-to-many relationship between sections and subjects.
    This allows a subject to be taught in multiple sections.
    """
    
    section = models.ForeignKey(
        Section,
        on_delete=models.CASCADE,
        related_name='subject_assignments'
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='section_assignments'
    )
    
    # Assignment Details
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_subjects',
        verbose_name="Assigned Teacher",
        help_text="Teacher assigned to teach this subject in this section"
    )
    
    is_active = models.BooleanField(default=True, verbose_name="Is Active")
    
    # Timestamps
    assigned_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='subject_assignments_made'
    )
    
    class Meta:
        verbose_name = "Section Subject Assignment"
        verbose_name_plural = "Section Subject Assignments"
        unique_together = ['section', 'subject']  # One subject per section
        ordering = ['section', 'subject__name']
        
    def __str__(self):
        return f"{self.section} → {self.subject.name}"
    
    @property
    def branch(self):
        """Get the branch through section."""
        return self.section.branch