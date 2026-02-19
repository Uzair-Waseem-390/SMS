from django.db import models
from django.conf import settings
from django.utils import timezone


TEMPLATE_TYPE_CHOICES = [
    ('character', 'Character Certificate'),
    ('bonafide', 'Bonafide Certificate'),
    ('fee_clearance', 'Fee Clearance Certificate'),
    ('result', 'Result Certificate'),
    ('leaving', 'Leaving Certificate'),
    ('experience', 'Experience Certificate (Employee)'),
]


class CertificateTemplate(models.Model):
    """HTML template for certificate generation with placeholders."""

    branch = models.ForeignKey(
        'tenants.Branch',
        on_delete=models.CASCADE,
        related_name='certificate_templates',
        verbose_name="Branch",
    )
    school = models.ForeignKey(
        'tenants.SchoolTenant',
        on_delete=models.CASCADE,
        related_name='certificate_templates',
        verbose_name="School",
    )

    name = models.CharField(max_length=255, verbose_name="Template Name")
    template_type = models.CharField(
        max_length=30,
        choices=TEMPLATE_TYPE_CHOICES,
        verbose_name="Certificate Type",
    )
    body_template = models.TextField(
        verbose_name="Body Template (HTML)",
        help_text="Use placeholders: {{student_name}}, {{class}}, {{section}}, {{admission_number}}, "
                  "{{father_name}}, {{date}}, {{school_name}}, {{branch_name}}, etc. "
                  "For experience: {{employee_name}}, {{designation}}, {{joining_date}}, {{leaving_date}}, etc.",
    )
    is_active = models.BooleanField(default=True, verbose_name="Is Active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Certificate Template"
        verbose_name_plural = "Certificate Templates"
        ordering = ['template_type', 'name']
        unique_together = ['branch', 'name']

    def __str__(self):
        return f"{self.name} ({self.get_template_type_display()})"


class Certificate(models.Model):
    """Issued certificate - immutable after generation."""

    # Recipient: either student or employee (user)
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='certificates',
        verbose_name="Student",
    )
    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='issued_certificates',
        verbose_name="Employee (for experience cert)",
    )

    template = models.ForeignKey(
        CertificateTemplate,
        on_delete=models.PROTECT,
        related_name='certificates',
        verbose_name="Template",
    )
    branch = models.ForeignKey(
        'tenants.Branch',
        on_delete=models.CASCADE,
        related_name='certificates',
        verbose_name="Branch",
    )
    school = models.ForeignKey(
        'tenants.SchoolTenant',
        on_delete=models.CASCADE,
        related_name='certificates',
        verbose_name="School",
    )

    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='certificates_issued',
        verbose_name="Issued By",
    )
    issued_date = models.DateField(default=timezone.now, verbose_name="Issue Date")
    serial_number = models.CharField(max_length=50, unique=True, verbose_name="Serial Number")
    generated_pdf = models.FileField(
        upload_to='certificates/%Y/%m/',
        null=True,
        blank=True,
        verbose_name="Generated PDF",
    )

    # Snapshot of rendered content (for display if PDF missing)
    custom_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Certificate Data",
        help_text="Stored placeholder values used for this certificate",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Certificate"
        verbose_name_plural = "Certificates"
        ordering = ['-issued_date', '-created_at']
        indexes = [
            models.Index(fields=['branch', 'issued_date']),
            models.Index(fields=['serial_number']),
        ]

    def __str__(self):
        if self.student:
            return f"{self.get_template_display()} - {self.student.full_name} ({self.serial_number})"
        return f"{self.get_template_display()} - {self.employee.full_name if self.employee else 'N/A'} ({self.serial_number})"

    @property
    def get_template_display(self):
        return self.template.get_template_type_display()

    @property
    def recipient_name(self):
        if self.student:
            return self.student.full_name
        return self.employee.full_name if self.employee else ""
