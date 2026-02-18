from django.db import models
from django.core.validators import RegexValidator
from django.utils import timezone
from django.conf import settings


class Employee(models.Model):
    """
    Employee Model - Represents non-teaching staff members.
    Teachers and Accountants have their own models.
    Employee types: guard, clerk, cleaner, driver, other.
    """

    EMPLOYEE_TYPE_CHOICES = [
        ('guard', 'Guard'),
        ('clerk', 'Clerk'),
        ('cleaner', 'Cleaner'),
        ('driver', 'Driver'),
        ('other', 'Other'),
    ]

    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in format: '+999999999'. Up to 15 digits allowed."
    )

    employee_id = models.CharField(max_length=50, unique=True, verbose_name="Employee ID")

    first_name = models.CharField(max_length=100, verbose_name="First Name")
    last_name = models.CharField(max_length=100, blank=True, verbose_name="Last Name")
    father_name = models.CharField(max_length=200, blank=True, verbose_name="Father's Name")

    phone_number = models.CharField(validators=[phone_regex], max_length=17, verbose_name="Phone Number")
    alternate_phone = models.CharField(validators=[phone_regex], max_length=17, blank=True, verbose_name="Alternate Phone")
    email = models.EmailField(blank=True, verbose_name="Email Address")

    date_of_birth = models.DateField(null=True, blank=True, verbose_name="Date of Birth")
    gender = models.CharField(
        max_length=10,
        choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')],
        blank=True,
        verbose_name="Gender"
    )

    address = models.TextField(blank=True, verbose_name="Address")
    city = models.CharField(max_length=100, blank=True, verbose_name="City")

    employee_type = models.CharField(max_length=20, choices=EMPLOYEE_TYPE_CHOICES, verbose_name="Employee Type")

    qualification = models.CharField(max_length=200, blank=True, verbose_name="Qualification")
    experience_years = models.PositiveIntegerField(default=0, verbose_name="Years of Experience")

    employee_code = models.CharField(max_length=50, unique=True, verbose_name="Employee Code")
    joining_date = models.DateField(default=timezone.now, verbose_name="Joining Date")
    salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Salary")

    branch = models.ForeignKey('tenants.Branch', on_delete=models.CASCADE, related_name='employees', verbose_name="Branch")
    school = models.ForeignKey('tenants.SchoolTenant', on_delete=models.CASCADE, related_name='employees', verbose_name="School")

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='employee_profile', null=True, blank=True
    )

    profile_picture = models.ImageField(upload_to='employee_profiles/', null=True, blank=True, verbose_name="Profile Picture")

    is_active = models.BooleanField(default=True, verbose_name="Is Active")
    cnic = models.CharField(max_length=15, blank=True, verbose_name="CNIC Number", help_text="Format: 12345-1234567-1")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_employees')

    class Meta:
        verbose_name = "Employee"
        verbose_name_plural = "Employees"
        ordering = ['first_name', 'last_name']
        indexes = [
            models.Index(fields=['employee_id']),
            models.Index(fields=['employee_type']),
            models.Index(fields=['branch', 'is_active']),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.get_employee_type_display()})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def save(self, *args, **kwargs):
        if not self.employee_id:
            year = timezone.now().strftime('%y')
            branch_code = self.branch.code[:3].upper() if self.branch.code else 'EMP'
            type_code = self.employee_type[:2].upper()
            last_emp = Employee.objects.filter(
                employee_id__startswith=f"{branch_code}{type_code}"
            ).order_by('-employee_id').first()
            new_num = (int(last_emp.employee_id[-4:]) + 1) if last_emp else 1
            self.employee_id = f"{branch_code}{type_code}{year}{new_num:04d}"

        if not self.employee_code:
            self.employee_code = f"EMP-{self.employee_id}"

        super().save(*args, **kwargs)


