from django import forms
from django.contrib.auth import get_user_model
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Fieldset, Submit, Div, HTML, Field
from crispy_forms.bootstrap import FormActions

from .models import CertificateTemplate, Certificate
from students.models import Student
from accounts.utils import branch_url

User = get_user_model()


def get_branch_staff_for_experience_cert(branch, exclude_manager_if_current=None):
    """Return list of (user_id, display_label) for experience certificate dropdown.
    Excludes manager if exclude_manager_if_current is the current user (manager cannot cert self).
    """
    from staff.models import Teacher, Accountant, Employee
    choices = []
    if branch.manager and branch.manager != exclude_manager_if_current:
        choices.append((branch.manager.id, f"{branch.manager.full_name} (Manager)"))
    for t in Teacher.objects.filter(branch=branch, is_active=True).select_related('user'):
        if t.user and t.user != exclude_manager_if_current:
            choices.append((t.user.id, f"{t.user.full_name} (Teacher)"))
    for a in Accountant.objects.filter(branch=branch, is_active=True).select_related('user'):
        if a.user and a.user != exclude_manager_if_current:
            choices.append((a.user.id, f"{a.user.full_name} (Accountant)"))
    for e in Employee.objects.filter(branch=branch, is_active=True):
        u = e.user
        if u and u != exclude_manager_if_current:
            choices.append((u.id, f"{e.full_name} ({e.get_employee_type_display()})"))
    return choices


class CertificateTemplateForm(forms.ModelForm):
    """Create/Edit certificate template."""

    class Meta:
        model = CertificateTemplate
        fields = ['name', 'template_type', 'body_template', 'is_active']
        widgets = {
            'body_template': forms.Textarea(attrs={'rows': 12}),
        }

    def __init__(self, *args, **kwargs):
        self.branch = kwargs.pop('branch', None)
        self.school = kwargs.pop('school', None)
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                'Template Details',
                'name',
                'template_type',
                'body_template',
                'is_active',
            ),
            FormActions(Submit('save', 'Save Template')),
        )

    def save(self, commit=True):
        obj = super().save(commit=False)
        if self.branch:
            obj.branch = self.branch
        if self.school:
            obj.school = self.school
        if commit:
            obj.save()
        return obj


class GenerateCertificateForm(forms.Form):
    """Step 1: Select template and recipient."""

    template = forms.ModelChoiceField(
        queryset=CertificateTemplate.objects.none(),
        label="Certificate Template",
        required=True,
    )
    # For student certs
    student = forms.ModelChoiceField(
        queryset=Student.objects.none(),
        label="Student",
        required=False,
    )
    # For employee certs - ChoiceField with (user_id, label)
    employee_id = forms.ChoiceField(
        label="Employee",
        required=False,
        choices=[],
    )

    def __init__(self, *args, **kwargs):
        self.branch = kwargs.pop('branch', None)
        self.template_type_filter = kwargs.pop('template_type_filter', None)
        self.request_user = kwargs.pop('request_user', None)
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Field('template'),
            Field('student'),
            Field('employee_id'),
            FormActions(Submit('submit', 'Continue', css_class='btn-primary')),
        )

        if self.branch:
            qs = CertificateTemplate.objects.filter(branch=self.branch, is_active=True)
            if self.template_type_filter:
                qs = qs.filter(template_type=self.template_type_filter)
            self.fields['template'].queryset = qs.order_by('template_type', 'name')

            students = Student.objects.filter(
                section__class_obj__branch=self.branch,
                is_active=True,
            ).select_related('section', 'section__class_obj').order_by('first_name', 'last_name')
            self.fields['student'].queryset = students

            # Manager cannot select themselves for experience cert
            exclude_self = self.request_user if (self.request_user and self.request_user.user_type == 'manager') else None
            emp_choices = [('', '---------')] + get_branch_staff_for_experience_cert(self.branch, exclude_self)
            self.fields['employee_id'].choices = emp_choices

    def clean(self):
        data = super().clean()
        template = data.get('template')
        student = data.get('student')
        employee_id = data.get('employee_id')

        if not template:
            return data

        is_student_cert = template.template_type in ('character', 'bonafide', 'fee_clearance', 'result', 'leaving')
        if is_student_cert:
            if not student:
                raise forms.ValidationError("Please select a student.")
        else:
            if not employee_id:
                raise forms.ValidationError("Please select an employee.")
        return data

    def get_employee_user(self):
        """Return User instance from employee_id selection."""
        uid = self.cleaned_data.get('employee_id')
        if not uid:
            return None
        try:
            return User.objects.get(pk=int(uid))
        except (ValueError, User.DoesNotExist):
            return None


