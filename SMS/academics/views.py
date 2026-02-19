from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.urls import reverse
from django.http import JsonResponse
from .models import Class, Section, Subject, SectionSubject
from students.models import Student
from .forms import (
    ClassCreationStep1Form,
    ClassEditForm,
    SectionCreationStep2Form,
    SubjectForm,
    SectionSubjectAssignmentForm,
    SectionFilterForm,
    SectionEditForm,
)

from rbac.services import require_permission, require_principal_or_manager, require_principal_or_manager_or_permission
from rbac.permissions import Permissions
from accounts.utils import get_user_branch, can_manage_academics, branch_url


def _get_dashboard_redirect():
    """Redirect target when user has no branch."""
    try:
        return redirect('tenants:test_page')
    except Exception:
        return redirect('accounts:profile')


@login_required
@require_principal_or_manager()
def create_class_wizard(request):
    """
    Two-step wizard for creating a class with sections.
    Only managers and principals can create.
    """
    branch = get_user_branch(request.user, request)
    if not branch:
        messages.error(request, "No branch associated with your account.")
        return _get_dashboard_redirect()

    # Reset to step 1 if user clicks Back
    if request.GET.get('back') == '1':
        request.session.pop('class_wizard_step', None)
        request.session.pop('class_wizard_data', None)
        return redirect(branch_url(request, 'academics:create_class_wizard'))

    step = request.session.get('class_wizard_step', 1)

    if request.method == 'POST':
        if step == 1:
            return handle_step1(request, branch)
        elif step == 2:
            return handle_step2(request, branch)

    if step == 1:
        form = ClassCreationStep1Form(branch=branch)
        return render(request, 'academics/class_wizard_step1.html', {
            'form': form,
            'step': 1,
            'branch': branch,
            'title': 'Create Class - Step 1'
        })
    elif step == 2:
        class_data = request.session.get('class_wizard_data', {})
        num_sections = class_data.get('num_sections', 1)
        form = SectionCreationStep2Form(num_sections=num_sections)
        return render(request, 'academics/class_wizard_step2.html', {
            'form': form,
            'step': 2,
            'num_sections': num_sections,
            'class_name': class_data.get('class_name'),
            'branch': branch,
            'title': 'Create Sections - Step 2'
        })
    return redirect(branch_url(request, 'academics:create_class_wizard'))


def handle_step1(request, branch):
    """Handle Step 1 form submission."""
    form = ClassCreationStep1Form(request.POST, branch=branch)

    if form.is_valid():
        request.session['class_wizard_step'] = 2
        request.session['class_wizard_data'] = {
            'class_name': form.cleaned_data['name'],
            'numeric_level': form.cleaned_data.get('numeric_level'),
            'description': form.cleaned_data.get('description', ''),
            'num_sections': form.cleaned_data['number_of_sections'],
        }
        messages.success(request, 'Class information saved. Now add section details.')
        return redirect(branch_url(request, 'academics:create_class_wizard'))
    else:
        messages.error(request, 'Please correct the errors below.')
        return render(request, 'academics/class_wizard_step1.html', {
            'form': form,
            'step': 1,
            'branch': branch,
            'title': 'Create Class - Step 1'
        })


