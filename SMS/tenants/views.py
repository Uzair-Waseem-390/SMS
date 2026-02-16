from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model
import random
import string

from .models import SchoolTenant, Branch
from .forms import (
    SchoolSetupStep1Form, 
    BranchSetupForm, 
    ManagerCredentialsForm,
    BranchManagerForm
)
from accounts.utils import has_school_setup

User = get_user_model()

def generate_temp_password(length=10):
    """Generate a temporary password for manager."""
    characters = string.ascii_letters + string.digits + '@#$%'
    return ''.join(random.choice(characters) for i in range(length))

@login_required
def setup_wizard(request):
    """
    Main setup wizard view.
    Checks if user has school setup, if not, guides through 3-step process.
    """
    # Check if user already has school setup
    if has_school_setup(request.user):
        messages.info(request, 'Your school is already set up. Redirecting to test page.')
        return redirect('tenants:test_page')
    
    # Get or initialize session data for wizard
    step = request.session.get('setup_step', 1)
    
    if request.method == 'POST':
        if step == 1:
            return handle_step1(request)
        elif step == 2:
            return handle_step2(request)
        elif step == 3:
            return handle_step3(request)
    
    # GET request - show appropriate step
    if step == 1:
        form = SchoolSetupStep1Form()
        return render(request, 'tenants/setup_step1.html', {
            'form': form,
            'step': 1,
            'title': 'Step 1: School Information'
        })
    elif step == 2:
        # Get branch data from session
        branch_data = request.session.get('branch_data', {})
        num_branches = branch_data.get('num_branches', 1)
        form = BranchSetupForm(num_branches=num_branches)
        return render(request, 'tenants/setup_step2.html', {
            'form': form,
            'step': 2,
            'num_branches': num_branches,
            'school_name': branch_data.get('school_name'),
            'title': 'Step 2: Branch Details'
        })
    elif step == 3:
        # Get branches from session
        branches = request.session.get('branches', [])
        branch_objects = []
        for i, branch_info in enumerate(branches):
            # Create temporary branch objects for form (not saved - use form_id for field names)
            branch = Branch(
                name=branch_info.get('name'),
                city=branch_info.get('city')
            )
            branch.form_id = branch_info.get('temp_id', i + 1)  # Unique ID for form fields
            branch_objects.append(branch)
        
        form = ManagerCredentialsForm(branches=branch_objects)
        return render(request, 'tenants/setup_step3.html', {
            'form': form,
            'step': 3,
            'branches': branch_objects,
            'title': 'Step 3: Manager Credentials'
        })


def handle_step1(request):
    """Handle Step 1 form submission."""
    form = SchoolSetupStep1Form(request.POST)
    if form.is_valid():
        # Store data in session
        request.session['setup_step'] = 2
        request.session['school_data'] = {
            'name': form.cleaned_data['name'],
            'city': form.cleaned_data['city'],
            'address': form.cleaned_data['address'],
            'phone': form.cleaned_data.get('phone', ''),
            'email': form.cleaned_data.get('email', ''),
            'established_year': form.cleaned_data.get('established_year'),
            'registration_number': form.cleaned_data.get('registration_number', ''),
        }
        request.session['branch_data'] = {
            'num_branches': form.cleaned_data['number_of_branches'],
            'school_name': form.cleaned_data['name'],
        }
        messages.success(request, 'School information saved. Now add branch details.')
        return redirect('tenants:setup_wizard')
    else:
        messages.error(request, 'Please correct the errors below.')
        return render(request, 'tenants/setup_step1.html', {
            'form': form,
            'step': 1,
            'title': 'Step 1: School Information'
        })


def handle_step2(request):
    """Handle Step 2 form submission."""
    branch_data = request.session.get('branch_data', {})
    num_branches = branch_data.get('num_branches', 1)
    
    form = BranchSetupForm(request.POST, num_branches=num_branches)
    if form.is_valid():
        # Store branch details in session
        branches = []
        for i in range(1, num_branches + 1):
            branch_info = {
                'temp_id': i,
                'name': form.cleaned_data[f'branch_{i}_name'],
                'city': form.cleaned_data[f'branch_{i}_city'],
                'address': form.cleaned_data[f'branch_{i}_address'],
                'phone': form.cleaned_data[f'branch_{i}_phone'],
                'email': form.cleaned_data[f'branch_{i}_email'],
            }
            branches.append(branch_info)
        
        request.session['setup_step'] = 3
        request.session['branches'] = branches
        messages.success(request, 'Branch details saved. Now set up manager credentials.')
        return redirect('tenants:setup_wizard')
    else:
        messages.error(request, 'Please correct the errors below.')
        return render(request, 'tenants/setup_step2.html', {
            'form': form,
            'step': 2,
            'num_branches': num_branches,
            'school_name': branch_data.get('school_name'),
            'title': 'Step 2: Branch Details'
        })


