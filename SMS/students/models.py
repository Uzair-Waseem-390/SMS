from django.db import models
from django.core.validators import RegexValidator, MinLengthValidator
from django.utils import timezone
from django.conf import settings
import uuid

class Student(models.Model):
    """
    Student Model - Represents a student enrolled in a section.
    Each student has a linked user account for login.
    """
    
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ]
    
    BLOOD_GROUP_CHOICES = [
        ('A+', 'A+'), ('A-', 'A-'),
        ('B+', 'B+'), ('B-', 'B-'),
        ('O+', 'O+'), ('O-', 'O-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'),
    ]
    
    # Phone number validation
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in format: '+999999999'. Up to 15 digits allowed."
    )
    
    # Basic Information
    admission_number = models.CharField(
        max_length=50, 
        unique=True,
        verbose_name="Admission Number"
    )
    roll_number = models.CharField(
        max_length=20, 
        blank=True,
        verbose_name="Roll Number"
    )
    
    # Personal Information
    first_name = models.CharField(max_length=100, verbose_name="First Name")
    last_name = models.CharField(max_length=100, verbose_name="Last Name")
    father_name = models.CharField(max_length=200, verbose_name="Father's Name")
    mother_name = models.CharField(max_length=200, blank=True, verbose_name="Mother's Name")
    
    # Date of Birth
    date_of_birth = models.DateField(null=True, blank=True, verbose_name="Date of Birth")
    
    # Gender
    gender = models.CharField(
        max_length=10, 
        choices=GENDER_CHOICES,
        blank=True,
        verbose_name="Gender"
    )
    
    # Contact Information
    phone_number = models.CharField(
        validators=[phone_regex], 
        max_length=17, 
        blank=True,
        verbose_name="Phone Number"
    )
    email = models.EmailField(blank=True, verbose_name="Email Address")
    alternate_phone = models.CharField(
        validators=[phone_regex], 
        max_length=17, 
        blank=True,
        verbose_name="Alternate Phone"
    )
    
    # Address
    address = models.TextField(blank=True, verbose_name="Address")
    city = models.CharField(max_length=100, blank=True, verbose_name="City")
    postal_code = models.CharField(max_length=20, blank=True, verbose_name="Postal Code")
    
    # Academic Information
    section = models.ForeignKey(
        'academics.Section',
        on_delete=models.CASCADE,
        related_name='students',
        verbose_name="Section"
    )
    
    # Additional Details
    blood_group = models.CharField(
        max_length=5, 
        choices=BLOOD_GROUP_CHOICES,
        blank=True,
        verbose_name="Blood Group"
    )
    
    # Medical Information
    medical_conditions = models.TextField(
        blank=True,
        verbose_name="Medical Conditions",
        help_text="Any medical conditions or allergies"
    )
    
    emergency_contact_name = models.CharField(
        max_length=200, 
        blank=True,
        verbose_name="Emergency Contact Name"
    )
    emergency_contact_phone = models.CharField(
        validators=[phone_regex], 
        max_length=17, 
        blank=True,
        verbose_name="Emergency Contact Phone"
    )
    
    # Profile Picture
    profile_picture = models.ImageField(
        upload_to='student_profiles/',
        null=True,
        blank=True,
        verbose_name="Profile Picture"
    )
    
    # Status
    is_active = models.BooleanField(default=True, verbose_name="Is Active")
    enrollment_date = models.DateField(default=timezone.now, verbose_name="Enrollment Date")
    
    # Audit Fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_students'
    )
    
    # Linked User Account
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='student_profile',
        null=True,
        blank=True
    )

    # Scholarship
    scholarship = models.ForeignKey(
        'finance.Scholarship',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='students',
        verbose_name="Scholarship"
    )
    
    class Meta:
        verbose_name = "Student"
        verbose_name_plural = "Students"
        ordering = ['first_name', 'last_name']
        indexes = [
            models.Index(fields=['admission_number']),
            models.Index(fields=['section', 'is_active']),
            models.Index(fields=['first_name', 'last_name']),
        ]
        
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.admission_number})"
    
    @property
    def full_name(self):
        """Return full name of student."""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def branch(self):
        """Get branch through section."""
        return self.section.branch
    
    def save(self, *args, **kwargs):
        if not self.admission_number:
            # Generate unique admission number
            year = timezone.now().strftime('%y')
            branch_code = self.section.branch.code[:3].upper() if self.section.branch.code else 'SCH'
            last_student = Student.objects.filter(
                admission_number__startswith=f"{branch_code}{year}"
            ).order_by('-admission_number').first()
            
            if last_student:
                last_num = int(last_student.admission_number[-4:])
                new_num = last_num + 1
            else:
                new_num = 1
            
            self.admission_number = f"{branch_code}{year}{new_num:04d}"
        
        super().save(*args, **kwargs)


class Parent(models.Model):
    """
    Parent Model - Represents a parent/guardian of one or more students.
    Each parent has a linked user account for login.
    """
    
    RELATIONSHIP_CHOICES = [
        ('father', 'Father'),
        ('mother', 'Mother'),
        ('guardian', 'Legal Guardian'),
        ('other', 'Other'),
    ]
    
    # Phone number validation
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in format: '+999999999'. Up to 15 digits allowed."
    )
    
    # Basic Information
    first_name = models.CharField(max_length=100, verbose_name="First Name")
    last_name = models.CharField(max_length=100, verbose_name="Last Name")
    relationship = models.CharField(
        max_length=20,
        choices=RELATIONSHIP_CHOICES,
        default='guardian',
        verbose_name="Relationship to Student"
    )
    
    # Contact Information
    phone_number = models.CharField(
        validators=[phone_regex], 
        max_length=17,
        verbose_name="Phone Number"
    )
    alternate_phone = models.CharField(
        validators=[phone_regex], 
        max_length=17, 
        blank=True,
        verbose_name="Alternate Phone"
    )
    email = models.EmailField(verbose_name="Email Address")
    
    # Personal Information
    occupation = models.CharField(max_length=200, blank=True, verbose_name="Occupation")
    qualification = models.CharField(max_length=200, blank=True, verbose_name="Qualification")
    
    # Address (if different from student)
    address = models.TextField(blank=True, verbose_name="Address")
    city = models.CharField(max_length=100, blank=True, verbose_name="City")
    
    # Profile Picture
    profile_picture = models.ImageField(
        upload_to='parent_profiles/',
        null=True,
        blank=True,
        verbose_name="Profile Picture"
    )
    
    # Students linked to this parent
    students = models.ManyToManyField(
        Student,
        related_name='parents',
        verbose_name="Students"
    )
    
    # Status
    is_active = models.BooleanField(default=True, verbose_name="Is Active")
    
    # Audit Fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_parents'
    )
    
    # Linked User Account
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='parent_profile',
        null=True,
        blank=True
    )
    
    class Meta:
        verbose_name = "Parent"
        verbose_name_plural = "Parents"
        ordering = ['first_name', 'last_name']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['phone_number']),
        ]
        
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.get_relationship_display()})"
    
    @property
    def full_name(self):
        """Return full name of parent."""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def branch(self):
        """Get branch through first student."""
        first_student = self.students.first()
        return first_student.branch if first_student else None