@transaction.atomic
def handle_step2(request, branch):
    """Handle Step 2 form submission and save everything."""
    class_data = request.session.get('class_wizard_data', {})
    num_sections = class_data.get('num_sections', 1)

    form = SectionCreationStep2Form(request.POST, num_sections=num_sections)

    if form.is_valid():
        try:
            new_class = Class.objects.create(
                name=class_data['class_name'],
                branch=branch,
                numeric_level=class_data.get('numeric_level'),
                description=class_data.get('description', ''),
                created_by=request.user
            )

            sections_created = []
            for i in range(1, num_sections + 1):
                section_name = form.cleaned_data.get(f'section_{i}_name', '')
                if not section_name:
                    continue
                section_capacity = form.cleaned_data.get(f'section_{i}_capacity') or 30
                section_room = form.cleaned_data.get(f'section_{i}_room', '')

                section = Section.objects.create(
                    name=section_name,
                    class_obj=new_class,
                    capacity=section_capacity,
                    room_number=section_room,
                    created_by=request.user
                )
                sections_created.append(section.name)

            request.session.pop('class_wizard_step', None)
            request.session.pop('class_wizard_data', None)

            messages.success(
                request,
                f'Class "{new_class.name}" created successfully with {len(sections_created)} sections: '
                f'{", ".join(sections_created)}'
            )
            return redirect(branch_url(request, 'academics:class_list'))

        except Exception as e:
            messages.error(request, f'An error occurred: {str(e)}')
            return render(request, 'academics/class_wizard_step2.html', {
                'form': form,
                'step': 2,
                'num_sections': num_sections,
                'class_name': class_data.get('class_name'),
                'branch': branch,
                'title': 'Create Sections - Step 2'
            })
    else:
        messages.error(request, 'Please correct the errors below.')
        return render(request, 'academics/class_wizard_step2.html', {
            'form': form,
            'step': 2,
            'num_sections': num_sections,
            'class_name': class_data.get('class_name'),
            'branch': branch,
            'title': 'Create Sections - Step 2'
        })


@login_required
@require_principal_or_manager_or_permission(Permissions.CLASS_VIEW.value)
def class_list(request):
    """Display list of all classes in the user's branch."""
    branch = get_user_branch(request.user, request)
    if not branch:
        messages.error(request, "No branch associated with your account.")
        return _get_dashboard_redirect()

    classes = Class.objects.filter(branch=branch, is_active=True).prefetch_related('sections')

    return render(request, 'academics/class_list.html', {
        'classes': classes,
        'branch': branch,
        'title': 'Classes Management',
        'can_manage': can_manage_academics(request.user),
    })


@login_required
@require_principal_or_manager()
def edit_class(request, class_id):
    """Edit class details."""
    branch = get_user_branch(request.user, request)
    if not branch:
        messages.error(request, "No branch associated with your account.")
        return _get_dashboard_redirect()

    class_obj = get_object_or_404(Class, id=class_id, branch=branch)

    if request.method == 'POST':
        form = ClassEditForm(request.POST, instance=class_obj, branch=branch)
        if form.is_valid():
            form.save()
            messages.success(request, f'Class "{class_obj.name}" updated successfully.')
            return redirect(branch_url(request, 'academics:class_list'))
    else:
        form = ClassEditForm(instance=class_obj, branch=branch)

    return render(request, 'academics/edit_class.html', {
        'form': form,
        'class_obj': class_obj,
        'branch': branch,
        'title': f'Edit Class: {class_obj.name}'
    })


@login_required
@require_principal_or_manager()
def delete_class(request, class_id):
    """Delete a class (soft delete)."""
    branch = get_user_branch(request.user, request)
    if not branch:
        messages.error(request, "No branch associated with your account.")
        return _get_dashboard_redirect()

    class_obj = get_object_or_404(Class, id=class_id, branch=branch)

    if request.method == 'POST':
        class_obj.is_active = False
        class_obj.save()
        messages.success(request, f'Class "{class_obj.name}" has been deactivated.')
        return redirect(branch_url(request, 'academics:class_list'))

    return render(request, 'academics/delete_class.html', {
        'class_obj': class_obj,
        'branch': branch,
        'title': f'Delete Class: {class_obj.name}'
    })


