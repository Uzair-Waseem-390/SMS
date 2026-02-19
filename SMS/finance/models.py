from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal


FREQUENCY_CHOICES = [
    ('monthly', 'Monthly'),
    ('yearly', 'Yearly'),
]

FEE_STATUS_CHOICES = [
    ('unpaid', 'Unpaid'),
    ('partial', 'Partially Paid'),
    ('paid', 'Paid'),
]

FEE_TYPE_CHOICES = [
    ('academic', 'Academic Fee'),
    ('special', 'Special Fee'),
]

SCHOLARSHIP_TYPE_CHOICES = [
    ('percentage', 'Percentage'),
    ('fixed', 'Fixed Amount'),
]

EXPENSE_CATEGORY_CHOICES = [
    ('rent', 'Rent'),
    ('electricity', 'Electricity'),
    ('water', 'Water'),
    ('internet', 'Internet'),
    ('maintenance', 'Maintenance'),
    ('supplies', 'Supplies / Stationery'),
    ('transport', 'Transport'),
    ('furniture', 'Furniture'),
    ('events', 'Events'),
    ('other', 'Other'),
]

SALARY_STATUS_CHOICES = [
    ('unpaid', 'Unpaid'),
    ('paid', 'Paid'),
]


class BranchFeeStructure(models.Model):
    """
    Defines the fee structure for a branch.
    One active fee structure per branch at a time.
    """

    branch = models.ForeignKey(
        'tenants.Branch', on_delete=models.CASCADE,
        related_name='fee_structures', verbose_name="Branch"
    )
    school = models.ForeignKey(
        'tenants.SchoolTenant', on_delete=models.CASCADE,
        related_name='fee_structures', verbose_name="School"
    )

    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES, verbose_name="Fee Frequency")

    monthly_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        verbose_name="Monthly Fee (PKR)",
        help_text="Required if frequency is monthly"
    )

    yearly_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        verbose_name="Yearly Fee (PKR)",
        help_text="Required if frequency is yearly"
    )
    yearly_installments = models.PositiveIntegerField(
        null=True, blank=True, verbose_name="No. of Installments per Year",
        help_text="Required if frequency is yearly"
    )
    installment_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        verbose_name="Each Installment Amount (PKR)",
        help_text="Auto-calculated: yearly_amount / yearly_installments"
    )

    is_active = models.BooleanField(default=True, verbose_name="Is Active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Branch Fee Structure"
        verbose_name_plural = "Branch Fee Structures"
        ordering = ['-created_at']

    def __str__(self):
        if self.frequency == 'monthly':
            return f"{self.branch.name} - Monthly: PKR {self.monthly_amount}"
        return f"{self.branch.name} - Yearly: PKR {self.yearly_amount} ({self.yearly_installments} installments)"

    def save(self, *args, **kwargs):
        if self.frequency == 'yearly' and self.yearly_amount and self.yearly_installments:
            self.installment_amount = (self.yearly_amount / Decimal(self.yearly_installments)).quantize(Decimal('0.01'))
        if self.is_active:
            BranchFeeStructure.objects.filter(
                branch=self.branch, is_active=True
            ).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

    @property
    def per_fee_amount(self):
        """The amount charged per fee generation."""
        if self.frequency == 'monthly':
            return self.monthly_amount or Decimal('0')
        return self.installment_amount or Decimal('0')


class Scholarship(models.Model):
    """Scholarship that can be assigned to students to reduce their fees."""

    name = models.CharField(max_length=255, verbose_name="Scholarship Name")
    description = models.TextField(blank=True, verbose_name="Description")

    scholarship_type = models.CharField(
        max_length=15, choices=SCHOLARSHIP_TYPE_CHOICES,
        verbose_name="Scholarship Type"
    )

    percentage_amount = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        verbose_name="Percentage (%)",
        help_text="Required if type is percentage (e.g. 25 for 25%)"
    )
    fixed_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        verbose_name="Fixed Amount (PKR)",
        help_text="Required if type is fixed"
    )

    start_date = models.DateField(verbose_name="Start Date")
    end_date = models.DateField(null=True, blank=True, verbose_name="End Date")

    branch = models.ForeignKey(
        'tenants.Branch', on_delete=models.CASCADE,
        related_name='scholarships', verbose_name="Branch"
    )
    school = models.ForeignKey(
        'tenants.SchoolTenant', on_delete=models.CASCADE,
        related_name='scholarships', verbose_name="School"
    )

    is_active = models.BooleanField(default=True, verbose_name="Is Active")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='created_scholarships'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Scholarship"
        verbose_name_plural = "Scholarships"
        ordering = ['-created_at']

    def __str__(self):
        if self.scholarship_type == 'percentage':
            return f"{self.name} ({self.percentage_amount}%)"
        return f"{self.name} (PKR {self.fixed_amount})"

    def calculate_deduction(self, fee_amount):
        """
        Calculate scholarship deduction for a given fee amount.
        For percentage: fee_amount * percentage / 100
        For fixed: the fixed amount directly (capped at fee_amount)
        """
        if self.scholarship_type == 'percentage' and self.percentage_amount:
            return (fee_amount * self.percentage_amount / Decimal('100')).quantize(Decimal('0.01'))
        elif self.scholarship_type == 'fixed' and self.fixed_amount:
            return min(self.fixed_amount, fee_amount)
        return Decimal('0')


