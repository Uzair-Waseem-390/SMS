from django.apps import AppConfig
import logging

# Get logger for this app
logger = logging.getLogger(__name__)

class AccountsConfig(AppConfig):
    """
    Configuration class for the accounts app.
    
    This class configures the accounts application which handles:
    - User registration and authentication
    - Profile management
    - Payment verification for new accounts
    """
    
    # Set the default auto field type for models
    default_auto_field = 'django.db.models.BigAutoField'
    
    # Define the app name (used in Django's app registry)
    name = 'accounts'
    
    # Human-readable verbose name for the app
    verbose_name = 'User Accounts Management'
    
    def ready(self):
        """
        Method called when the application is fully loaded.
        
        This method is used to:
        - Import signals when the app is ready
        - Perform any startup initialization
        - Register any app-specific configurations
        """
        try:
            # Import signals to ensure they are registered
            # This allows signals like post_save to work properly
            import accounts.signals  # noqa
            logger.info("Accounts signals imported successfully")
        except ImportError as e:
            # Log error if signals can't be imported but don't crash the app
            logger.error(f"Failed to import accounts signals: {e}")
        except Exception as e:
            # Catch any other unexpected errors
            logger.error(f"Unexpected error in accounts.ready(): {e}")
        
        # Log that the app is ready
        logger.info(f"{self.verbose_name} app is ready and configured")