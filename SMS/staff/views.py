import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from django.db.models import Q
from django.core.exceptions import PermissionDenied

from .models import Employee, Teacher, Accountant
from .forms import (
    StaffCreationStep1Form, StaffCreationStep2Form,
    StaffFilterForm, EmployeeEditForm, TeacherEditForm, AccountantEditForm,
    ChangeCredentialsForm, ProfileEditForm,
    USER_TYPE_MAP,
)
from accounts.utils import get_user_branch, get_user_school, branch_url
from rbac.services import require_principal_or_manager, require_principal_or_manager_or_permission
from rbac.permissions import Permissions
from django.contrib.auth import get_user_model

User = get_user_model()


def _get_dashboard_redirect():
    return redirect('tenants:test_page')


# ─── Create Wizard ───────────────────────────────────────────────

@login_required
@require_principal_or_manager()
def create_staff_wizard(request):
    school = get_user_school(request.user, request)
    branch = get_user_branch(request.user, request)

    if not school or not branch:
        messages.error(request, "No school or branch associated with your account.")
        return _get_dashboard_redirect()

    if request.GET.get('back') == '1':
        request.session['staff_wizard_step'] = 1
        request.session.pop('staff_wizard_data', None)
        return redirect(branch_url(request, 'staff:create_staff_wizard'))

    step = request.session.get('staff_wizard_step', 1)

    if request.method == 'POST':
        if step == 1:
            return _handle_step1(request, school, branch)
        elif step == 2:
            return _handle_step2(request, school, branch)

    if step == 2:
        staff_data = request.session.get('staff_wizard_data', {})
        staff_data['branch_code'] = branch.code if branch else 'SCH'
        form = StaffCreationStep2Form(staff_data=staff_data, branch=branch, request=request)
        return render(request, 'staff/create_step2.html', {
            'form': form, 'step': 2, 'staff_data': staff_data,
            'branch': branch, 'title': 'Create Staff - Step 2',
        })

    form = StaffCreationStep1Form(branch=branch)
    return render(request, 'staff/create_step1.html', {
        'form': form, 'step': 1, 'branch': branch, 'title': 'Create Staff - Step 1',
    })


def _handle_step1(request, school, branch):
    form = StaffCreationStep1Form(request.POST, branch=branch)
    if form.is_valid():
        cd = form.cleaned_data
        dob = cd.get('date_of_birth')
        salary = cd.get('salary')
        request.session['staff_wizard_step'] = 2
        request.session['staff_wizard_data'] = {
            'first_name': cd['first_name'],
            'last_name': cd.get('last_name', ''),
            'phone_number': cd['phone_number'],
            'joining_date': str(cd['joining_date']),
            'employee_type': cd['employee_type'],
            'father_name': cd.get('father_name', ''),
            'email': cd.get('email', ''),
            'date_of_birth': str(dob) if dob else '',
            'gender': cd.get('gender', ''),
            'address': cd.get('address', ''),
            'city': cd.get('city', ''),
            'qualification': cd.get('qualification', ''),
            'experience_years': cd.get('experience_years') or 0,
            'salary': str(salary) if salary else '',
            'cnic': cd.get('cnic', ''),
            'school_id': school.id,
            'branch_id': branch.id,
        }
        messages.success(request, 'Staff information saved. Now create the account.')
        return redirect(branch_url(request, 'staff:create_staff_wizard'))

    return render(request, 'staff/create_step1.html', {
        'form': form, 'step': 1, 'branch': branch, 'title': 'Create Staff - Step 1',
    })


