from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

from .models import Role, UserRole
from .services import rbac_service

User = get_user_model()


@receiver(post_save, sender=User)
def assign_default_role(sender, instance, created, **kwargs):
    """
    Auto-assign default role to a newly created user based on their user_type.
    Runs after every User save; only acts when the record is brand-new.
    """
    if not created:
        return

    if not instance.user_type:
        return

    # Resolve the tenant from the user (custom user models typically carry this)
    tenant = getattr(instance, 'tenant', None)

    try:
        role = Role.objects.get(name=instance.user_type, tenant=tenant)
        rbac_service.assign_role(
            user=instance,
            role=role,
            assigned_by=None,   # system-level assignment
        )
    except Role.DoesNotExist:
        # Role not seeded yet for this tenant — skip silently
        pass