@login_required
@require_principal_or_manager_or_permission(Permissions.SECTION_VIEW.value)
def section_list(request, class_id=None):
    """Display list of sections, optionally filtered by class."""
    branch = get_user_branch(request.user, request)
    if not branch:
        messages.error(request, "No branch associated with your account.")
        return _get_dashboard_redirect()

    sections = Section.objects.filter(class_obj__branch=branch, is_active=True)

    if class_id:
        sections = sections.filter(class_obj_id=class_id)
        current_class = get_object_or_404(Class, id=class_id, branch=branch)
    else:
        current_class = None

    filter_form = SectionFilterForm(request.GET, branch=branch)
    if filter_form.is_valid() and filter_form.cleaned_data.get('class_filter'):
        sections = sections.filter(class_obj=filter_form.cleaned_data['class_filter'])
        if not current_class:
            current_class = filter_form.cleaned_data['class_filter']

    sections = sections.select_related('class_obj').prefetch_related('subject_assignments__subject')

    return render(request, 'academics/section_list.html', {
        'sections': sections,
        'filter_form': filter_form,
        'current_class': current_class,
        'branch': branch,
        'title': 'Sections Management',
        'can_manage': can_manage_academics(request.user),
    })


@login_required
@require_principal_or_manager_or_permission(Permissions.SECTION_VIEW.value)
def section_students(request, section_id):
    """Display all students in a section."""
    branch = get_user_branch(request.user, request)
    if not branch:
        messages.error(request, "No branch associated with your account.")
        return _get_dashboard_redirect()

    section = get_object_or_404(Section, id=section_id, class_obj__branch=branch)
    students = Student.objects.filter(section=section, is_active=True).select_related(
        'user'
    ).prefetch_related('parents')

    return render(request, 'academics/section_students.html', {
        'section': section,
        'students': students,
        'branch': branch,
        'class_obj': section.class_obj,
        'title': f'Students - {section.class_obj.name} {section.name}',
    })


@login_required
@require_principal_or_manager()
def edit_section(request, section_id):
    """Edit section details."""
    branch = get_user_branch(request.user, request)
    if not branch:
        messages.error(request, "No branch associated with your account.")
        return _get_dashboard_redirect()

    section = get_object_or_404(Section, id=section_id, class_obj__branch=branch)

    if request.method == 'POST':
        form = SectionEditForm(request.POST, instance=section)
        if form.is_valid():
            form.save()
            messages.success(request, f'Section "{section.name}" updated successfully.')
            return redirect(branch_url(request, 'academics:section_list'))
    else:
        form = SectionEditForm(instance=section)

    return render(request, 'academics/edit_section.html', {
        'form': form,
        'section': section,
        'branch': branch,
        'title': f'Edit Section: {section.name}'
    })


@login_required
@require_principal_or_manager()
def delete_section(request, section_id):
    """Delete a section (soft delete)."""
    branch = get_user_branch(request.user, request)
    if not branch:
        messages.error(request, "No branch associated with your account.")
        return _get_dashboard_redirect()

    section = get_object_or_404(Section, id=section_id, class_obj__branch=branch)

    if request.method == 'POST':
        section.is_active = False
        section.save()
        messages.success(request, f'Section "{section.name}" has been deactivated.')
        return redirect(branch_url(request, 'academics:section_list'))

    return render(request, 'academics/delete_section.html', {
        'section': section,
        'branch': branch,
        'title': f'Delete Section: {section.name}'
    })


@login_required
@require_principal_or_manager_or_permission(Permissions.SUBJECT_VIEW.value)
def subject_list(request):
    """Display list of all subjects in the branch."""
    branch = get_user_branch(request.user, request)
    if not branch:
        messages.error(request, "No branch associated with your account.")
        return _get_dashboard_redirect()

    subjects = Subject.objects.filter(branch=branch, is_active=True)

    return render(request, 'academics/subject_list.html', {
        'subjects': subjects,
        'branch': branch,
        'title': 'Subjects Management',
        'can_manage': can_manage_academics(request.user),
    })


