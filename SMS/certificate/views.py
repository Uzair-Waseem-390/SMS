


import json
import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, Http404, FileResponse
from django.utils import timezone
from django.conf import settings
from django.template.loader import render_to_string

from .models import CertificateTemplate, Certificate
from .forms import CertificateTemplateForm, GenerateCertificateForm, CertificateDataForm
from accounts.utils import get_user_branch, get_user_school, branch_url


def _require_certificate_access(view_func):
    """Decorator: only Principal and Manager can access certificate generation."""
    from functools import wraps

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if request.user.user_type not in ('principal', 'manager'):
            raise PermissionDenied("Only principals and managers can manage certificates.")
        return view_func(request, *args, **kwargs)
    return _wrapped


def _can_issue_manager_certificate(request_user, employee_user):
    """Manager cannot issue experience cert for themselves. Principal can issue for any employee including manager."""
    if request_user.user_type == 'principal':
        return True
    if request_user.user_type == 'manager':
        # Manager cannot issue cert for another manager (including self)
        if employee_user and hasattr(employee_user, 'managed_branch') and employee_user.managed_branch:
            return False  # Target is a manager - only principal can do this
        return True
    return False


def _generate_serial_number(branch):
    """Generate unique serial number for certificate."""
    prefix = f"CERT-{branch.code or 'BR'}-" if branch else "CERT-"
    return f"{prefix}{uuid.uuid4().hex[:8].upper()}"


DEFAULT_TEMPLATES = {
    'character': {
        'name': 'Character Certificate',
        'body_template': '''<p>This is to certify that <strong>{{recipient_name}}</strong>, son/daughter of <strong>{{father_name}}</strong>, 
        is/was a student of this institution. He/She is bearing a good moral character and conduct.</p>
        <p>Admission No: {{admission_number}} | Class: {{class_name}} {{section_name}}</p>
        <p>{{custom_text}}</p>''',
    },
    'bonafide': {
        'name': 'Bonafide Certificate',
        'body_template': '''<p>This is to certify that <strong>{{recipient_name}}</strong>, son/daughter of <strong>{{father_name}}</strong>, 
        is a bonafide student of this institution studying in <strong>{{class_name}} - {{section_name}}</strong>.</p>
        <p>Admission Number: {{admission_number}} | Date of Enrollment: {{enrollment_date}}</p>
        <p>{{custom_text}}</p>''',
    },
    'fee_clearance': {
        'name': 'Fee Clearance Certificate',
        'body_template': '''<p>This is to certify that <strong>{{recipient_name}}</strong>, son/daughter of <strong>{{father_name}}</strong>, 
        student of <strong>{{class_name}} - {{section_name}}</strong> (Admission No: {{admission_number}}), 
        has cleared all fee dues up to <strong>{{date}}</strong>.</p>
        <p>{{custom_text}}</p>''',
    },
    'result': {
        'name': 'Result Certificate',
        'body_template': '''<p>This is to certify that <strong>{{recipient_name}}</strong>, son/daughter of <strong>{{father_name}}</strong>, 
        was a student of <strong>{{class_name}} - {{section_name}}</strong> (Admission No: {{admission_number}}) 
        and has successfully completed the academic requirements.</p>
        <p>{{custom_text}}</p>''',
    },
    'leaving': {
        'name': 'Leaving Certificate',
        'body_template': '''<p>This is to certify that <strong>{{recipient_name}}</strong>, son/daughter of <strong>{{father_name}}</strong>, 
        was a bonafide student of this institution from <strong>{{enrollment_date}}</strong> until <strong>{{date}}</strong> 
        in Class <strong>{{class_name}} - {{section_name}}</strong> (Admission No: {{admission_number}}).</p>
        <p>He/She is leaving the institution on the above date. No dues are pending against him/her.</p>
        <p>{{custom_text}}</p>''',
    },
    'experience': {
        'name': 'Experience Certificate',
        'body_template': '''<p>This is to certify that <strong>{{recipient_name}}</strong> worked at our institution as <strong>{{designation}}</strong> 
        from <strong>{{joining_date}}</strong> to <strong>{{leaving_date}}</strong>.</p>
        <p>During the tenure, he/she discharged duties with sincerity and dedication. We wish him/her success in future endeavors.</p>
        <p>{{custom_text}}</p>''',
    },
}


@login_required
@_require_certificate_access
def seed_default_templates(request):
    """Create default certificate templates for the branch if none exist."""
    school = get_user_school(request.user, request)
    branch = get_user_branch(request.user, request)
    if not school or not branch:
        return redirect('tenants:test_page')

    created = 0
    for ttype, data in DEFAULT_TEMPLATES.items():
        if not CertificateTemplate.objects.filter(branch=branch, template_type=ttype).exists():
            CertificateTemplate.objects.create(
                branch=branch,
                school=school,
                name=data['name'],
                template_type=ttype,
                body_template=data['body_template'],
                is_active=True,
            )
            created += 1
    messages.success(request, f'{created} default template(s) created.')
    return redirect(branch_url(request, 'certificate:template_list'))


