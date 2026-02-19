from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone
from accounts.utils import branch_url
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, HTML, Fieldset
from crispy_forms.bootstrap import FormActions, TabHolder, Tab
from .models import Employee, Teacher, Accountant
from academics.models import Subject, Section
from tenants.models import Branch
import random
import string

User = get_user_model()

EMPLOYEE_TYPE_CHOICES = [
    ('teacher', 'Teacher'),
    ('accountant', 'Accountant'),
    ('guard', 'Guard'),
    ('clerk', 'Clerk'),
    ('cleaner', 'Cleaner'),
    ('driver', 'Driver'),
    ('other', 'Other'),
]

# Maps employee_type to the CustomUser user_type field
USER_TYPE_MAP = {
    'teacher': 'teacher',
    'accountant': 'accountant',
    'guard': 'employee',
    'clerk': 'employee',
    'cleaner': 'employee',
    'driver': 'employee',
    'other': 'employee',
}


def generate_temp_password(length=8):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))


def generate_email(first_name, last_name, employee_type, branch_code):
    clean_first = first_name.lower().replace(' ', '.')
    clean_last = last_name.lower().replace(' ', '.') if last_name else ''
    random_num = random.randint(100, 999)
    type_prefix = {
        'teacher': 'teacher', 'accountant': 'accountant', 'guard': 'guard',
        'clerk': 'clerk', 'cleaner': 'cleaner', 'driver': 'driver', 'other': 'staff',
    }.get(employee_type, 'staff')
    if clean_last:
        return f"{type_prefix}.{clean_first}.{clean_last}.{random_num}@school.edu"
    return f"{type_prefix}.{clean_first}.{random_num}@school.edu"


