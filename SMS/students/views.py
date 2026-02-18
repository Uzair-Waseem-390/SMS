from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.urls import reverse
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime

from .models import Student, Parent
from .forms import (
    StudentCreationStep1Form, StudentCreationStep2Form,
    StudentFilterForm, StudentEditForm, ParentEditForm
)
from academics.models import Class, Section
from rbac.services import require_principal_or_manager, require_principal_or_manager_or_permission
from rbac.permissions import Permissions
from accounts.utils import get_user_branch
from django.contrib.auth import get_user_model

User = get_user_model()


def _get_dashboard_redirect():
    """Redirect target when user has no branch."""
    try:
        return redirect('tenants:test_page')
    except Exception:
        return redirect('accounts:profile')


@login_required
@require_principal_or_manager()
def create_student_wizard(request):
    """
    Two-step wizard for creating a student with parent account.
    """
    branch = get_user_branch(request.user, request)
    if not branch:
        messages.error(request, "No branch associated with your account.")
        return _get_dashboard_redirect()

    # Reset to step 1 if user clicks Back
    if request.GET.get('back') == '1':
        request.session.pop('student_wizard_step', None)
        request.session.pop('student_wizard_data', None)
        return redirect('students:create_student_wizard')

    step = request.session.get('student_wizard_step', 1)
    
    if request.method == 'POST':
        if step == 1:
            return handle_step1(request, branch)
        elif step == 2:
            return handle_step2(request, branch)
    
    # GET request - show appropriate step
    if step == 1:
        form = StudentCreationStep1Form(branch=branch)
        return render(request, 'students/create_step1.html', {
            'form': form,
            'step': 1,
            'branch': branch,
            'title': 'Create Student - Step 1'
        })
    elif step == 2:
        student_data = request.session.get('student_wizard_data', {})
        form = StudentCreationStep2Form(student_data=student_data)
        return render(request, 'students/create_step2.html', {
            'form': form,
            'step': 2,
            'student_data': student_data,
            'branch': branch,
            'title': 'Create Student - Step 2'
        })


def handle_step1(request, branch):
    """Handle Step 1 form submission."""
    form = StudentCreationStep1Form(request.POST, branch=branch)
    
    if form.is_valid():
        # Get the selected section
        section = form.cleaned_data['section_choice']
        
        # Store data in session
        request.session['student_wizard_step'] = 2
        request.session['student_wizard_data'] = {
            'first_name': form.cleaned_data['first_name'],
            'last_name': form.cleaned_data['last_name'],
            'father_name': form.cleaned_data['father_name'],
            'mother_name': form.cleaned_data.get('mother_name', ''),
            'date_of_birth': str(form.cleaned_data.get('date_of_birth', '')),
            'gender': form.cleaned_data.get('gender', ''),
            'phone_number': form.cleaned_data.get('phone_number', ''),
            'email': form.cleaned_data.get('email', ''),
            'address': form.cleaned_data.get('address', ''),
            'class_id': form.cleaned_data['class_choice'].id,
            'class_name': form.cleaned_data['class_choice'].name,
            'section_id': section.id,
            'section_name': section.name,
        }
        
        messages.success(request, 'Student information saved. Now create accounts.')
        return redirect('students:create_student_wizard')
    else:
        messages.error(request, 'Please correct the errors below.')
        return render(request, 'students/create_step1.html', {
            'form': form,
            'step': 1,
            'branch': branch,
            'title': 'Create Student - Step 1'
        })


@transaction.atomic
def handle_step2(request, branch):
    """Handle Step 2 form submission and save everything."""
    student_data = request.session.get('student_wizard_data', {})
    
    form = StudentCreationStep2Form(request.POST, student_data=student_data)
    
    if form.is_valid():
        try:
            # Get section
            section = Section.objects.get(id=student_data['section_id'])
            
            # 1. Create Student User
            student_user = User.objects.create_user(
                email=form.cleaned_data['student_email'],
                password=form.cleaned_data['student_password'],
                full_name=f"{student_data['first_name']} {student_data['last_name']}",
                phone_number=student_data.get('phone_number', '') or '',
                user_type='student',
                is_active=True,
                payment_verified=True,
            )
            
            # Parse date_of_birth from session (stored as string)
            dob = student_data.get('date_of_birth')
            date_of_birth = None
            if dob and dob not in ('', 'None'):
                try:
                    date_of_birth = datetime.strptime(str(dob), '%Y-%m-%d').date()
                except (ValueError, TypeError):
                    pass

            # 2. Create Student Profile
            student = Student.objects.create(
                first_name=student_data['first_name'],
                last_name=student_data['last_name'],
                father_name=student_data['father_name'],
                mother_name=student_data.get('mother_name', ''),
                date_of_birth=date_of_birth,
                gender=student_data.get('gender', ''),
                phone_number=student_data.get('phone_number', ''),
                email=student_data.get('email', ''),
                address=student_data.get('address', ''),
                section=section,
                created_by=request.user,
                user=student_user
            )
            
            # 3. Create Parent User
            parent_user = User.objects.create_user(
                email=form.cleaned_data['parent_email'],
                password=form.cleaned_data['parent_password'],
                full_name=f"{form.cleaned_data['parent_first_name']} {form.cleaned_data['parent_last_name']}",
                phone_number=form.cleaned_data.get('parent_phone', '') or '',
                user_type='parent',
                is_active=True,
                payment_verified=True,
            )
            
            # 4. Create Parent Profile
            parent = Parent.objects.create(
                first_name=form.cleaned_data['parent_first_name'],
                last_name=form.cleaned_data['parent_last_name'],
                relationship=form.cleaned_data['parent_relationship'],
                phone_number=form.cleaned_data['parent_phone'],
                email=form.cleaned_data['parent_email'],
                created_by=request.user,
                user=parent_user
            )
            
            # 5. Link parent to student
            parent.students.add(student)
            
            # Clear session data
            request.session.pop('student_wizard_step', None)
            request.session.pop('student_wizard_data', None)
            
            messages.success(
                request, 
                f'Student "{student.full_name}" created successfully!<br>'
                f'Student Login: {student_user.email}<br>'
                f'Parent Login: {parent_user.email}',
                extra_tags='safe'
            )
            return redirect('students:student_detail', student_id=student.id)
            
        except Exception as e:
            messages.error(request, f'An error occurred: {str(e)}')
            return render(request, 'students/create_step2.html', {
                'form': form,
                'step': 2,
                'student_data': student_data,
                'branch': branch,
                'title': 'Create Student - Step 2'
            })
    else:
        messages.error(request, 'Please correct the errors below.')
        return render(request, 'students/create_step2.html', {
            'form': form,
            'step': 2,
            'student_data': student_data,
            'branch': branch,
            'title': 'Create Student - Step 2'
        })


@login_required
@require_principal_or_manager_or_permission(Permissions.STUDENT_VIEW.value)
def student_list(request):
    """Display list of all students with filters."""
    branch = get_user_branch(request.user, request)
    if not branch:
        messages.error(request, "No branch associated with your account.")
        return _get_dashboard_redirect()
    
    students = Student.objects.filter(section__class_obj__branch=branch).select_related(
        'section', 'section__class_obj', 'user'
    ).prefetch_related('parents')
    
    # Apply filters
    filter_form = StudentFilterForm(request.GET, branch=branch)
    if filter_form.is_valid():
        class_filter = filter_form.cleaned_data.get('class_filter')
        section_filter = filter_form.cleaned_data.get('section_filter')
        status_filter = filter_form.cleaned_data.get('status_filter')
        search = filter_form.cleaned_data.get('search')
        
        if class_filter:
            students = students.filter(section__class_obj=class_filter)
        if section_filter:
            students = students.filter(section=section_filter)
        if status_filter:
            is_active = status_filter == 'active'
            students = students.filter(is_active=is_active)
        if search:
            students = students.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(admission_number__icontains=search) |
                Q(father_name__icontains=search)
            )
    
    context = {
        'students': students,
        'filter_form': filter_form,
        'branch': branch,
        'title': 'Students Management',
        'total_students': students.count(),
        'active_students': students.filter(is_active=True).count(),
    }
    return render(request, 'students/student_list.html', context)


@login_required
@require_principal_or_manager_or_permission(Permissions.STUDENT_VIEW.value)
def student_detail(request, student_id):
    """Display detailed information about a student."""
    branch = get_user_branch(request.user, request)
    if not branch:
        messages.error(request, "No branch associated with your account.")
        return _get_dashboard_redirect()
    student = get_object_or_404(
        Student.objects.select_related('section', 'section__class_obj', 'user')
        .prefetch_related('parents', 'parents__user'),
        id=student_id,
        section__class_obj__branch=branch
    )
    
    return render(request, 'students/student_detail.html', {
        'student': student,
        'title': f'Student: {student.full_name}'
    })


