from django.db import models
from django.conf import settings
from django.utils import timezone


NOTIFICATION_TYPE_CHOICES = [
    ('general', 'General'),
    ('important', 'Important'),
    ('urgent', 'Urgent'),
    ('other', 'Other'),
]

VISIBILITY_CHOICES = [
    ('public', 'Public (Everyone)'),
    ('staff', 'Staff Only'),
    ('students', 'Students Only'),
    ('parents', 'Parents Only'),
    ('private', 'Private (Staff + Students + Parents)'),
]


class Notification(models.Model):
    """A notification/announcement for the school or a specific branch."""

    title = models.CharField(max_length=255, verbose_name="Title")
    message = models.TextField(verbose_name="Message")
    notification_type = models.CharField(
        max_length=20, choices=NOTIFICATION_TYPE_CHOICES,
        default='general', verbose_name="Type"
    )
    visibility = models.CharField(
        max_length=20, choices=VISIBILITY_CHOICES,
        default='public', verbose_name="Visibility"
    )

    date = models.DateField(verbose_name="Notification Date")
    time = models.TimeField(verbose_name="Notification Time")
    duration_days = models.PositiveIntegerField(
        default=7, verbose_name="Duration (days)",
        help_text="Notification auto-expires after this many days"
    )

    branch = models.ForeignKey(
        'tenants.Branch', on_delete=models.CASCADE,
        related_name='notifications', verbose_name="Branch"
    )
    school = models.ForeignKey(
        'tenants.SchoolTenant', on_delete=models.CASCADE,
        related_name='notifications', verbose_name="School"
    )

    is_active = models.BooleanField(default=True, verbose_name="Is Active")

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='created_notifications'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ['-date', '-time']
        indexes = [
            models.Index(fields=['branch', 'is_active']),
            models.Index(fields=['date']),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_notification_type_display()})"

    @property
    def expires_on(self):
        import datetime
        return self.date + datetime.timedelta(days=self.duration_days)

    @property
    def is_expired(self):
        return timezone.now().date() > self.expires_on

    def visible_to_user(self, user):
        """Check if this notification should be visible to a given user."""
        if not self.is_active or self.is_expired:
            return False
        vis = self.visibility
        if vis == 'public':
            return True
        if vis == 'staff':
            return user.user_type in ('principal', 'manager', 'teacher', 'accountant', 'employee')
        if vis == 'students':
            return user.user_type == 'student'
        if vis == 'parents':
            return user.user_type == 'parent'
        if vis == 'private':
            return user.user_type in ('principal', 'manager', 'teacher', 'accountant', 'employee', 'student', 'parent')
        return False


class Timetable(models.Model):
    """A timetable image uploaded for a branch. Only one can be active per branch."""

    title = models.CharField(max_length=255, verbose_name="Title")
    image = models.ImageField(upload_to='timetables/', verbose_name="Timetable Image")
    description = models.TextField(blank=True, verbose_name="Description")

    branch = models.ForeignKey(
        'tenants.Branch', on_delete=models.CASCADE,
        related_name='timetables', verbose_name="Branch"
    )
    school = models.ForeignKey(
        'tenants.SchoolTenant', on_delete=models.CASCADE,
        related_name='timetables', verbose_name="School"
    )

    is_active = models.BooleanField(default=True, verbose_name="Is Active")

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='created_timetables'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Timetable"
        verbose_name_plural = "Timetables"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.branch.name}"

    def save(self, *args, **kwargs):
        if self.is_active:
            Timetable.objects.filter(
                branch=self.branch, is_active=True
            ).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)