@transaction.atomic
def _handle_step2(request, school, branch):
    staff_data = request.session.get('staff_wizard_data', {})
    form = StaffCreationStep2Form(request.POST, staff_data=staff_data, branch=branch, request=request)

    if form.is_valid():
        try:
            employee_type = staff_data['employee_type']
            first_name = staff_data.get('first_name', '')
            last_name = staff_data.get('last_name', '')
            full_name = f"{first_name} {last_name}".strip()
            user_type = USER_TYPE_MAP.get(employee_type, 'employee')

            user = User.objects.create_user(
                email=form.cleaned_data['staff_email'],
                password=form.cleaned_data['staff_password'],
                full_name=full_name,
                phone_number=staff_data.get('phone_number', ''),
                user_type=user_type,
                is_active=True,
                payment_verified=True,
            )

            joining_date = staff_data.get('joining_date')
            if joining_date:
                try:
                    joining_date = datetime.date.fromisoformat(joining_date)
                except (ValueError, TypeError):
                    joining_date = timezone.now().date()
            else:
                joining_date = timezone.now().date()

            salary_val = staff_data.get('salary')
            salary = salary_val if salary_val else None

            dob_str = staff_data.get('date_of_birth', '')
            dob = None
            if dob_str:
                try:
                    dob = datetime.date.fromisoformat(dob_str)
                except (ValueError, TypeError):
                    pass

            if employee_type == 'teacher':
                teacher = Teacher(
                    user=user, branch=branch, school=school,
                    qualification=staff_data.get('qualification', ''),
                    experience_years=staff_data.get('experience_years', 0),
                    salary=salary,
                    specialization=form.cleaned_data.get('specialization', ''),
                    joining_date=joining_date,
                    created_by=request.user,
                )
                incharge = form.cleaned_data.get('incharge_section')
                if incharge:
                    teacher.incharge_section = incharge
                teacher.save()

                subjects = form.cleaned_data.get('subjects')
                if subjects:
                    teacher.subjects.set(subjects)

                messages.success(request, f'Teacher "{teacher.full_name}" created successfully!')

            elif employee_type == 'accountant':
                accountant = Accountant.objects.create(
                    user=user, branch=branch, school=school,
                    qualification=staff_data.get('qualification', ''),
                    experience_years=staff_data.get('experience_years', 0),
                    salary=salary,
                    certification=form.cleaned_data.get('certification', ''),
                    joining_date=joining_date,
                    created_by=request.user,
                )
                messages.success(request, f'Accountant "{accountant.full_name}" created successfully!')

            else:
                Employee.objects.create(
                    first_name=first_name, last_name=last_name,
                    father_name=staff_data.get('father_name', ''),
                    phone_number=staff_data.get('phone_number', ''),
                    email=staff_data.get('email', ''),
                    date_of_birth=dob,
                    gender=staff_data.get('gender', ''),
                    address=staff_data.get('address', ''),
                    city=staff_data.get('city', ''),
                    employee_type=employee_type,
                    qualification=staff_data.get('qualification', ''),
                    experience_years=staff_data.get('experience_years', 0),
                    salary=salary,
                    cnic=staff_data.get('cnic', ''),
                    joining_date=joining_date,
                    branch=branch, school=school, user=user,
                    created_by=request.user,
                )
                messages.success(request, f'Employee "{full_name}" created successfully!')

            request.session.pop('staff_wizard_step', None)
            request.session.pop('staff_wizard_data', None)
            return redirect(branch_url(request, 'staff:staff_list'))

        except Exception as e:
            messages.error(request, f'An error occurred: {str(e)}')
            return redirect(branch_url(request, 'staff:create_staff_wizard'))

    return render(request, 'staff/create_step2.html', {
        'form': form, 'step': 2, 'staff_data': staff_data,
        'branch': branch, 'title': 'Create Staff - Step 2',
    })


# ─── List ─────────────────────────────────────────────────────────

