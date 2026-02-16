from django.shortcuts import redirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin
from accounts.utils import has_school_setup

class SetupRequiredMiddleware(MiddlewareMixin):
    """
    Middleware to redirect users to setup wizard if they haven't completed school setup.
    """
    
    def process_request(self, request):
        # Skip for unauthenticated users
        if not request.user.is_authenticated:
            return None
        
        # Skip for admin paths
        if request.path.startswith('/admin/'):
            return None
        
        # Skip for setup paths
        if request.path.startswith('/tenants/setup/'):
            return None
        
        # Skip for logout
        if request.path == reverse('accounts:logout'):
            return None
        
        # Check if user needs setup (principals only)
        if request.user.user_type == 'principal' and not has_school_setup(request.user):
            # Only redirect if not already on setup page
            if not request.path.startswith('/tenants/setup/'):
                return redirect('tenants:setup_wizard')
        
        return None