@transaction.atomic
def handle_step3(request):
    """Handle Step 3 form submission and save everything to database."""
    branches_data = request.session.get('branches', [])
    school_data = request.session.get('school_data', {})
    
    # Create branch objects for validation (assign form_id for field lookup)
    branch_objects = []
    for i, branch_info in enumerate(branches_data):
        branch = Branch(
            name=branch_info.get('name'),
            city=branch_info.get('city')
        )
        branch.form_id = branch_info.get('temp_id', i + 1)  # Unique ID for form fields
        branch_objects.append(branch)
    
    form = ManagerCredentialsForm(request.POST, branches=branch_objects)
    if form.is_valid():
        try:
            # Step 1: Create School Tenant
            school = SchoolTenant.objects.create(
                name=school_data['name'],
                city=school_data['city'],
                address=school_data['address'],
                phone=school_data.get('phone', ''),
                email=school_data.get('email', ''),
                established_year=school_data.get('established_year'),
                registration_number=school_data.get('registration_number', ''),
                owner=request.user,
                max_branches=len(branches_data)  # Set max branches based on actual branches
            )
            
            # Step 2: Create Branches and Managers
            for i, branch_info in enumerate(branches_data):
                branch_obj = branch_objects[i]
                form_id = getattr(branch_obj, 'form_id', i + 1)  # Use form_id for form field lookup
                
                # Get manager credentials from form
                manager_email = form.cleaned_data.get(f'manager_email_{form_id}')
                manager_password = form.cleaned_data.get(f'manager_password_{form_id}')
                
                if not manager_email or not manager_password:
                    raise ValueError(f'Missing manager credentials for branch {branch_info.get("name")}')
                
                # Create manager user (non-principal: active by default, no payment verification)
                manager_user = User.objects.create_user(
                    email=manager_email,
                    password=manager_password,
                    full_name=f"Manager - {branch_info['name']}",
                    phone_number=branch_info.get('phone', ''),
                    city=branch_info.get('city', ''),
                    user_type='manager',
                    is_active=True,  # Non-principals are active by default
                    payment_verified=True,  # Managers don't need payment verification
                )
                
                # Create branch
                branch = Branch.objects.create(
                    name=branch_info['name'],
                    school=school,
                    city=branch_info['city'],
                    address=branch_info['address'],
                    phone=branch_info.get('phone', ''),
                    email=branch_info.get('email', ''),
                    manager=manager_user,
                    manager_temp_email=manager_email,
                    manager_temp_password=manager_password,
                    is_main_branch=(i == 0)  # First branch is main branch
                )
            
            # Clear session data
            request.session.pop('setup_step', None)
            request.session.pop('school_data', None)
            request.session.pop('branch_data', None)
            request.session.pop('branches', None)
            
            messages.success(
                request, 
                f'Congratulations! Your school "{school.name}" has been created successfully. '
                f'You can now log in as manager with the credentials you set.'
            )
            return redirect('tenants:test_page')
            
        except Exception as e:
            messages.error(request, f'An error occurred while saving: {str(e)}')
            return redirect('tenants:setup_wizard')
    else:
        messages.error(request, 'Please correct the errors in manager credentials.')
        return render(request, 'tenants/setup_step3.html', {
            'form': form,
            'step': 3,
            'branches': branch_objects,
            'title': 'Step 3: Manager Credentials'
        })


@login_required
def test_page(request):
    """
    Test page for users who have completed setup.
    This will be replaced with actual dashboard later.
    """
    # Check if user has setup, if not redirect to wizard
    if not has_school_setup(request.user):
        messages.warning(request, 'Please complete your school setup first.')
        return redirect('tenants:setup_wizard')
    
    # Get user's school and branches
    try:
        if request.user.user_type == 'principal':
            school = request.user.owned_school
            branches = school.branches.all()
        elif request.user.user_type == 'manager':
            branch = request.user.managed_branch
            school = branch.school
            branches = school.branches.all()
        else:
            school = None
            branches = None
    except:
        school = None
        branches = None
    
    return render(request, 'tenants/test_page.html', {
        'school': school,
        'branches': branches,
        'user': request.user,
        'title': 'Setup Complete - Test Page'
    })


@login_required
def manage_branch(request, branch_id):
    """
    View for principals to edit branch and manager details.
    """
    branch = get_object_or_404(Branch, id=branch_id, school__owner=request.user)
    
    if request.method == 'POST':
        form = BranchManagerForm(request.POST, instance=branch)
        if form.is_valid():
            branch = form.save(commit=False)
            
            # Update manager email if changed
            manager_email = form.cleaned_data.get('manager_email')
            if manager_email and branch.manager.email != manager_email:
                branch.manager.email = manager_email
                branch.manager.save()
            
            # Update manager password if provided
            new_password = form.cleaned_data.get('manager_password')
            if new_password:
                branch.manager.set_password(new_password)
                branch.manager.save()
                messages.success(request, f'Password updated for manager {branch.manager.email}')
            
            branch.save()
            messages.success(request, f'Branch "{branch.name}" updated successfully.')
            return redirect('tenants:test_page')
    else:
        form = BranchManagerForm(instance=branch, initial={
            'manager_email': branch.manager.email if branch.manager else ''
        })
    
    return render(request, 'tenants/manage_branch.html', {
        'form': form,
        'branch': branch,
        'title': f'Manage Branch: {branch.name}'
    })