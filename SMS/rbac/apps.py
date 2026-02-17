from django.apps import AppConfig


class RbacConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'rbac'
    verbose_name = 'Role-Based Access Control'

    def ready(self):
        # Importing signals here ensures they are connected when Django starts.
        # Without this, the post_save signal in signals.py is never registered.
        # (Error #9)
        import rbac.signals  # noqa: F401