@login_required
@require_principal_or_manager()
def staff_list(request):
    school = get_user_school(request.user, request)
    branch = get_user_branch(request.user, request)
    if not school:
        messages.error(request, "No school associated with your account.")
        return _get_dashboard_redirect()

    user = request.user
    is_principal = user.user_type == 'principal'
    is_manager = user.user_type == 'manager'

    # Managers visible to principal; manager sees only self
    managers = User.objects.none()
    if is_principal:
        managers = User.objects.filter(
            user_type='manager', is_active=True,
            managed_branch__school=school,
        ).select_related('managed_branch')
    elif is_manager:
        managers = User.objects.filter(id=user.id)

    teachers = Teacher.objects.filter(school=school, is_active=True).select_related('user', 'branch', 'incharge_section').prefetch_related('subjects')
    accountants = Accountant.objects.filter(school=school, is_active=True).select_related('user', 'branch')
    employees = Employee.objects.filter(school=school, is_active=True).select_related('user', 'branch')

    filter_form = StaffFilterForm(request.GET, school=school)
    if filter_form.is_valid():
        emp_type = filter_form.cleaned_data.get('employee_type')
        status = filter_form.cleaned_data.get('status_filter')
        branch_f = filter_form.cleaned_data.get('branch_filter')
        search = filter_form.cleaned_data.get('search')

        if status:
            is_active_val = status == 'active'
            teachers = Teacher.objects.filter(school=school, is_active=is_active_val).select_related('user', 'branch', 'incharge_section').prefetch_related('subjects')
            accountants = Accountant.objects.filter(school=school, is_active=is_active_val).select_related('user', 'branch')
            employees = Employee.objects.filter(school=school, is_active=is_active_val).select_related('user', 'branch')

        if emp_type:
            if emp_type == 'manager':
                teachers = Teacher.objects.none()
                accountants = Accountant.objects.none()
                employees = Employee.objects.none()
            elif emp_type == 'teacher':
                managers = User.objects.none()
                accountants = Accountant.objects.none()
                employees = Employee.objects.none()
            elif emp_type == 'accountant':
                managers = User.objects.none()
                teachers = Teacher.objects.none()
                employees = Employee.objects.none()
            else:
                managers = User.objects.none()
                teachers = Teacher.objects.none()
                accountants = Accountant.objects.none()
                employees = employees.filter(employee_type=emp_type)

        if branch_f:
            teachers = teachers.filter(branch=branch_f)
            accountants = accountants.filter(branch=branch_f)
            employees = employees.filter(branch=branch_f)
            if is_principal:
                managers = managers.filter(managed_branch=branch_f)

        if search:
            teachers = teachers.filter(Q(user__full_name__icontains=search) | Q(user__email__icontains=search) | Q(employee_code__icontains=search))
            accountants = accountants.filter(Q(user__full_name__icontains=search) | Q(user__email__icontains=search) | Q(employee_code__icontains=search))
            employees = employees.filter(Q(first_name__icontains=search) | Q(last_name__icontains=search) | Q(employee_id__icontains=search) | Q(phone_number__icontains=search))
            if managers.exists():
                managers = managers.filter(Q(full_name__icontains=search) | Q(email__icontains=search))

    total = teachers.count() + accountants.count() + employees.count() + managers.count()

    return render(request, 'staff/staff_list.html', {
        'teachers': teachers, 'accountants': accountants, 'employees': employees,
        'managers': managers,
        'filter_form': filter_form, 'school': school, 'title': 'Staff Management',
        'total_staff': total,
        'can_manage': True,
        'is_principal': is_principal,
        'is_manager': is_manager,
    })


# ─── Detail ───────────────────────────────────────────────────────

@login_required
@require_principal_or_manager()
def staff_detail(request, staff_type, staff_id):
    school = get_user_school(request.user, request)
    if not school:
        return _get_dashboard_redirect()

    if staff_type == 'manager':
        staff_user = get_object_or_404(User, id=staff_id, user_type='manager')
        if request.user.user_type == 'manager' and request.user.id != staff_id:
            raise PermissionDenied("You can only view your own profile.")
        return render(request, 'staff/manager_detail.html', {
            'staff_user': staff_user, 'staff_type': 'manager',
            'title': f'Manager: {staff_user.full_name}',
        })

    if staff_type == 'teacher':
        staff = get_object_or_404(
            Teacher.objects.select_related('user', 'branch', 'school', 'incharge_section').prefetch_related('subjects'),
            id=staff_id, school=school
        )
        template = 'staff/teacher_detail.html'
    elif staff_type == 'accountant':
        staff = get_object_or_404(Accountant.objects.select_related('user', 'branch', 'school'), id=staff_id, school=school)
        template = 'staff/accountant_detail.html'
    else:
        staff = get_object_or_404(Employee.objects.select_related('branch', 'school', 'user'), id=staff_id, school=school)
        template = 'staff/employee_detail.html'

    return render(request, template, {
        'staff': staff, 'staff_type': staff_type,
        'title': f'Staff Details: {staff.full_name}',
    })


# ─── Edit ─────────────────────────────────────────────────────────

@login_required
@require_principal_or_manager()
def edit_staff(request, staff_type, staff_id):
    school = get_user_school(request.user, request)
    branch = get_user_branch(request.user, request)
    if not school:
        return _get_dashboard_redirect()

    if staff_type == 'teacher':
        staff = get_object_or_404(Teacher, id=staff_id, school=school)
        if request.method == 'POST':
            form = TeacherEditForm(request.POST, instance=staff, branch=branch)
        else:
            form = TeacherEditForm(instance=staff, branch=branch)
    elif staff_type == 'accountant':
        staff = get_object_or_404(Accountant, id=staff_id, school=school)
        if request.method == 'POST':
            form = AccountantEditForm(request.POST, instance=staff)
        else:
            form = AccountantEditForm(instance=staff)
    else:
        staff = get_object_or_404(Employee, id=staff_id, school=school)
        if request.method == 'POST':
            form = EmployeeEditForm(request.POST, request.FILES, instance=staff)
        else:
            form = EmployeeEditForm(instance=staff)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'{staff_type.title()} "{staff.full_name}" updated successfully.')
        return redirect(branch_url(request, 'staff:staff_detail', staff_type=staff_type, staff_id=staff.id))

    return render(request, 'staff/edit_staff.html', {
        'form': form, 'staff': staff, 'staff_type': staff_type,
        'title': f'Edit {staff_type.title()}: {staff.full_name}',
    })


