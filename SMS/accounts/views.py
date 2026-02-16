from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.conf import settings
from django.utils import timezone
from accounts.utils import has_school_setup


from .forms import (
    CustomUserCreationForm, 
    CustomAuthenticationForm, 
    PaymentVerificationForm,
    UserProfileForm,
    CustomPasswordChangeForm
)
from .models import CustomUser
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMessage


def register(request):
    """
    User registration view.
    Handles new user registration with terms acceptance.
    After successful registration, redirects to payment verification.
    """
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            # Save user but is_active=False
            user = form.save()
            
            # Store user ID in session for payment verification
            request.session['pending_user_id'] = user.id
            
            messages.success(request, 'Registration successful! Please complete payment verification to activate your account.')
            return redirect('accounts:payment_verification')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'accounts/register.html', {
        'form': form,
        'title': 'Register - School Management System'
    })

def payment_verification(request):
    """
    Payment verification view.
    Users upload payment screenshot and transaction ID.
    Account remains inactive until admin manually verifies payment.
    """
    # Check if user came from registration
    pending_user_id = request.session.get('pending_user_id')
    
    if not pending_user_id:
        messages.warning(request, 'Please register first before payment verification.')
        return redirect('accounts:register')
    
    try:
        user = CustomUser.objects.get(id=pending_user_id)
    except CustomUser.DoesNotExist:
        messages.error(request, 'User not found. Please register again.')
        return redirect('accounts:register')
    
    if request.method == 'POST':
        form = PaymentVerificationForm(request.POST, request.FILES)
        if form.is_valid():
            # Save payment details
            user.transaction_id = form.cleaned_data['transaction_id']
            user.payment_screenshot = form.cleaned_data['payment_screenshot']
            user.payment_submitted_at = timezone.now()
            user.save()
            
            # Clear session
            del request.session['pending_user_id']
            
            messages.success(
                request, 
                'Payment proof submitted successfully! '
                'Your account will be activated within 24 hours after manual verification. '
                'You will receive a confirmation on WhatsApp.'
            )
            return redirect('accounts:login')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PaymentVerificationForm()
    
    return render(request, 'accounts/payment_verification.html', {
        'form': form,
        'user': user,
        'title': 'Payment Verification'
    })

def login_view(request):
    """
    User login view.
    Checks if user is active and payment verified before allowing login.
    """
    if request.user.is_authenticated:
        # return redirect('accounts:test_page')
        if not has_school_setup(request.user):
            return redirect('tenants:setup_wizard')
        return redirect('tenants:test_page')
    
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=email, password=password)
            
            if user is not None:
                if user.can_login():
                    login(request, user)
                    messages.success(request, f'Welcome back, {user.full_name}!')
                    # return redirect('accounts:test_page')
                    if not has_school_setup(user):
                        return redirect('tenants:setup_wizard')
                    else:
                        return redirect('tenants:test_page')
                elif user.payment_verified and not user.is_active:
                    messages.warning(
                        request, 
                        'Your account is pending activation by admin. '
                        'Please wait for WhatsApp confirmation.'
                    )
                else:
                    messages.warning(
                        request,
                        'Your account is not activated. Please complete payment verification.'
                    )
                    return redirect('accounts:payment_verification')
            else:
                messages.error(request, 'Invalid email or password.')
        else:
            messages.error(request, 'Invalid email or password.')
    else:
        form = CustomAuthenticationForm()
    
    return render(request, 'accounts/login.html', {
        'form': form,
        'title': 'Login - School Management System'
    })

@login_required
def logout_view(request):
    """User logout view."""
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('accounts:login')

@login_required
def profile(request):
    """View user profile."""
    user = CustomUser.objects.get(email=request.user.email)
    context = {
        'user': user,
        'title': 'My Profile'
    }
    return render(request, 'accounts/profile.html', context)

@login_required
def edit_profile(request):
    """Edit user profile information."""
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('accounts:profile')
    else:
        form = UserProfileForm(instance=request.user)
    
    return render(request, 'accounts/edit_profile.html', {
        'form': form,
        'title': 'Edit Profile'
    })

@login_required
def change_password(request):
    """Change user password."""
    if request.method == 'POST':
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Keep user logged in
            messages.success(request, 'Password changed successfully!')
            return redirect('accounts:profile')
    else:
        form = CustomPasswordChangeForm(request.user)
    
    return render(request, 'accounts/change_password.html', {
        'form': form,
        'title': 'Change Password'
    })

def terms_and_conditions(request):
    """Display terms and conditions page."""
    return render(request, 'accounts/terms.html', {
        'title': 'Terms and Conditions'
    })

def privacy_policies(request):
    """Display privacy policies page."""
    return render(request, 'accounts/policies.html', {
        'title': 'Privacy Policies'
    })

@login_required
def test_page(request):
    """
    Test page for logged-in users.
    This page confirms successful login and shows user details.
    """
    return render(request, 'accounts/test_page.html', {
        'user': request.user,
        'title': 'Login Successful - Test Page'
    })



