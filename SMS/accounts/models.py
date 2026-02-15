from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from django.core.validators import RegexValidator
import os

class CustomUserManager(BaseUserManager):
    """
    Custom manager for CustomUser model.
    Handles user creation with email as the unique identifier.
    """
    
    def create_user(self, email, password=None, **extra_fields):
        """
        Create and save a regular user with the given email and password.
        """
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """
        Create and save a superuser with the given email and password.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('payment_verified', True)  # Superusers are auto-verified
        extra_fields.setdefault('user_type', 'principal')
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    """
    Custom User Model for the School Management System.
    
    This model extends Django's AbstractBaseUser to provide:
    - Email as the unique identifier for authentication
    - Phone number with validation
    - User type selection (principal, manager, teacher, etc.)
    - Account activation status (for payment verification)
    - Terms and conditions acceptance tracking
    """
    
    # User type choices for role-based access
    USER_TYPE_CHOICES = [
        ('principal', 'Principal'),
        ('manager', 'Manager'),
        ('accountant', 'Accountant'),
        ('teacher', 'Teacher'),
        ('employee', 'Employee'),
        ('parent', 'Parent'),
        ('student', 'Student'),
    ]
    
    # Phone number validation
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in format: '+999999999'. Up to 15 digits allowed."
    )
    
    # Basic Information
    email = models.EmailField(unique=True, db_index=True)
    phone_number = models.CharField(validators=[phone_regex], max_length=17, blank=True)
    full_name = models.CharField(max_length=255)
    city = models.CharField(max_length=100, blank=True)
    
    # User Type and Status
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default='principal')
    is_active = models.BooleanField(default=False)  # False until payment verified
    is_staff = models.BooleanField(default=False)
    
    # Terms and Conditions
    accepted_terms = models.BooleanField(default=False)
    accepted_policies = models.BooleanField(default=False)
    terms_accepted_at = models.DateTimeField(null=True, blank=True)
    
    # Payment Verification
    payment_verified = models.BooleanField(default=False)
    payment_screenshot = models.ImageField(upload_to='payment_screenshots/', null=True, blank=True)
    payment_submitted_at = models.DateTimeField(null=True, blank=True)
    transaction_id = models.CharField(max_length=100, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login = models.DateTimeField(null=True, blank=True)
    
    # Django required fields
    date_joined = models.DateTimeField(default=timezone.now)
    
    objects = CustomUserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name']
    
    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['user_type']),
            models.Index(fields=['is_active']),
            models.Index(fields=['payment_verified']),
        ]
        
    def __str__(self):
        return f"{self.full_name} ({self.email})"
    
    def get_full_name(self):
        """Return the full name of the user."""
        return self.full_name
    
    def get_short_name(self):
        """Return the short name (first word of full name)."""
        return self.full_name.split()[0] if self.full_name else self.email
    
    def has_verified_payment(self):
        """Check if user has submitted payment for verification."""
        return self.payment_verified
    
    def can_login(self):
        """Check if user can login (active and payment verified)."""
        return self.is_active and self.payment_verified
    
    def accept_terms(self):
        """Method to accept terms and conditions."""
        self.accepted_terms = True
        self.terms_accepted_at = timezone.now()
        self.save(update_fields=['accepted_terms', 'terms_accepted_at'])





class UserActivity(models.Model):
    """
    Model to track user activities
    """
    ACTIVITY_TYPES = [
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('profile_update', 'Profile Update'),
        ('password_change', 'Password Change'),
        ('payment_upload', 'Payment Upload'),
        ('payment_verified', 'Payment Verified'),
        ('terms_accepted', 'Terms Accepted'),
        ('view_report', 'View Report'),
        ('export_data', 'Export Data'),
    ]
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=50, choices=ACTIVITY_TYPES)
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(default=timezone.now)
    data = models.JSONField(null=True, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = 'User activities'
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['activity_type']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.activity_type} - {self.timestamp}"