# ─── Deactivate / Activate ───────────────────────────────────────

@login_required
@require_principal_or_manager()
def deactivate_staff(request, staff_type, staff_id):
    school = get_user_school(request.user, request)
    if not school:
        return _get_dashboard_redirect()

    if staff_type == 'teacher':
        staff = get_object_or_404(Teacher, id=staff_id, school=school)
    elif staff_type == 'accountant':
        staff = get_object_or_404(Accountant, id=staff_id, school=school)
    else:
        staff = get_object_or_404(Employee, id=staff_id, school=school)

    if request.method == 'POST':
        staff.is_active = False
        staff.save()
        if hasattr(staff, 'user') and staff.user:
            staff.user.is_active = False
            staff.user.save()
        messages.success(request, f'{staff_type.title()} "{staff.full_name}" has been deactivated.')
        return redirect(branch_url(request, 'staff:staff_list'))

    return render(request, 'staff/deactivate_staff.html', {
        'staff': staff, 'staff_type': staff_type,
        'title': f'Deactivate {staff_type.title()}: {staff.full_name}',
    })


@login_required
@require_principal_or_manager()
def activate_staff(request, staff_type, staff_id):
    school = get_user_school(request.user, request)
    if not school:
        return _get_dashboard_redirect()

    if staff_type == 'teacher':
        staff = get_object_or_404(Teacher, id=staff_id, school=school)
    elif staff_type == 'accountant':
        staff = get_object_or_404(Accountant, id=staff_id, school=school)
    else:
        staff = get_object_or_404(Employee, id=staff_id, school=school)

    if request.method == 'POST':
        staff.is_active = True
        staff.save()
        if hasattr(staff, 'user') and staff.user:
            staff.user.is_active = True
            staff.user.save()
        messages.success(request, f'{staff_type.title()} "{staff.full_name}" has been activated.')
        return redirect(branch_url(request, 'staff:staff_list'))

    return render(request, 'staff/activate_staff.html', {
        'staff': staff, 'staff_type': staff_type,
        'title': f'Activate {staff_type.title()}: {staff.full_name}',
    })


# ─── My Profile (Principal / Manager) ────────────────────────────

@login_required
@require_principal_or_manager()
def my_profile(request):
    user = request.user
    school = get_user_school(user, request)
    branch = get_user_branch(user, request)

    return render(request, 'staff/my_profile.html', {
        'profile_user': user,
        'school': school,
        'branch': branch,
        'title': 'My Profile',
    })


@login_required
@require_principal_or_manager()
def edit_my_profile(request):
    user = request.user
    if request.method == 'POST':
        form = ProfileEditForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect(branch_url(request, 'staff:my_profile'))
    else:
        form = ProfileEditForm(instance=user)

    return render(request, 'staff/edit_my_profile.html', {
        'form': form,
        'title': 'Edit My Profile',
    })


# ─── Change Credentials (email/password) for any user ────────────

@login_required
@require_principal_or_manager()
def change_credentials(request, user_id):
    """Principal/Manager can change email and password of any user in their school."""
    actor = request.user
    school = get_user_school(actor)
    if not school:
        return _get_dashboard_redirect()

    target_user = get_object_or_404(User, id=user_id)

    # Manager cannot change other managers' or principal's credentials
    if actor.user_type == 'manager':
        if target_user.user_type == 'principal':
            raise PermissionDenied("Managers cannot change the Principal's credentials.")
        if target_user.user_type == 'manager' and target_user.id != actor.id:
            raise PermissionDenied("Managers cannot change other Managers' credentials.")

    if request.method == 'POST':
        form = ChangeCredentialsForm(request.POST, target_user=target_user)
        if form.is_valid():
            new_email = form.cleaned_data.get('new_email')
            new_password = form.cleaned_data.get('new_password')

            if new_email and new_email != target_user.email:
                target_user.email = new_email
            if new_password:
                target_user.set_password(new_password)

            target_user.save()
            messages.success(request, f'Credentials for "{target_user.full_name}" updated successfully.')
            return redirect(branch_url(request, 'staff:staff_list'))
    else:
        form = ChangeCredentialsForm(target_user=target_user)

    return render(request, 'staff/change_credentials.html', {
        'form': form,
        'target_user': target_user,
        'title': f'Change Credentials: {target_user.full_name}',
    })