@login_required
@require_principal_or_manager()
def create_subject(request):
    """Create a new subject."""
    branch = get_user_branch(request.user, request)
    if not branch:
        messages.error(request, "No branch associated with your account.")
        return _get_dashboard_redirect()

    if request.method == 'POST':
        form = SubjectForm(request.POST, branch=branch)
        if form.is_valid():
            subject = form.save(commit=False)
            subject.created_by = request.user
            subject.save()
            messages.success(request, f'Subject "{subject.name}" created successfully.')
            return redirect(branch_url(request, 'academics:subject_list'))
    else:
        form = SubjectForm(branch=branch)

    return render(request, 'academics/subject_form.html', {
        'form': form,
        'branch': branch,
        'title': 'Create Subject'
    })


@login_required
@require_principal_or_manager()
def edit_subject(request, subject_id):
    """Edit an existing subject."""
    branch = get_user_branch(request.user, request)
    if not branch:
        messages.error(request, "No branch associated with your account.")
        return _get_dashboard_redirect()

    subject = get_object_or_404(Subject, id=subject_id, branch=branch)

    if request.method == 'POST':
        form = SubjectForm(request.POST, instance=subject, branch=branch)
        if form.is_valid():
            form.save()
            messages.success(request, f'Subject "{subject.name}" updated successfully.')
            return redirect(branch_url(request, 'academics:subject_list'))
    else:
        form = SubjectForm(instance=subject, branch=branch)

    return render(request, 'academics/subject_form.html', {
        'form': form,
        'subject': subject,
        'branch': branch,
        'title': f'Edit Subject: {subject.name}'
    })


@login_required
@require_principal_or_manager()
def delete_subject(request, subject_id):
    """Delete a subject (soft delete)."""
    branch = get_user_branch(request.user, request)
    if not branch:
        messages.error(request, "No branch associated with your account.")
        return _get_dashboard_redirect()

    subject = get_object_or_404(Subject, id=subject_id, branch=branch)

    if request.method == 'POST':
        subject.is_active = False
        subject.save()
        messages.success(request, f'Subject "{subject.name}" has been deactivated.')
        return redirect(branch_url(request, 'academics:subject_list'))

    return render(request, 'academics/delete_subject.html', {
        'subject': subject,
        'branch': branch,
        'title': f'Delete Subject: {subject.name}'
    })


@login_required
@require_principal_or_manager()
def assign_subjects_to_section(request, section_id):
    """Assign subjects to a section. Only managers and principals."""
    branch = get_user_branch(request.user, request)
    if not branch:
        messages.error(request, "No branch associated with your account.")
        return _get_dashboard_redirect()

    section = get_object_or_404(Section, id=section_id, class_obj__branch=branch)

    assigned_subjects = section.subject_assignments.values_list('subject_id', flat=True)
    available_subjects = Subject.objects.filter(
        branch=section.branch,
        is_active=True
    ).exclude(id__in=assigned_subjects)

    if request.method == 'POST':
        form = SectionSubjectAssignmentForm(
            request.POST,
            section=section,
            available_subjects=available_subjects
        )
        if form.is_valid():
            assignments = form.save(assigned_by=request.user)
            if assignments:
                messages.success(
                    request,
                    f'{len(assignments)} subject(s) assigned to section {section.name} successfully.'
                )
            else:
                messages.info(request, 'No subjects were selected for assignment.')
            return redirect(branch_url(request, 'academics:section_list'))
    else:
        form = SectionSubjectAssignmentForm(
            section=section,
            available_subjects=available_subjects
        )

    # Get teachers for this branch (from UserRole)
    teachers = _get_teachers_for_branch(section.branch)

    return render(request, 'academics/assign_subjects.html', {
        'form': form,
        'section': section,
        'available_subjects': available_subjects,
        'teachers': teachers,
        'branch': branch,
        'title': f'Assign Subjects to {section}'
    })