class StaffCreationStep1Form(forms.Form):
    """Step 1: Basic staff information."""

    first_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'placeholder': 'Enter first name', 'class': 'form-control form-control-lg'}),
        label="First Name *"
    )
    last_name = forms.CharField(
        max_length=100, required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Enter last name (optional)', 'class': 'form-control'}),
        label="Last Name"
    )
    phone_number = forms.CharField(
        max_length=17,
        widget=forms.TextInput(attrs={'placeholder': '+92 300 1234567', 'class': 'form-control'}),
        label="Phone Number *", help_text="Required. Enter with country code."
    )
    joining_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label="Joining Date *"
    )
    employee_type = forms.ChoiceField(
        choices=EMPLOYEE_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select form-select-lg', 'id': 'id_employee_type'}),
        label="Employee Type *"
    )

    # Optional fields
    father_name = forms.CharField(max_length=200, required=False, widget=forms.TextInput(attrs={'placeholder': "Father's/Husband's name", 'class': 'form-control'}), label="Father's Name")
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={'placeholder': 'email@address.com', 'class': 'form-control'}), label="Email")
    date_of_birth = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}), label="Date of Birth")
    gender = forms.ChoiceField(choices=[('', '-- Select --'), ('male', 'Male'), ('female', 'Female'), ('other', 'Other')], required=False, widget=forms.Select(attrs={'class': 'form-select'}), label="Gender")
    address = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 2, 'placeholder': 'Address', 'class': 'form-control'}), label="Address")
    city = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'placeholder': 'City', 'class': 'form-control'}), label="City")
    qualification = forms.CharField(max_length=200, required=False, widget=forms.TextInput(attrs={'placeholder': 'Qualification', 'class': 'form-control'}), label="Qualification")
    experience_years = forms.IntegerField(required=False, initial=0, widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 0}), label="Years of Experience")
    salary = forms.DecimalField(required=False, widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': 1000}), label="Salary (PKR)")
    cnic = forms.CharField(max_length=15, required=False, widget=forms.TextInput(attrs={'placeholder': '12345-1234567-1', 'class': 'form-control'}), label="CNIC")

    def __init__(self, *args, branch=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.branch = branch
        if not self.fields['joining_date'].initial:
            self.fields['joining_date'].initial = timezone.now().date()

        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_id = 'staff-step1-form'
        self.helper.layout = Layout(
            HTML("""<div class="alert alert-primary mb-4">
                <h5><i class="bi bi-person-plus"></i> Step 1 of 2: Staff Information</h5>
                <p class="mb-0">Enter basic staff details. Required fields are marked with *.</p>
            </div>"""),
            Fieldset('Required Information',
                Row(
                    Column('first_name', css_class='form-group mb-3 col-md-4'),
                    Column('last_name', css_class='form-group mb-3 col-md-4'),
                    Column('employee_type', css_class='form-group mb-3 col-md-4'),
                ),
                Row(
                    Column('phone_number', css_class='form-group mb-3 col-md-6'),
                    Column('joining_date', css_class='form-group mb-3 col-md-6'),
                ),
            ),
            Fieldset('Personal Information (Optional)',
                Row(Column('father_name', css_class='col-md-6 mb-3'), Column('date_of_birth', css_class='col-md-6 mb-3')),
                Row(Column('gender', css_class='col-md-4 mb-3'), Column('cnic', css_class='col-md-4 mb-3'), Column('email', css_class='col-md-4 mb-3')),
            ),
            Fieldset('Address & Employment (Optional)',
                'address',
                Row(Column('city', css_class='col-md-6 mb-3'), Column('qualification', css_class='col-md-6 mb-3')),
                Row(Column('experience_years', css_class='col-md-6 mb-3'), Column('salary', css_class='col-md-6 mb-3')),
            ),
            FormActions(Submit('next', 'Next \u2192 Create Account', css_class='btn btn-primary btn-lg w-100 py-3')),
        )

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number', '')
        phone = phone.replace(' ', '').replace('-', '')
        if phone and not phone.startswith('+'):
            phone = '+' + phone
        return phone


class StaffCreationStep2Form(forms.Form):
    """Step 2: Account credentials + type-specific fields (teacher subjects/incharge)."""

    def __init__(self, *args, staff_data=None, branch=None, request=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.staff_data = staff_data or {}
        self.branch = branch
        self.request = request

        first_name = self.staff_data.get('first_name', '')
        last_name = self.staff_data.get('last_name', '')
        employee_type = self.staff_data.get('employee_type', 'other')
        branch_code = self.staff_data.get('branch_code', 'SCH')

        self.fields['staff_email'] = forms.EmailField(
            required=True, initial=generate_email(first_name, last_name, employee_type, branch_code),
            widget=forms.EmailInput(attrs={'class': 'form-control form-control-lg'}), label="Staff Email (for login) *"
        )
        temp_pass = generate_temp_password()
        self.fields['staff_password'] = forms.CharField(
            required=True, initial=temp_pass,
            widget=forms.TextInput(attrs={'class': 'form-control'}), label="Password *"
        )
        self.fields['confirm_staff_password'] = forms.CharField(
            required=True, initial=temp_pass,
            widget=forms.TextInput(attrs={'class': 'form-control'}), label="Confirm Password *"
        )

        if employee_type == 'teacher':
            self.fields['specialization'] = forms.CharField(
                required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Mathematics'}),
                label="Specialization"
            )
            if branch:
                self.fields['subjects'] = forms.ModelMultipleChoiceField(
                    queryset=Subject.objects.filter(branch=branch, is_active=True),
                    required=False, widget=forms.CheckboxSelectMultiple(),
                    label="Subjects this teacher will teach"
                )
                self.fields['incharge_section'] = forms.ModelChoiceField(
                    queryset=Section.objects.filter(class_obj__branch=branch, is_active=True),
                    required=False, empty_label="-- None (not incharge) --",
                    widget=forms.Select(attrs={'class': 'form-select'}),
                    label="Incharge of Section (optional)"
                )

        if employee_type == 'accountant':
            self.fields['certification'] = forms.CharField(
                required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., CA, ACCA'}),
                label="Certification"
            )

        self.helper = FormHelper()
        self.helper.form_method = 'post'
        layout_fields = [
            HTML(f"""<div class="alert alert-success mb-4">
                <h5><i class="bi bi-person-check"></i> Step 2 of 2: Account Creation</h5>
                <p class="mb-0">Review and edit credentials. Employee Type: <strong>{self._type_display(employee_type)}</strong></p>
            </div>"""),
            HTML(f"""<div class="alert alert-info mb-3">
                <strong>Name:</strong> {first_name} {last_name}
            </div>"""),
            Fieldset('Staff Account Credentials',
                'staff_email',
                Row(Column('staff_password', css_class='col-md-6 mb-3'), Column('confirm_staff_password', css_class='col-md-6 mb-3')),
            ),
        ]

        if employee_type == 'teacher':
            teacher_fields = ['specialization']
            if 'subjects' in self.fields:
                teacher_fields.append('subjects')
            if 'incharge_section' in self.fields:
                teacher_fields.append('incharge_section')
            layout_fields.append(Fieldset('Teacher Details', *teacher_fields))

        if employee_type == 'accountant' and 'certification' in self.fields:
            layout_fields.append(Fieldset('Accountant Details', 'certification'))

        back_url = branch_url(self.request, 'staff:create_staff_wizard') if self.request else '#'
        layout_fields.append(HTML(f"""<div class="d-flex justify-content-between mt-3">
            <a href="{back_url}?back=1" class="btn btn-secondary btn-lg"><i class="bi bi-arrow-left"></i> Back</a>
        </div>"""))
        layout_fields.append(FormActions(Submit('finish', 'Finish \u2192 Create Staff Account', css_class='btn btn-success btn-lg w-100 py-3 mt-2')))
        self.helper.layout = Layout(*layout_fields)

    def _type_display(self, t):
        return dict(EMPLOYEE_TYPE_CHOICES).get(t, t)

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('staff_password')
        p2 = cleaned_data.get('confirm_staff_password')
        if p1 and p2 and p1 != p2:
            self.add_error('confirm_staff_password', 'Passwords do not match.')
        email = cleaned_data.get('staff_email')
        if email and User.objects.filter(email=email).exists():
            self.add_error('staff_email', 'This email is already in use.')
        return cleaned_data


FILTER_TYPE_CHOICES = [('', 'All Types'), ('manager', 'Manager')] + EMPLOYEE_TYPE_CHOICES


class StaffFilterForm(forms.Form):
    employee_type = forms.ChoiceField(choices=FILTER_TYPE_CHOICES, required=False, widget=forms.Select(attrs={'class': 'form-select', 'onchange': 'this.form.submit();'}))
    status_filter = forms.ChoiceField(choices=[('', 'All Status'), ('active', 'Active'), ('inactive', 'Inactive')], required=False, widget=forms.Select(attrs={'class': 'form-select', 'onchange': 'this.form.submit();'}))
    branch_filter = forms.ModelChoiceField(queryset=None, required=False, empty_label="All Branches", widget=forms.Select(attrs={'class': 'form-select', 'onchange': 'this.form.submit();'}))
    search = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Search by name, ID, phone...'}))

    def __init__(self, *args, school=None, **kwargs):
        super().__init__(*args, **kwargs)
        if school:
            self.fields['branch_filter'].queryset = Branch.objects.filter(school=school, is_active=True)
        else:
            self.fields['branch_filter'].queryset = Branch.objects.none()


class EmployeeEditForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = [
            'first_name', 'last_name', 'father_name', 'phone_number',
            'alternate_phone', 'email', 'date_of_birth', 'gender',
            'address', 'city', 'employee_type', 'qualification',
            'experience_years', 'salary', 'cnic', 'profile_picture', 'is_active'
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'address': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_enctype = 'multipart/form-data'
        self.helper.layout = Layout(
            TabHolder(
                Tab('Basic Info',
                    Row(Column('first_name', css_class='col-md-4 mb-3'), Column('last_name', css_class='col-md-4 mb-3'), Column('employee_type', css_class='col-md-4 mb-3')),
                    Row(Column('father_name', css_class='col-md-6 mb-3'), Column('cnic', css_class='col-md-6 mb-3')),
                ),
                Tab('Contact',
                    Row(Column('phone_number', css_class='col-md-6 mb-3'), Column('alternate_phone', css_class='col-md-6 mb-3')),
                    'email', 'address', 'city',
                ),
                Tab('Personal',
                    Row(Column('date_of_birth', css_class='col-md-4 mb-3'), Column('gender', css_class='col-md-4 mb-3'), Column('profile_picture', css_class='col-md-4 mb-3')),
                ),
                Tab('Employment',
                    Row(Column('qualification', css_class='col-md-6 mb-3'), Column('experience_years', css_class='col-md-6 mb-3')),
                    'salary', 'is_active',
                ),
            ),
            FormActions(Submit('submit', 'Update Employee', css_class='btn btn-primary')),
        )


class TeacherEditForm(forms.ModelForm):
    full_name = forms.CharField(max_length=255, label="Full Name")
    phone_number = forms.CharField(max_length=17, label="Phone Number")
    email = forms.EmailField(label="Email")

    class Meta:
        model = Teacher
        fields = ['specialization', 'qualification', 'experience_years', 'salary', 'subjects', 'incharge_section', 'is_active']
        widgets = {
            'subjects': forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, branch=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.branch = branch
        if self.instance and self.instance.user:
            self.fields['full_name'].initial = self.instance.user.full_name
            self.fields['phone_number'].initial = self.instance.user.phone_number
            self.fields['email'].initial = self.instance.user.email

        if branch:
            self.fields['subjects'].queryset = Subject.objects.filter(branch=branch, is_active=True)
            self.fields['incharge_section'].queryset = Section.objects.filter(class_obj__branch=branch, is_active=True)
        elif self.instance and self.instance.pk:
            self.fields['subjects'].queryset = Subject.objects.filter(branch=self.instance.branch, is_active=True)
            self.fields['incharge_section'].queryset = Section.objects.filter(class_obj__branch=self.instance.branch, is_active=True)

        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Row(Column('full_name', css_class='col-md-4 mb-3'), Column('phone_number', css_class='col-md-4 mb-3'), Column('email', css_class='col-md-4 mb-3')),
            Row(Column('specialization', css_class='col-md-6 mb-3'), Column('qualification', css_class='col-md-6 mb-3')),
            Row(Column('experience_years', css_class='col-md-6 mb-3'), Column('salary', css_class='col-md-6 mb-3')),
            'subjects',
            'incharge_section',
            'is_active',
            FormActions(Submit('submit', 'Update Teacher', css_class='btn btn-primary')),
        )

    def save(self, commit=True):
        teacher = super().save(commit=False)
        if teacher.user:
            teacher.user.full_name = self.cleaned_data['full_name']
            teacher.user.phone_number = self.cleaned_data['phone_number']
            teacher.user.email = self.cleaned_data['email']
            if commit:
                teacher.user.save()
        if commit:
            teacher.save()
            self.save_m2m()
        return teacher


class AccountantEditForm(forms.ModelForm):
    full_name = forms.CharField(max_length=255, label="Full Name")
    phone_number = forms.CharField(max_length=17, label="Phone Number")
    email = forms.EmailField(label="Email")

    class Meta:
        model = Accountant
        fields = ['qualification', 'certification', 'experience_years', 'salary', 'is_active']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        if self.instance and self.instance.user:
            self.fields['full_name'].initial = self.instance.user.full_name
            self.fields['phone_number'].initial = self.instance.user.phone_number
            self.fields['email'].initial = self.instance.user.email

        self.helper.layout = Layout(
            Row(Column('full_name', css_class='col-md-4 mb-3'), Column('phone_number', css_class='col-md-4 mb-3'), Column('email', css_class='col-md-4 mb-3')),
            Row(Column('qualification', css_class='col-md-6 mb-3'), Column('certification', css_class='col-md-6 mb-3')),
            Row(Column('experience_years', css_class='col-md-6 mb-3'), Column('salary', css_class='col-md-6 mb-3')),
            'is_active',
            FormActions(Submit('submit', 'Update Accountant', css_class='btn btn-primary')),
        )

    def save(self, commit=True):
        accountant = super().save(commit=False)
        if accountant.user:
            accountant.user.full_name = self.cleaned_data['full_name']
            accountant.user.phone_number = self.cleaned_data['phone_number']
            accountant.user.email = self.cleaned_data['email']
            if commit:
                accountant.user.save()
        if commit:
            accountant.save()
        return accountant


class ChangeCredentialsForm(forms.Form):
    """Allows principal/manager to change a user's login email and password."""

    new_email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control form-control-lg'}),
        label="New Email (login)",
    )
    new_password = forms.CharField(
        required=False, min_length=6,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label="New Password",
        help_text="Leave blank to keep the current password."
    )
    confirm_password = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label="Confirm Password",
    )

    def __init__(self, *args, target_user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.target_user = target_user
        if target_user:
            self.fields['new_email'].initial = target_user.email

        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Fieldset('Login Credentials',
                'new_email',
                Row(Column('new_password', css_class='col-md-6 mb-3'), Column('confirm_password', css_class='col-md-6 mb-3')),
            ),
            FormActions(Submit('submit', 'Update Credentials', css_class='btn btn-warning btn-lg')),
        )

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('new_password', '')
        p2 = cleaned.get('confirm_password', '')
        if p1 and p1 != p2:
            self.add_error('confirm_password', 'Passwords do not match.')
        new_email = cleaned.get('new_email', '')
        if new_email and self.target_user and new_email != self.target_user.email:
            if User.objects.filter(email=new_email).exclude(id=self.target_user.id).exists():
                self.add_error('new_email', 'This email is already in use by another account.')
        return cleaned


class ProfileEditForm(forms.ModelForm):
    """For principal/manager to edit their own profile."""

    class Meta:
        model = User
        fields = ['full_name', 'phone_number', 'city']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Row(Column('full_name', css_class='col-md-6 mb-3'), Column('phone_number', css_class='col-md-6 mb-3')),
            'city',
            FormActions(Submit('submit', 'Update Profile', css_class='btn btn-primary btn-lg')),
        )