@login_required
@_require_certificate_access
def template_list(request):
    school = get_user_school(request.user, request)
    branch = get_user_branch(request.user, request)
    if not school or not branch:
        return redirect('tenants:test_page')

    templates = CertificateTemplate.objects.filter(branch=branch).order_by('template_type', 'name')
    return render(request, 'certificate/template_list.html', {
        'templates': templates,
        'branch': branch,
        'title': 'Certificate Templates',
    })


@login_required
@_require_certificate_access
def template_create(request):
    school = get_user_school(request.user, request)
    branch = get_user_branch(request.user, request)
    if not school or not branch:
        return redirect('tenants:test_page')

    if request.method == 'POST':
        form = CertificateTemplateForm(request.POST, branch=branch, school=school)
        if form.is_valid():
            form.save()
            messages.success(request, 'Certificate template created.')
            return redirect(branch_url(request, 'certificate:template_list'))
    else:
        form = CertificateTemplateForm(branch=branch, school=school)
    return render(request, 'certificate/template_form.html', {
        'form': form,
        'branch': branch,
        'title': 'Create Template',
    })


@login_required
@_require_certificate_access
def template_edit(request, pk):
    school = get_user_school(request.user, request)
    branch = get_user_branch(request.user, request)
    if not school or not branch:
        return redirect('tenants:test_page')

    tmpl = get_object_or_404(CertificateTemplate, pk=pk, branch=branch)
    if request.method == 'POST':
        form = CertificateTemplateForm(request.POST, instance=tmpl, branch=branch, school=school)
        if form.is_valid():
            form.save()
            messages.success(request, 'Template updated.')
            return redirect(branch_url(request, 'certificate:template_list'))
    else:
        form = CertificateTemplateForm(instance=tmpl, branch=branch, school=school)
    return render(request, 'certificate/template_form.html', {
        'form': form,
        'template': tmpl,
        'branch': branch,
        'title': 'Edit Template',
    })


@login_required
@_require_certificate_access
def template_delete(request, pk):
    school = get_user_school(request.user, request)
    branch = get_user_branch(request.user, request)
    if not school or not branch:
        return redirect('tenants:test_page')

    tmpl = get_object_or_404(CertificateTemplate, pk=pk, branch=branch)
    if request.method == 'POST':
        tmpl.delete()
        messages.success(request, 'Template deleted.')
        return redirect(branch_url(request, 'certificate:template_list'))
    return render(request, 'certificate/template_confirm_delete.html', {
        'template': tmpl,
        'branch': branch,
        'title': 'Delete Template',
    })


@login_required
@_require_certificate_access
def certificate_list(request):
    school = get_user_school(request.user, request)
    branch = get_user_branch(request.user, request)
    if not school or not branch:
        return redirect('tenants:test_page')

    certs = Certificate.objects.filter(branch=branch).select_related(
        'template', 'student', 'employee', 'issued_by'
    ).order_by('-issued_date', '-created_at')
    return render(request, 'certificate/certificate_list.html', {
        'certificates': certs,
        'branch': branch,
        'title': 'Issued Certificates',
    })