@login_required
@require_principal_or_manager()
def remove_subject_from_section(request, assignment_id):
    """Remove a subject assignment from a section."""
    branch = get_user_branch(request.user, request)
    if not branch:
        messages.error(request, "No branch associated with your account.")
        return _get_dashboard_redirect()

    assignment = get_object_or_404(SectionSubject, id=assignment_id, section__class_obj__branch=branch)

    if request.method == 'POST':
        section_name = assignment.section.name
        subject_name = assignment.subject.name
        assignment.delete()
        messages.success(request, f'Subject "{subject_name}" removed from section {section_name}.')
        return redirect(branch_url(request, 'academics:section_list'))

    return render(request, 'academics/remove_subject.html', {
        'assignment': assignment,
        'branch': branch,
        'title': 'Remove Subject Assignment'
    })


def _get_teachers_for_branch(branch):
    """Get teachers available for a branch (from UserRole or user_type)."""
    from django.contrib.auth import get_user_model
    from django.db.models import Q
    from rbac.models import UserRole
    User = get_user_model()

    # Teachers assigned to this branch via UserRole
    teacher_ids = UserRole.objects.filter(
        role__name='teacher',
        is_active=True
    ).filter(Q(branch=branch) | Q(branch__isnull=True)).values_list('user_id', flat=True)

    if teacher_ids:
        return User.objects.filter(pk__in=teacher_ids, is_active=True).order_by('full_name')
    # Fallback: all teachers in system
    return User.objects.filter(user_type='teacher', is_active=True).order_by('full_name')


# ═══ Student Transfer / Promotion ════════════════════════════════

@login_required
def api_sections_for_class(request):
    """AJAX: Return sections for a given class_id within the user's branch."""
    branch = get_user_branch(request.user, request)
    class_id = request.GET.get('class_id')
    if not branch or not class_id:
        return JsonResponse({'sections': []})
    sections = Section.objects.filter(
        class_obj_id=class_id, class_obj__branch=branch, is_active=True
    ).order_by('name').values('id', 'name')
    return JsonResponse({'sections': list(sections)})


@login_required
@require_principal_or_manager()
def transfer_students(request, section_id):
    """
    Transfer selected (or all) students from one section to another.
    Used for promotions or section re-assignment within the branch.
    """
    branch = get_user_branch(request.user, request)
    if not branch:
        messages.error(request, "No branch associated with your account.")
        return _get_dashboard_redirect()

    source_section = get_object_or_404(Section, id=section_id, class_obj__branch=branch)
    students = Student.objects.filter(section=source_section, is_active=True).order_by('first_name', 'last_name')

    classes = Class.objects.filter(branch=branch, is_active=True).order_by('numeric_level', 'name')

    if request.method == 'POST':
        target_section_id = request.POST.get('target_section')
        student_ids = request.POST.getlist('students')

        if not target_section_id:
            messages.error(request, 'Please select a target section.')
            return render(request, 'academics/transfer_students.html', {
                'source_section': source_section, 'students': students,
                'classes': classes, 'title': f'Transfer Students from {source_section}',
            })

        target_section = get_object_or_404(Section, id=target_section_id, class_obj__branch=branch)

        if target_section.id == source_section.id:
            messages.error(request, 'Source and target sections are the same.')
            return render(request, 'academics/transfer_students.html', {
                'source_section': source_section, 'students': students,
                'classes': classes, 'title': f'Transfer Students from {source_section}',
            })

        if not student_ids:
            messages.error(request, 'Please select at least one student to transfer.')
            return render(request, 'academics/transfer_students.html', {
                'source_section': source_section, 'students': students,
                'classes': classes, 'title': f'Transfer Students from {source_section}',
            })

        with transaction.atomic():
            transferred = Student.objects.filter(
                id__in=student_ids, section=source_section, is_active=True
            ).update(section=target_section)

        messages.success(
            request,
            f'{transferred} student(s) transferred from '
            f'{source_section.class_obj.name}-{source_section.name} to '
            f'{target_section.class_obj.name}-{target_section.name}.'
        )
        return redirect(branch_url(request, 'academics:section_students', section_id=source_section.id))

    return render(request, 'academics/transfer_students.html', {
        'source_section': source_section,
        'students': students,
        'classes': classes,
        'title': f'Transfer Students from {source_section}',
    })