class StudentFee(models.Model):
    """A single generated fee instance for a student."""

    fee_type = models.CharField(
        max_length=10, choices=FEE_TYPE_CHOICES, default='academic',
        verbose_name="Fee Type"
    )

    student = models.ForeignKey(
        'students.Student', on_delete=models.CASCADE,
        related_name='fees', verbose_name="Student"
    )
    fee_structure = models.ForeignKey(
        BranchFeeStructure, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='student_fees', verbose_name="Fee Structure"
    )

    branch = models.ForeignKey(
        'tenants.Branch', on_delete=models.CASCADE,
        related_name='student_fees', verbose_name="Branch"
    )
    school = models.ForeignKey(
        'tenants.SchoolTenant', on_delete=models.CASCADE,
        related_name='student_fees', verbose_name="School"
    )

    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Original Amount (PKR)")
    scholarship_deduction = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name="Scholarship Deduction (PKR)"
    )
    net_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Net Amount (PKR)")
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Amount Paid (PKR)")

    status = models.CharField(max_length=10, choices=FEE_STATUS_CHOICES, default='unpaid', verbose_name="Status")

    due_date = models.DateField(verbose_name="Due Date")
    paid_date = models.DateField(null=True, blank=True, verbose_name="Paid Date")

    installment_number = models.PositiveIntegerField(
        null=True, blank=True, verbose_name="Installment #",
        help_text="For yearly fee structures"
    )

    label = models.CharField(max_length=255, blank=True, verbose_name="Fee Label",
                             help_text="e.g. 'January 2026' or 'Installment 2 of 3'")

    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='fees_received', verbose_name="Received By"
    )
    received_by_role = models.CharField(max_length=30, blank=True, verbose_name="Receiver Role")

    notes = models.TextField(blank=True, verbose_name="Notes")
    is_active = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='fees_created', verbose_name="Generated By"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Student Fee"
        verbose_name_plural = "Student Fees"
        ordering = ['-due_date', 'student__first_name']
        indexes = [
            models.Index(fields=['student', 'status']),
            models.Index(fields=['branch', 'status']),
            models.Index(fields=['due_date']),
        ]

    def __str__(self):
        return f"{self.student} - {self.label or self.due_date} - {self.get_status_display()}"

    @property
    def balance(self):
        return self.net_amount - self.amount_paid

    def record_payment(self, amount, received_by=None):
        """Record a payment towards this fee."""
        self.amount_paid += Decimal(str(amount))
        if self.amount_paid >= self.net_amount:
            self.amount_paid = self.net_amount
            self.status = 'paid'
            self.paid_date = timezone.now().date()
        else:
            self.status = 'partial'
        if received_by:
            self.received_by = received_by
            self.received_by_role = received_by.get_user_type_display()
        self.save()


class Expense(models.Model):
    """Tracks branch expenses (rent, utilities, supplies, etc.). Salary is handled separately."""

    branch = models.ForeignKey(
        'tenants.Branch', on_delete=models.CASCADE,
        related_name='expenses', verbose_name="Branch"
    )
    school = models.ForeignKey(
        'tenants.SchoolTenant', on_delete=models.CASCADE,
        related_name='expenses', verbose_name="School"
    )

    title = models.CharField(max_length=255, verbose_name="Expense Title")
    category = models.CharField(max_length=30, choices=EXPENSE_CATEGORY_CHOICES, verbose_name="Category")
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Amount (PKR)")
    description = models.TextField(blank=True, verbose_name="Description")
    expense_date = models.DateField(default=timezone.now, verbose_name="Expense Date")

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='created_expenses'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Expense"
        verbose_name_plural = "Expenses"
        ordering = ['-expense_date', '-created_at']
        indexes = [
            models.Index(fields=['branch', 'expense_date']),
            models.Index(fields=['category']),
        ]

    def __str__(self):
        return f"{self.title} - PKR {self.amount} ({self.get_category_display()})"


class SalaryRecord(models.Model):
    """
    Monthly salary record for each employee.
    Generated per month/year per employee, then marked as paid when disbursed.
    """

    branch = models.ForeignKey(
        'tenants.Branch', on_delete=models.CASCADE,
        related_name='salary_records', verbose_name="Branch"
    )
    school = models.ForeignKey(
        'tenants.SchoolTenant', on_delete=models.CASCADE,
        related_name='salary_records', verbose_name="School"
    )

    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='salary_records', verbose_name="Employee"
    )

    employee_type = models.CharField(max_length=30, blank=True, verbose_name="Employee Type")
    salary_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Salary Amount (PKR)")

    month = models.PositiveIntegerField(verbose_name="Month (1-12)")
    year = models.PositiveIntegerField(verbose_name="Year")

    status = models.CharField(max_length=10, choices=SALARY_STATUS_CHOICES, default='unpaid', verbose_name="Status")
    description = models.TextField(blank=True, verbose_name="Notes / Description")

    payment_date = models.DateField(null=True, blank=True, verbose_name="Payment Date")
    paid_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='salaries_paid', verbose_name="Paid By"
    )
    paid_by_role = models.CharField(max_length=30, blank=True, verbose_name="Paid By Role")

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='salaries_created', verbose_name="Created By"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Salary Record"
        verbose_name_plural = "Salary Records"
        ordering = ['-year', '-month', 'employee__full_name']
        unique_together = ['employee', 'month', 'year']
        indexes = [
            models.Index(fields=['branch', 'month', 'year']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.employee.full_name} - {self.get_month_display()} {self.year} - {self.get_status_display()}"

    def get_month_display(self):
        import calendar
        return calendar.month_name[self.month]

    @property
    def month_year_label(self):
        import calendar
        return f"{calendar.month_name[self.month]} {self.year}"