class Teacher(models.Model):
    """
    Teacher Model - Extends CustomUser with teacher-specific fields.
    Linked to subjects and optionally a section as incharge.
    """

    specialization = models.CharField(max_length=200, blank=True, verbose_name="Specialization")
    qualification = models.CharField(max_length=200, blank=True, verbose_name="Qualification")
    experience_years = models.PositiveIntegerField(default=0, verbose_name="Years of Experience")

    employee_code = models.CharField(max_length=50, unique=True, verbose_name="Employee Code")
    joining_date = models.DateField(default=timezone.now, verbose_name="Joining Date")
    salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Salary")

    branch = models.ForeignKey('tenants.Branch', on_delete=models.CASCADE, related_name='teachers', verbose_name="Branch")
    school = models.ForeignKey('tenants.SchoolTenant', on_delete=models.CASCADE, related_name='teachers', verbose_name="School")

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='teacher_profile')

    subjects = models.ManyToManyField(
        'academics.Subject', blank=True, related_name='teachers',
        verbose_name="Subjects", help_text="Subjects this teacher teaches"
    )

    incharge_section = models.ForeignKey(
        'academics.Section', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='incharge_teacher',
        verbose_name="Incharge of Section",
        help_text="Section this teacher is incharge of (optional)"
    )

    is_active = models.BooleanField(default=True, verbose_name="Is Active")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_teachers')

    class Meta:
        verbose_name = "Teacher"
        verbose_name_plural = "Teachers"
        ordering = ['user__full_name']

    def __str__(self):
        return f"{self.user.get_full_name()} - Teacher"

    @property
    def full_name(self):
        return self.user.get_full_name()

    def save(self, *args, **kwargs):
        if not self.employee_code:
            branch_code = self.branch.code[:3].upper() if self.branch.code else 'TCH'
            year = timezone.now().strftime('%y')
            last_teacher = Teacher.objects.filter(
                employee_code__startswith=f"{branch_code}TCH"
            ).order_by('-employee_code').first()
            new_num = (int(last_teacher.employee_code[-4:]) + 1) if last_teacher else 1
            self.employee_code = f"{branch_code}TCH{year}{new_num:04d}"
        super().save(*args, **kwargs)


class Accountant(models.Model):
    """
    Accountant Model - Extends CustomUser with accountant-specific fields.
    """

    qualification = models.CharField(max_length=200, blank=True, verbose_name="Qualification")
    certification = models.CharField(max_length=200, blank=True, verbose_name="Certification")
    experience_years = models.PositiveIntegerField(default=0, verbose_name="Years of Experience")

    employee_code = models.CharField(max_length=50, unique=True, verbose_name="Employee Code")
    joining_date = models.DateField(default=timezone.now, verbose_name="Joining Date")
    salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Salary")

    branch = models.ForeignKey('tenants.Branch', on_delete=models.CASCADE, related_name='accountants', verbose_name="Branch")
    school = models.ForeignKey('tenants.SchoolTenant', on_delete=models.CASCADE, related_name='accountants', verbose_name="School")

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='accountant_profile')

    is_active = models.BooleanField(default=True, verbose_name="Is Active")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_accountants')

    class Meta:
        verbose_name = "Accountant"
        verbose_name_plural = "Accountants"
        ordering = ['user__full_name']

    def __str__(self):
        return f"{self.user.get_full_name()} - Accountant"

    @property
    def full_name(self):
        return self.user.get_full_name()

    def save(self, *args, **kwargs):
        if not self.employee_code:
            branch_code = self.branch.code[:3].upper() if self.branch.code else 'ACC'
            year = timezone.now().strftime('%y')
            last_acc = Accountant.objects.filter(
                employee_code__startswith=f"{branch_code}ACC"
            ).order_by('-employee_code').first()
            new_num = (int(last_acc.employee_code[-4:]) + 1) if last_acc else 1
            self.employee_code = f"{branch_code}ACC{year}{new_num:04d}"
        super().save(*args, **kwargs)