def forgotPassword(request):
    if request.method == 'POST':
        email = request.POST['email']
        if CustomUser.objects.filter(email=email).exists():
            user = CustomUser.objects.get(email__exact=email)
            # Reset password email
            current_site = get_current_site(request)
            mail_subject = 'Reset Your Password'
            message = render_to_string('accounts/reset_password_email.html', {
                'user': user,
                'domain': current_site,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': default_token_generator.make_token(user),
            })
            to_email = email
            send_email = EmailMessage(mail_subject, message, to=[to_email])
            send_email.content_subtype = "html"
            send_email.send()
            messages.success(request, 'Password reset email has been sent to your email address.')
            email = email
            context = {
                'email': email,
            }   
            return render(request, 'accounts/mail_sent.html', context)
        else:
            messages.error(request, 'Account does not exist!')
            return redirect('accounts:forgotPassword')
    return render(request, 'accounts/forgotPassword.html')


def resetPassword(request):
    if request.method == 'POST':
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']

        if password == confirm_password:
            uid = request.session.get('uid')
            user = CustomUser.objects.get(pk=uid)
            user.set_password(password)
            user.save()
            messages.success(request, 'Password reset successful')
            return redirect('accounts:login')
        else:
            messages.error(request, 'Password do not match!')
            return redirect('accounts:resetPassword')
    else:
        return render(request, 'accounts/resetPassword.html')
    

def resetpassword_validate(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = CustomUser._default_manager.get(pk=uid)
    except(TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        user = None
    if user is not None and default_token_generator.check_token(user, token):
        request.session['uid'] = uid
        messages.success(request, 'Please reset your password')
        return redirect('accounts:resetPassword')
    else:
        messages.error(request, 'This link has been expired or invalid!')
        return redirect('accounts:login')











# this is for activity log and profile update form
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.core.paginator import Paginator
from django.utils import timezone
from django.db.models import Q

from datetime import datetime, timedelta
from .forms import EditProfileForm, CustomPasswordChangeForm

# Activity Log Model (create this in models.py)
from django.db import models
from .models import UserActivity

@login_required
def profile(request):
    """View user profile."""
    # Log profile view activity
    UserActivity.objects.create(
        user=request.user,
        activity_type='view_report',
        description='Viewed profile',
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )
    
    context = {
        'user': request.user,
        'title': 'My Profile'
    }
    return render(request, 'accounts/profile.html', context)

@login_required
def edit_profile(request):
    """
    Edit user profile information.
    """
    if request.method == 'POST':
        form = EditProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            # Save the form
            user = form.save()
            
            # Log the activity
            UserActivity.objects.create(
                user=request.user,
                activity_type='profile_update',
                description='Updated profile information',
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                data={
                    'updated_fields': list(form.changed_data)
                }
            )
            
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('accounts:profile')
    else:
        form = EditProfileForm(instance=request.user)
    
    context = {
        'form': form,
        'title': 'Edit Profile'
    }
    return render(request, 'accounts/edit_profile.html', context)

@login_required
def change_password(request):
    """
    Change user password.
    """
    if request.method == 'POST':
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            
            # Update session to prevent logout
            update_session_auth_hash(request, user)
            
            # Log the activity
            UserActivity.objects.create(
                user=request.user,
                activity_type='password_change',
                description='Changed password',
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            messages.success(request, 'Your password has been changed successfully!')
            return redirect('accounts:profile')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomPasswordChangeForm(request.user)
    
    context = {
        'form': form,
        'title': 'Change Password'
    }
    return render(request, 'accounts/change_password.html', context)

@login_required
def activity_log(request):
    """
    View user activity log with filtering and pagination.
    """
    # Get activities for the current user
    activities = UserActivity.objects.filter(user=request.user)
    
    # Filter by activity type
    activity_type = request.GET.get('type', '')
    if activity_type:
        activities = activities.filter(activity_type=activity_type)
    
    # Filter by date range
    date_range = request.GET.get('date_range', '')
    today = timezone.now().date()
    
    if date_range == 'today':
        activities = activities.filter(timestamp__date=today)
    elif date_range == 'yesterday':
        yesterday = today - timedelta(days=1)
        activities = activities.filter(timestamp__date=yesterday)
    elif date_range == 'week':
        week_ago = today - timedelta(days=7)
        activities = activities.filter(timestamp__date__gte=week_ago)
    elif date_range == 'month':
        month_ago = today - timedelta(days=30)
        activities = activities.filter(timestamp__date__gte=month_ago)
    
    # Search by description
    search = request.GET.get('search', '')
    if search:
        activities = activities.filter(
            Q(description__icontains=search) |
            Q(activity_type__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(activities, 20)  # Show 20 activities per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Get activity type counts for summary
    activity_summary = UserActivity.objects.filter(
        user=request.user
    ).values('activity_type').annotate(
        count=models.Count('id')
    ).order_by('-count')
    
    # Get login activity for the last 7 days
    last_week = today - timedelta(days=7)
    login_activity = UserActivity.objects.filter(
        user=request.user,
        activity_type='login',
        timestamp__date__gte=last_week
    ).count()
    
    context = {
        'page_obj': page_obj,
        'activities': page_obj,
        'activity_summary': activity_summary,
        'login_activity': login_activity,
        'total_activities': activities.count(),
        'activity_types': UserActivity.ACTIVITY_TYPES,
        'current_filters': {
            'type': activity_type,
            'date_range': date_range,
            'search': search,
            'page': page_number
        },
        'title': 'Activity Log'
    }
    return render(request, 'accounts/activity_log.html', context)

# Helper function to get client IP
def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip