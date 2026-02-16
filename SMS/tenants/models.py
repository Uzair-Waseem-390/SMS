from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import uuid

class SchoolTenant(models.Model):
    """
    School Tenant Model - Represents a school in the multi-tenant system.
    Each school is owned by a principal (user) and can have multiple branches.
    """
    
    # Basic Information
    name = models.CharField(max_length=255, verbose_name="School Name")
    slug = models.SlugField(unique=True, blank=True, help_text="URL identifier (auto-generated)")
    
    # Location Information
    city = models.CharField(max_length=100, verbose_name="City")
    address = models.TextField(verbose_name="Full Address")
    
    # Contact Information
    phone = models.CharField(max_length=20, verbose_name="Contact Phone", blank=True)
    email = models.EmailField(verbose_name="Contact Email", blank=True)
    
    # Ownership - Link to principal (user who created the school)
    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='owned_school',
        verbose_name="School Principal"
    )
    
    # School Details
    established_year = models.IntegerField(
        validators=[MinValueValidator(1900), MaxValueValidator(timezone.now().year)],
        null=True, blank=True,
        verbose_name="Established Year"
    )
    registration_number = models.CharField(max_length=50, blank=True, verbose_name="Registration Number")
    
    # Subscription and Status
    is_active = models.BooleanField(default=True)
    max_branches = models.IntegerField(default=5, help_text="Maximum branches allowed")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "School Tenant"
        verbose_name_plural = "School Tenants"
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.name} - {self.city}"
    
    def save(self, *args, **kwargs):
        """Auto-generate slug from school name if not provided."""
        if not self.slug:
            # Convert name to slug format
            self.slug = self.name.lower().replace(' ', '-').replace('&', 'and')
            # Ensure uniqueness by adding a random suffix if needed
            original_slug = self.slug
            counter = 1
            while SchoolTenant.objects.filter(slug=self.slug).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)
    
    def get_branch_count(self):
        """Return the number of branches for this school."""
        return self.branches.count()
    
    def can_add_branch(self):
        """Check if school can add more branches based on subscription limits."""
        return self.branches.count() < self.max_branches


class Branch(models.Model):
    """
    Branch Model - Represents a branch/campus of a school.
    Each branch belongs to one school tenant and has its own manager.
    """
    
    # Basic Information
    name = models.CharField(max_length=255, verbose_name="Branch Name")
    code = models.CharField(max_length=20, blank=True, verbose_name="Branch Code")
    
    # Relationship to School
    school = models.ForeignKey(
        SchoolTenant, 
        on_delete=models.CASCADE,
        related_name='branches',
        verbose_name="School"
    )
    
    # Location Information
    city = models.CharField(max_length=100, verbose_name="City")
    address = models.TextField(verbose_name="Full Address")
    
    # Contact Information
    phone = models.CharField(max_length=20, verbose_name="Contact Phone")
    email = models.EmailField(verbose_name="Contact Email")
    
    # Branch Management
    manager = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_branch',
        verbose_name="Branch Manager"
    )
    
    # Branch Details
    is_main_branch = models.BooleanField(default=False, help_text="Is this the main branch?")
    is_active = models.BooleanField(default=True)
    
    # Temporary credentials (to be shown to principal)
    manager_temp_email = models.EmailField(blank=True, verbose_name="Manager Temporary Email")
    manager_temp_password = models.CharField(max_length=100, blank=True, verbose_name="Manager Temporary Password")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Branch"
        verbose_name_plural = "Branches"
        ordering = ['school', '-is_main_branch', 'name']
        unique_together = ['school', 'code']  # Ensure unique branch codes per school
        indexes = [
            models.Index(fields=['school', 'is_active']),
            models.Index(fields=['manager']),
        ]
        
    def __str__(self):
        return f"{self.school.name} - {self.name}"
    
    def save(self, *args, **kwargs):
        """Auto-generate branch code if not provided."""
        if not self.code:
            # Generate a simple code from branch name
            base_code = self.name[:3].upper()
            # Add school initials
            school_initials = ''.join(word[0] for word in self.school.name.split()[:2]).upper()
            self.code = f"{school_initials}-{base_code}-{self.school.branches.count() + 1:02d}"
        super().save(*args, **kwargs)