@login_required
@_require_certificate_access
def generate_certificate(request):
    school = get_user_school(request.user, request)
    branch = get_user_branch(request.user, request)
    if not school or not branch:
        return redirect('tenants:test_page')

    step = request.session.get('cert_gen_step', 1)
    template_pk = request.session.get('cert_gen_template_pk')
    student_pk = request.session.get('cert_gen_student_pk')
    employee_id = request.session.get('cert_gen_employee_id')

    # Step 1: Select template and recipient
    if step == 1 or request.GET.get('reset'):
        if request.GET.get('reset'):
            for k in ['cert_gen_step', 'cert_gen_template_pk', 'cert_gen_student_pk', 'cert_gen_employee_id']:
                request.session.pop(k, None)
            return redirect(branch_url(request, 'certificate:generate_certificate'))

        if request.method == 'POST':
            form = GenerateCertificateForm(
                request.POST,
                branch=branch,
                request_user=request.user,
            )
            if form.is_valid():
                template = form.cleaned_data['template']
                request.session['cert_gen_step'] = 2
                request.session['cert_gen_template_pk'] = template.pk
                if template.template_type == 'experience':
                    emp_user = form.get_employee_user()
                    if not emp_user:
                        form.add_error(None, 'Invalid employee selection.')
                    elif not _can_issue_manager_certificate(request.user, emp_user):
                        form.add_error(None, 'Only the Principal can issue experience certificates for Managers.')
                    else:
                        request.session['cert_gen_employee_id'] = emp_user.id
                        return redirect(branch_url(request, 'certificate:generate_certificate'))
                else:
                    request.session['cert_gen_student_pk'] = form.cleaned_data['student'].pk
                    return redirect(branch_url(request, 'certificate:generate_certificate'))
        else:
            form = GenerateCertificateForm(branch=branch, request_user=request.user)
        # For class -> section -> student filtering
        from academics.models import Class, Section
        from students.models import Student
        classes = Class.objects.filter(branch=branch, is_active=True).order_by('numeric_level', 'name')
        sections = Section.objects.filter(class_obj__branch=branch, is_active=True).select_related('class_obj').order_by('class_obj__numeric_level', 'name')
        students = Student.objects.filter(
            section__class_obj__branch=branch,
            is_active=True,
        ).select_related('section', 'section__class_obj').order_by('first_name', 'last_name')
        students_meta_json = json.dumps([
            {'id': s.id, 'section_id': s.section_id, 'class_id': s.section.class_obj_id}
            for s in students
        ])
        return render(request, 'certificate/generate_step1.html', {
            'form': form,
            'branch': branch,
            'school': school,
            'classes': classes,
            'sections': sections,
            'students_meta_json': students_meta_json,
            'title': 'Generate Certificate - Step 1',
        })

    # Step 2: Fill certificate data and generate
    if step == 2:
        if not template_pk:
            request.session.pop('cert_gen_step', None)
            return redirect(branch_url(request, 'certificate:generate_certificate'))

        template = get_object_or_404(CertificateTemplate, pk=template_pk, branch=branch)
        recipient = None
        if template.template_type == 'experience':
            if not employee_id:
                request.session.pop('cert_gen_step', None)
                return redirect(branch_url(request, 'certificate:generate_certificate'))
            from django.contrib.auth import get_user_model
            User = get_user_model()
            recipient = get_object_or_404(User, pk=employee_id)
            if not _can_issue_manager_certificate(request.user, recipient):
                raise PermissionDenied("Only the Principal can issue experience certificates for Managers.")
        else:
            if not student_pk:
                request.session.pop('cert_gen_step', None)
                return redirect(branch_url(request, 'certificate:generate_certificate'))
            from students.models import Student
            recipient = get_object_or_404(Student, pk=student_pk)

        if request.method == 'POST':
            form = CertificateDataForm(request.POST, template=template, recipient=recipient)
            if form.is_valid():
                ctx = form.get_context_dict()
                ctx['school_name'] = school.name
                ctx['branch_name'] = branch.name
                ctx['template_type'] = template.get_template_type_display()

                serial = _generate_serial_number(branch)
                ctx['serial_number'] = serial

                cert = Certificate.objects.create(
                    template=template,
                    branch=branch,
                    school=school,
                    student=recipient if template.template_type != 'experience' else None,
                    employee=recipient if template.template_type == 'experience' else None,
                    issued_by=request.user,
                    issued_date=form.cleaned_data['issue_date'],
                    serial_number=serial,
                    custom_data=ctx,
                )

                for k in ['cert_gen_step', 'cert_gen_template_pk', 'cert_gen_student_pk', 'cert_gen_employee_id']:
                    request.session.pop(k, None)

                messages.success(request, f'Certificate generated successfully. Serial: {serial}')
                return redirect(branch_url(request, 'certificate:certificate_detail', pk=cert.pk))
        else:
            form = CertificateDataForm(template=template, recipient=recipient)

        return render(request, 'certificate/generate_step2.html', {
            'form': form,
            'template': template,
            'recipient': recipient,
            'branch': branch,
            'school': school,
            'title': 'Generate Certificate - Step 2',
        })

    return redirect(branch_url(request, 'certificate:generate_certificate'))


def _render_template_body(body_html, context):
    """Replace {{placeholder}} in body with context values."""
    import re
    result = body_html
    for key, val in context.items():
        result = result.replace('{{' + key + '}}', str(val))
    result = re.sub(r'\{\{[^}]+\}\}', '', result)  # Remove unmatched placeholders
    return result


@login_required
@_require_certificate_access
def certificate_detail(request, pk):
    school = get_user_school(request.user, request)
    branch = get_user_branch(request.user, request)
    if not school or not branch:
        return redirect('tenants:test_page')

    cert = get_object_or_404(Certificate, pk=pk, branch=branch)
    return render(request, 'certificate/certificate_detail.html', {
        'certificate': cert,
        'branch': branch,
        'title': f'Certificate {cert.serial_number}',
    })


@login_required
@_require_certificate_access
def certificate_print(request, pk):
    """Render a print-ready HTML page. User prints/saves as PDF via browser."""
    school = get_user_school(request.user, request)
    branch = get_user_branch(request.user, request)
    if not school or not branch:
        raise Http404

    cert = get_object_or_404(Certificate, pk=pk, branch=branch)
    ctx = cert.custom_data or {}
    html_body = _render_template_body(cert.template.body_template, ctx)

    return render(request, 'certificate/certificate_print.html', {
        'certificate': cert,
        'school': school,
        'branch': branch,
        'html_body': html_body,
        'ctx': ctx,
    })