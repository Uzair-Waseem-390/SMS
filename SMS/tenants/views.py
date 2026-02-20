from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model
from django.http import HttpResponseForbidden, HttpResponseRedirect
import random
import string
import re

from .models import SchoolTenant, Branch
from .forms import (
    SchoolSetupStep1Form,
    BranchSetupForm,
    ManagerCredentialsForm,
    BranchManagerForm,
    SchoolEditForm,
    BranchCreateForm,
    BranchUpdateForm,
)
from accounts.utils import has_school_setup
from decimal import Decimal
from functools import wraps

User = get_user_model()


def generate_temp_password(length=10):
    """Generate a temporary password for manager."""
    characters = string.ascii_letters + string.digits + '@#$%'
    return ''.join(random.choice(characters) for i in range(length))


import re

@login_required
def switch_branch(request):
    """
    Sets the active branch in the user's session.
    Redirects back to the referring page, attempting to update the branch ID in the URL.
    """
    branch_id = request.GET.get('branch_id') or request.POST.get('branch_id')
    next_url = request.GET.get('next') or request.META.get('HTTP_REFERER') or '/'

    if branch_id:
        try:
            # Validate that the branch belongs to the user's school
            from tenants.models import Branch
            school = request.user.owned_school if request.user.user_type == 'principal' else (
                request.user.managed_branch.school if request.user.user_type == 'manager' else None
            )

            if school:
                branch = Branch.objects.get(id=int(branch_id), school=school, is_active=True)
                request.session['active_branch_id'] = branch.id
                
                # Attempt to replace branch ID in the URL if it exists
                # Pattern matches: /branch/<old_id>/ or /branch=<old_id>
                # We only want to replace the FIRST occurrence which is usually the route param
                pattern = r'(branch/|branch=)(\d+)'
                
                def replace_branch_id(match):
                    prefix = match.group(1)
                    # Return prefix + new branch id
                    return f"{prefix}{branch.id}"
                
                # If the URL contains a branch ID, swap it
                next_url = re.sub(pattern, replace_branch_id, next_url, count=1)
                
        except (Branch.DoesNotExist, ValueError, AttributeError):
            pass

    return HttpResponseRedirect(next_url)

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
            yearly_amt = form.cleaned_data.get(f'branch_{i}_yearly_amount')
            yearly_inst = form.cleaned_data.get(f'branch_{i}_yearly_installments')
            monthly_amt = form.cleaned_data.get(f'branch_{i}_monthly_amount')
            branch_info = {
                'temp_id': i,
                'name': form.cleaned_data[f'branch_{i}_name'],
                'city': form.cleaned_data[f'branch_{i}_city'],
                'address': form.cleaned_data[f'branch_{i}_address'],
                'phone': form.cleaned_data[f'branch_{i}_phone'],
                'email': form.cleaned_data[f'branch_{i}_email'],
                'fee_frequency': form.cleaned_data.get(f'branch_{i}_fee_frequency', 'monthly'),
                'monthly_amount': str(monthly_amt) if monthly_amt else None,
                'yearly_amount': str(yearly_amt) if yearly_amt else None,
                'yearly_installments': yearly_inst,
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
                
                manager_salary = form.cleaned_data.get(f'manager_salary_{form_id}') or Decimal('0')

                # Create branch
                branch = Branch.objects.create(
                    name=branch_info['name'],
                    school=school,
                    city=branch_info['city'],
                    address=branch_info['address'],
                    phone=branch_info.get('phone', ''),
                    email=branch_info.get('email', ''),
                    manager=manager_user,
                    manager_salary=manager_salary,
                    manager_temp_email=manager_email,
                    manager_temp_password=manager_password,
                    is_main_branch=(i == 0)  # First branch is main branch
                )

                # Create fee structure for this branch
                from finance.models import BranchFeeStructure
                freq = branch_info.get('fee_frequency', 'monthly')
                fee_kwargs = {
                    'branch': branch, 'school': school,
                    'frequency': freq, 'is_active': True,
                }
                if freq == 'monthly':
                    fee_kwargs['monthly_amount'] = Decimal(branch_info['monthly_amount']) if branch_info.get('monthly_amount') else None
                else:
                    fee_kwargs['yearly_amount'] = Decimal(branch_info['yearly_amount']) if branch_info.get('yearly_amount') else None
                    fee_kwargs['yearly_installments'] = branch_info.get('yearly_installments')
                BranchFeeStructure.objects.create(**fee_kwargs)
            

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
            branch = school.branches.filter(is_main_branch=True).first() or school.branches.first()
            if branch:
                return redirect('dashboard:index', school_id=school.id, branch_id=branch.id)
            return redirect('dashboard:index')
            
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


# ─── Principal-only access decorator ───────────────────────────────────────────

def principal_required(view_func):
    """Decorator: allows only users with user_type == 'principal'."""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.user_type != 'principal':
            return HttpResponseForbidden(
                "<h2>403 – Access Denied</h2><p>Only principals can access this page.</p>"
            )
        return view_func(request, *args, **kwargs)
    return wrapper


# ─── School CRUD ───────────────────────────────────────────────────────────────

@principal_required
def school_detail(request):
    """View the principal's own school details."""
    try:
        school = request.user.owned_school
        max_branches = school.branches.all().count()
    except SchoolTenant.DoesNotExist:
        messages.warning(request, 'You have not set up a school yet.')
        return redirect('tenants:setup_wizard')

    branches = school.branches.all().select_related('manager').order_by('-is_main_branch', 'name')
    return render(request, 'tenants/school_detail.html', {
        'school': school,
        'branches': branches,
        'title': f'{school.name} – School Details',
    })


@principal_required
def school_update(request):
    """Edit the principal's school information."""
    try:
        school = request.user.owned_school
    except SchoolTenant.DoesNotExist:
        messages.warning(request, 'You have not set up a school yet.')
        return redirect('tenants:setup_wizard')

    if request.method == 'POST':
        form = SchoolEditForm(request.POST, instance=school)
        if form.is_valid():
            form.save()
            messages.success(request, 'School information updated successfully.')
            return redirect('tenants:school_detail')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = SchoolEditForm(instance=school)

    return render(request, 'tenants/school_form.html', {
        'form': form,
        'school': school,
        'title': 'Edit School Information',
    })


# ─── Branch CRUD ───────────────────────────────────────────────────────────────

@principal_required
def branch_list(request):
    """List all branches belonging to the principal's school."""
    try:
        school = request.user.owned_school
    except SchoolTenant.DoesNotExist:
        messages.warning(request, 'You have not set up a school yet.')
        return redirect('tenants:setup_wizard')

    branches = school.branches.all().select_related('manager').order_by('-is_main_branch', 'name')
    return render(request, 'tenants/branch_list.html', {
        'school': school,
        'branches': branches,
        'title': 'Manage Branches',
    })


@principal_required
@transaction.atomic
def branch_create(request):
    """Create a new branch and auto-create a manager user account."""
    try:
        school = request.user.owned_school
    except SchoolTenant.DoesNotExist:
        messages.warning(request, 'You have not set up a school yet.')
        return redirect('tenants:setup_wizard')

    if not school.can_add_branch():
        messages.error(
            request,
            f'You have reached the maximum number of branches ({school.max_branches}). '
            f'Please contact support to increase your limit.'
        )
        return redirect('tenants:branch_list')

    if request.method == 'POST':
        form = BranchCreateForm(request.POST)
        if form.is_valid():
            try:
                # Create manager user
                manager_email = form.cleaned_data['manager_email']
                manager_password = form.cleaned_data['manager_password']

                if User.objects.filter(email=manager_email).exists():
                    form.add_error('manager_email', 'A user with this email already exists.')
                    raise ValueError('duplicate email')

                manager_user = User.objects.create_user(
                    email=manager_email,
                    password=manager_password,
                    full_name=f"Manager - {form.cleaned_data['name']}",
                    user_type='manager',
                    is_active=True,
                    payment_verified=True,
                )

                # Create branch
                branch = form.save(commit=False)
                branch.school = school
                branch.manager = manager_user
                branch.manager_salary = form.cleaned_data.get('manager_salary') or Decimal('0')
                branch.manager_temp_email = manager_email
                branch.manager_temp_password = manager_password
                branch.save()

                messages.success(
                    request,
                    f'Branch "{branch.name}" created successfully. '
                    f'Manager credentials: {manager_email} / {manager_password}'
                )
                return redirect('tenants:branch_list')

            except ValueError:
                pass  # form errors already added
            except Exception as e:
                messages.error(request, f'Error creating branch: {str(e)}')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = BranchCreateForm()

    return render(request, 'tenants/branch_form.html', {
        'form': form,
        'school': school,
        'title': 'Create New Branch',
        'action': 'create',
    })


@principal_required
def branch_update(request, branch_id):
    """Edit an existing branch and optionally update manager credentials."""
    try:
        school = request.user.owned_school
    except SchoolTenant.DoesNotExist:
        return HttpResponseForbidden('No school found.')

    branch = get_object_or_404(Branch, id=branch_id, school=school)

    if request.method == 'POST':
        form = BranchUpdateForm(request.POST, instance=branch)
        if form.is_valid():
            branch = form.save(commit=False)
            branch.save()

            # Update manager email
            if branch.manager:
                new_email = form.cleaned_data.get('manager_email')
                new_name = form.cleaned_data.get('manager_name')
                new_pass = form.cleaned_data.get('new_password')

                if new_email and branch.manager.email != new_email:
                    branch.manager.email = new_email
                if new_name:
                    branch.manager.full_name = new_name
                if new_pass:
                    branch.manager.set_password(new_pass)
                    messages.info(request, 'Manager password has been updated.')
                branch.manager.save()

            messages.success(request, f'Branch "{branch.name}" updated successfully.')
            return redirect('tenants:branch_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        initial = {}
        if branch.manager:
            initial['manager_email'] = branch.manager.email
            initial['manager_name'] = branch.manager.full_name
        form = BranchUpdateForm(instance=branch, initial=initial)

    return render(request, 'tenants/branch_form.html', {
        'form': form,
        'school': school,
        'branch': branch,
        'title': f'Edit Branch: {branch.name}',
        'action': 'update',
    })


@principal_required
def branch_delete(request, branch_id):
    """Soft-delete (deactivate) a branch. Prevents deleting the only active branch."""
    try:
        school = request.user.owned_school
    except SchoolTenant.DoesNotExist:
        return HttpResponseForbidden('No school found.')

    branch = get_object_or_404(Branch, id=branch_id, school=school)

    # Safety check: don't allow deactivating the last active branch
    active_count = school.branches.filter(is_active=True).count()

    if request.method == 'POST':
        if active_count <= 1 and branch.is_active:
            messages.error(request, 'Cannot deactivate the only active branch.')
            return redirect('tenants:branch_list')
        branch.is_active = False
        branch.save()
        messages.success(request, f'Branch "{branch.name}" has been deactivated.')
        return redirect('tenants:branch_list')

    return render(request, 'tenants/branch_confirm_delete.html', {
        'branch': branch,
        'school': school,
        'active_count': active_count,
        'title': f'Deactivate Branch: {branch.name}',
    })