class CertificateDataForm(forms.Form):
    """
    Dynamic form for certificate placeholder data.
    Fields are added based on template placeholders or a standard set.
    """

    # Common placeholders
    custom_text = forms.CharField(
        required=False,
        label="Additional Text / Remarks",
        widget=forms.Textarea(attrs={'rows': 3}),
    )
    issue_date = forms.DateField(
        required=True,
        label="Issue Date",
        widget=forms.DateInput(attrs={'type': 'date'}),
    )

    def __init__(self, *args, **kwargs):
        self.template = kwargs.pop('template', None)
        self.recipient = kwargs.pop('recipient', None)
        super().__init__(*args, **kwargs)

        from django.utils import timezone
        self.fields['issue_date'].initial = timezone.now().date()

        # Add standard fields based on recipient type
        if self.recipient:
            if hasattr(self.recipient, 'full_name'):  # Student
                self.fields['recipient_name'] = forms.CharField(
                    initial=self.recipient.full_name,
                    required=True,
                    label="Full Name",
                )
                if hasattr(self.recipient, 'father_name'):
                    self.fields['father_name'] = forms.CharField(
                        initial=getattr(self.recipient, 'father_name', ''),
                        required=False,
                        label="Father's Name",
                    )
                if hasattr(self.recipient, 'section'):
                    self.fields['class_name'] = forms.CharField(
                        initial=self.recipient.section.class_obj.name if self.recipient.section else '',
                        required=False,
                        label="Class",
                    )
                    self.fields['section_name'] = forms.CharField(
                        initial=self.recipient.section.name if self.recipient.section else '',
                        required=False,
                        label="Section",
                    )
                if hasattr(self.recipient, 'admission_number'):
                    self.fields['admission_number'] = forms.CharField(
                        initial=self.recipient.admission_number,
                        required=False,
                        label="Admission Number",
                    )
                if hasattr(self.recipient, 'enrollment_date'):
                    self.fields['enrollment_date'] = forms.DateField(
                        initial=self.recipient.enrollment_date,
                        required=False,
                        label="Enrollment Date",
                        widget=forms.DateInput(attrs={'type': 'date'}),
                    )
            else:
                # Employee (User)
                from staff.models import Teacher, Accountant, Employee
                from tenants.models import Branch
                joining = None
                designation = ''
                if hasattr(self.recipient, 'teacher_profile'):
                    try:
                        t = self.recipient.teacher_profile
                        joining = t.joining_date
                        designation = 'Teacher'
                    except Exception:
                        pass
                elif hasattr(self.recipient, 'accountant_profile'):
                    try:
                        a = self.recipient.accountant_profile
                        joining = a.joining_date
                        designation = 'Accountant'
                    except Exception:
                        pass
                elif hasattr(self.recipient, 'employee_profile'):
                    try:
                        e = self.recipient.employee_profile
                        joining = e.joining_date
                        designation = e.get_employee_type_display()
                    except Exception:
                        pass
                else:
                    try:
                        if self.recipient.managed_branch:
                            designation = 'Manager'
                    except Exception:
                        pass
                self.fields['recipient_name'] = forms.CharField(
                    initial=getattr(self.recipient, 'full_name', str(self.recipient)),
                    required=True,
                    label="Full Name",
                )
                self.fields['designation'] = forms.CharField(
                    initial=designation,
                    required=False,
                    label="Designation / Role",
                )
                self.fields['joining_date'] = forms.DateField(
                    initial=joining,
                    required=False,
                    label="Joining Date",
                    widget=forms.DateInput(attrs={'type': 'date'}),
                )
                self.fields['leaving_date'] = forms.DateField(
                    required=False,
                    label="Leaving Date",
                    widget=forms.DateInput(attrs={'type': 'date'}),
                )

        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Fieldset('Certificate Details', *[Field(name) for name in self.fields]),
            FormActions(Submit('generate', 'Generate & Save Certificate', css_class='btn-success')),
        )

    def get_context_dict(self):
        """Return a dict of placeholder name -> value for template rendering."""
        from django.utils import formats
        result = {}
        for key, val in self.cleaned_data.items():
            if val is None:
                result[key] = ''
            elif hasattr(val, 'strftime'):
                result[key] = formats.date_format(val, 'F d, Y')
            else:
                result[key] = str(val)
        if 'issue_date' in self.cleaned_data and self.cleaned_data['issue_date']:
            result['date'] = formats.date_format(self.cleaned_data['issue_date'], 'F d, Y')
            result['issued_date'] = result['date']
        return result