@login_required
@require_principal_or_manager()
def edit_student(request, student_id):
    """Edit student information."""
    branch = get_user_branch(request.user, request)
    if not branch:
        messages.error(request, "No branch associated with your account.")
        return _get_dashboard_redirect()
    student = get_object_or_404(Student, id=student_id, section__class_obj__branch=branch)
    
    if request.method == 'POST':
        form = StudentEditForm(request.POST, request.FILES, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, f'Student "{student.full_name}" updated successfully.')
            return redirect('students:student_detail', student_id=student.id)
    else:
        form = StudentEditForm(instance=student)
    
    return render(request, 'students/edit_student.html', {
        'form': form,
        'student': student,
        'title': f'Edit Student: {student.full_name}'
    })


@login_required
@require_principal_or_manager()
def delete_student(request, student_id):
    """Soft delete a student."""
    branch = get_user_branch(request.user, request)
    if not branch:
        messages.error(request, "No branch associated with your account.")
        return _get_dashboard_redirect()
    student = get_object_or_404(Student, id=student_id, section__class_obj__branch=branch)
    
    if request.method == 'POST':
        student.is_active = False
        if student.user:
            student.user.is_active = False
            student.user.save()
        student.save()
        messages.success(request, f'Student "{student.full_name}" has been deactivated.')
        return redirect('students:student_list')
    
    return render(request, 'students/delete_student.html', {
        'student': student,
        'title': f'Delete Student: {student.full_name}'
    })


@login_required
@require_principal_or_manager_or_permission(Permissions.PARENT_VIEW.value)
def parent_list(request):
    """Display list of all parents."""
    branch = get_user_branch(request.user, request)
    if not branch:
        messages.error(request, "No branch associated with your account.")
        return _get_dashboard_redirect()
    
    parents = Parent.objects.filter(students__section__class_obj__branch=branch).distinct().prefetch_related(
        'students', 'user'
    )
    
    return render(request, 'students/parent_list.html', {
        'parents': parents,
        'branch': branch,
        'title': 'Parents Management'
    })


@login_required
@require_principal_or_manager_or_permission(Permissions.PARENT_VIEW.value)
def parent_detail(request, parent_id):
    """Display detailed information about a parent."""
    branch = get_user_branch(request.user, request)
    if not branch:
        messages.error(request, "No branch associated with your account.")
        return _get_dashboard_redirect()
    parent = get_object_or_404(
        Parent.objects.filter(students__section__class_obj__branch=branch).distinct()
            .prefetch_related('students', 'students__section', 'user'),
        id=parent_id
    )
    
    return render(request, 'students/parent_detail.html', {
        'parent': parent,
        'title': f'Parent: {parent.full_name}'
    })


@login_required
@require_principal_or_manager()
def edit_parent(request, parent_id):
    """Edit parent information."""
    branch = get_user_branch(request.user, request)
    if not branch:
        messages.error(request, "No branch associated with your account.")
        return _get_dashboard_redirect()
    parent = get_object_or_404(
        Parent.objects.filter(students__section__class_obj__branch=branch).distinct(),
        id=parent_id
    )
    
    if request.method == 'POST':
        form = ParentEditForm(request.POST, request.FILES, instance=parent)
        if form.is_valid():
            # Update associated user email if changed
            parent_user = parent.user
            if parent_user and 'email' in form.cleaned_data:
                parent_user.email = form.cleaned_data['email']
                parent_user.save()
            
            form.save()
            messages.success(request, f'Parent "{parent.full_name}" updated successfully.')
            return redirect('students:parent_detail', parent_id=parent.id)
    else:
        form = ParentEditForm(instance=parent)
    
    return render(request, 'students/edit_parent.html', {
        'form': form,
        'parent': parent,
        'title': f'Edit Parent: {parent.full_name}'
    })


@login_required
def get_sections_by_class(request):
    """AJAX view to get sections for a selected class."""
    class_id = request.GET.get('class_id')
    if class_id:
        sections = Section.objects.filter(class_obj_id=class_id, is_active=True).values('id', 'name')
        return JsonResponse(list(sections), safe=False)
    return JsonResponse([], safe=False)