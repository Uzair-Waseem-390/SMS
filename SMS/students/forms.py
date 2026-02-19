from django import forms
from django.contrib.auth import get_user_model
from django.urls import reverse
from accounts.utils import branch_url
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, HTML, Fieldset
from crispy_forms.bootstrap import FormActions, TabHolder, Tab
from .models import Student, Parent
from academics.models import Class, Section
import random
import string

User = get_user_model()

def generate_temp_password(length=8):
    """Generate a temporary password."""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for i in range(length))

def generate_email(name, role, branch_code):
    """Generate email based on name and role."""
    # Clean name and create email
    clean_name = name.lower().replace(' ', '.')
    random_num = random.randint(100, 999)
    return f"{role}.{clean_name}.{random_num}@school.edu"


class StudentCreationStep1Form(forms.Form):
    """
    Step 1: Basic student information and class/section selection.
    """
    
    # Required fields
    first_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter student first name',
            'class': 'form-control form-control-lg'
        }),
        label="Student First Name"
    )
    
    last_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter student last name',
            'class': 'form-control'
        }),
        label="Student Last Name"
    )
    
    father_name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'placeholder': "Enter father's full name",
            'class': 'form-control'
        }),
        label="Father's Name"
    )
    
    # Class and Section (dynamic)
    class_choice = forms.ModelChoiceField(
        queryset=None,
        empty_label="-- Select Class --",
        widget=forms.Select(attrs={
            'class': 'form-select form-select-lg',
            'id': 'id_class_choice'
        }),
        label="Class"
    )
    
    section_choice = forms.ModelChoiceField(
        queryset=None,
        empty_label="-- Select Section --",
        widget=forms.Select(attrs={
            'class': 'form-select form-select-lg',
            'id': 'id_section_choice'
        }),
        label="Section"
    )
    
    # Optional fields
    mother_name = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': "Enter mother's name (optional)",
            'class': 'form-control'
        }),
        label="Mother's Name"
    )
    
    date_of_birth = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        }),
        label="Date of Birth"
    )
    
    gender = forms.ChoiceField(
        choices=[('', '-- Select Gender --')] + Student.GENDER_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Gender"
    )
    
    phone_number = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': '+92 300 1234567',
            'class': 'form-control'
        }),
        label="Phone Number",
        help_text="Optional: Student's personal phone"
    )
    
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'placeholder': 'student@email.com (optional)',
            'class': 'form-control'
        }),
        label="Email Address"
    )
    
    address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': 'Residential address (optional)',
            'class': 'form-control'
        }),
        label="Address"
    )

    scholarship = forms.ModelChoiceField(
        queryset=None,
        required=False,
        empty_label="-- No Scholarship --",
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Scholarship"
    )
    
    def __init__(self, *args, branch=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.branch = branch
        
        # Set class queryset (classes in current branch)
        if branch:
            self.fields['class_choice'].queryset = Class.objects.filter(
                branch=branch, is_active=True
            ).order_by('numeric_level', 'name')
            from finance.models import Scholarship as ScholarshipModel
            self.fields['scholarship'].queryset = ScholarshipModel.objects.filter(
                branch=branch, is_active=True
            )
        else:
            from finance.models import Scholarship as ScholarshipModel
            self.fields['scholarship'].queryset = ScholarshipModel.objects.none()
        
        # For GET (initial load) keep sections empty; for POST bind, populate based on selected class
        self.fields['section_choice'].queryset = Section.objects.none()
        if 'class_choice' in self.data:
            try:
                class_id = int(self.data.get('class_choice'))
                self.fields['section_choice'].queryset = Section.objects.filter(
                    class_obj_id=class_id, class_obj__branch=branch, is_active=True
                ).order_by('name')
            except (TypeError, ValueError):
                pass
        elif self.initial.get('class_choice'):
            class_obj = self.initial['class_choice']
            self.fields['section_choice'].queryset = Section.objects.filter(
                class_obj=class_obj, class_obj__branch=branch, is_active=True
            ).order_by('name')
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_id = 'student-step1-form'
        
        self.helper.layout = Layout(
            HTML("""
                <div class="alert alert-primary mb-4">
                    <h5><i class="bi bi-person-plus"></i> Step 1 of 2: Student Information</h5>
                    <p class="mb-0">Enter basic student details and assign to a class section.</p>
                </div>
            """),
            
            Fieldset(
                'Required Information',
                Row(
                    Column('first_name', css_class='form-group mb-3 col-md-6'),
                    Column('last_name', css_class='form-group mb-3 col-md-6'),
                ),
                'father_name',
            ),
            
            Fieldset(
                'Class Assignment',
                Row(
                    Column('class_choice', css_class='form-group mb-3 col-md-6'),
                    Column('section_choice', css_class='form-group mb-3 col-md-6'),
                ),
            ),
            
            Fieldset(
                'Optional Information',
                Row(
                    Column('mother_name', css_class='form-group mb-3 col-md-6'),
                    Column('date_of_birth', css_class='form-group mb-3 col-md-6'),
                ),
                Row(
                    Column('gender', css_class='form-group mb-3 col-md-4'),
                    Column('phone_number', css_class='form-group mb-3 col-md-4'),
                    Column('email', css_class='form-group mb-3 col-md-4'),
                ),
                'address',
                'scholarship',
            ),
            
            FormActions(
                Submit('next', 'Next → Create Accounts', css_class='btn btn-primary btn-lg w-100 py-3'),
            )
        )
    
    def clean(self):
        cleaned_data = super().clean()
        class_obj = cleaned_data.get('class_choice')
        section = cleaned_data.get('section_choice')
        
        if class_obj and section and section.class_obj != class_obj:
            self.add_error('section_choice', 'Selected section does not belong to the selected class.')
        
        return cleaned_data


class StudentCreationStep2Form(forms.Form):
    """
    Step 2: Review and edit student/parent credentials.
    """
    
    def __init__(self, *args, student_data=None, request=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.student_data = student_data or {}
        self.request = request
        
        # Student Account Fields
        self.fields['student_email'] = forms.EmailField(
            required=True,
            initial=self.generate_student_email(),
            widget=forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'student@email.com'
            }),
            label="Student Email (for login)"
        )
        
        self.fields['student_password'] = forms.CharField(
            required=True,
            initial=generate_temp_password(),
            widget=forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Password'
            }),
            label="Student Password",
            help_text="Student will use this password to login"
        )
        
        self.fields['confirm_student_password'] = forms.CharField(
            required=True,
            initial=self.fields['student_password'].initial,
            widget=forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Confirm password'
            }),
            label="Confirm Student Password"
        )
        
        # Parent Account Fields
        parent_name = self.student_data.get('father_name', 'Parent')
        self.fields['parent_first_name'] = forms.CharField(
            required=True,
            initial=parent_name.split()[0] if parent_name else 'Parent',
            widget=forms.TextInput(attrs={'class': 'form-control'}),
            label="Parent First Name"
        )
        
        self.fields['parent_last_name'] = forms.CharField(
            required=True,
            initial=parent_name.split()[-1] if len(parent_name.split()) > 1 else 'Account',
            widget=forms.TextInput(attrs={'class': 'form-control'}),
            label="Parent Last Name"
        )
        
        self.fields['parent_email'] = forms.EmailField(
            required=True,
            initial=self.generate_parent_email(),
            widget=forms.EmailInput(attrs={'class': 'form-control'}),
            label="Parent Email (for login)"
        )
        
        self.fields['parent_password'] = forms.CharField(
            required=True,
            initial=generate_temp_password(),
            widget=forms.TextInput(attrs={'class': 'form-control'}),
            label="Parent Password"
        )
        
        self.fields['confirm_parent_password'] = forms.CharField(
            required=True,
            initial=self.fields['parent_password'].initial,
            widget=forms.TextInput(attrs={'class': 'form-control'}),
            label="Confirm Parent Password"
        )
        
        self.fields['parent_phone'] = forms.CharField(
            required=True,
            initial=self.student_data.get('phone_number', ''),
            widget=forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+92 300 1234567'
            }),
            label="Parent Phone Number"
        )
        
        self.fields['parent_relationship'] = forms.ChoiceField(
            choices=Parent.RELATIONSHIP_CHOICES,
            initial='father',
            widget=forms.Select(attrs={'class': 'form-select'}),
            label="Relationship to Student"
        )

        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            HTML("""
                <div class="alert alert-success mb-4">
                    <h5><i class="bi bi-person-check"></i> Step 2 of 2: Account Creation</h5>
                    <p class="mb-0">Review and edit the automatically generated credentials.</p>
                </div>
            """),
            
            Fieldset(
                'Student Account Details',
                Row(
                    Column('student_email', css_class='form-group mb-3 col-md-6'),
                    Column('student_password', css_class='form-group mb-3 col-md-3'),
                    Column('confirm_student_password', css_class='form-group mb-3 col-md-3'),
                ),
            ),
            
            HTML("<hr class='my-4'>"),
            
            Fieldset(
                'Parent Account Details',
                Row(
                    Column('parent_first_name', css_class='form-group mb-3 col-md-4'),
                    Column('parent_last_name', css_class='form-group mb-3 col-md-4'),
                    Column('parent_relationship', css_class='form-group mb-3 col-md-4'),
                ),
                Row(
                    Column('parent_email', css_class='form-group mb-3 col-md-6'),
                    Column('parent_phone', css_class='form-group mb-3 col-md-6'),
                ),
                Row(
                    Column('parent_password', css_class='form-group mb-3 col-md-6'),
                    Column('confirm_parent_password', css_class='form-group mb-3 col-md-6'),
                ),
            ),
            
            HTML(self._back_link_html()),
            FormActions(
                Submit('finish', 'Finish → Create Student & Parent',
                       css_class='btn btn-success btn-lg w-100 py-3'),
            )
        )

    def _back_link_html(self):
        """Back link with school/branch-scoped URL."""
        if self.request:
            url = branch_url(self.request, 'students:create_student_wizard')
        else:
            url = '#'
        return f'<div class="d-flex justify-content-between mt-4"><a href="{url}?back=1" class="btn btn-secondary btn-lg"><i class="bi bi-arrow-left"></i> Back</a></div>'

    def generate_student_email(self):
        """Generate email for student."""
        first = self.student_data.get('first_name', 'student').lower()
        last = self.student_data.get('last_name', '').lower()
        section = self.student_data.get('section', '')
        random_num = random.randint(100, 999)
        
        if last:
            return f"{first}.{last}.{random_num}@student.edu"
        return f"student.{first}.{random_num}@student.edu"
    
    def generate_parent_email(self):
        """Generate email for parent."""
        father = self.student_data.get('father_name', 'parent').lower().replace(' ', '.')
        random_num = random.randint(100, 999)
        return f"parent.{father}.{random_num}@school.edu"
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validate student passwords
        student_pass = cleaned_data.get('student_password')
        student_confirm = cleaned_data.get('confirm_student_password')
        if student_pass and student_confirm and student_pass != student_confirm:
            self.add_error('confirm_student_password', 'Student passwords do not match.')
        
        # Validate parent passwords
        parent_pass = cleaned_data.get('parent_password')
        parent_confirm = cleaned_data.get('confirm_parent_password')
        if parent_pass and parent_confirm and parent_pass != parent_confirm:
            self.add_error('confirm_parent_password', 'Parent passwords do not match.')
        
        # Check if emails are unique
        student_email = cleaned_data.get('student_email')
        parent_email = cleaned_data.get('parent_email')
        
        if student_email and User.objects.filter(email=student_email).exists():
            self.add_error('student_email', 'This email is already in use.')
        
        if parent_email and User.objects.filter(email=parent_email).exists():
            self.add_error('parent_email', 'This email is already in use.')
        
        return cleaned_data


class StudentFilterForm(forms.Form):
    """
    Form for filtering students list.
    """
    
    class_filter = forms.ModelChoiceField(
        queryset=None,
        required=False,
        empty_label="All Classes",
        widget=forms.Select(attrs={
            'class': 'form-select',
            'onchange': 'this.form.submit();'
        })
    )
    
    section_filter = forms.ModelChoiceField(
        queryset=None,
        required=False,
        empty_label="All Sections",
        widget=forms.Select(attrs={
            'class': 'form-select',
            'onchange': 'this.form.submit();'
        })
    )
    
    status_filter = forms.ChoiceField(
        choices=[('', 'All Status'), ('active', 'Active'), ('inactive', 'Inactive')],
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'onchange': 'this.form.submit();'
        })
    )
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by name, admission #...'
        })
    )
    
    def __init__(self, *args, branch=None, **kwargs):
        super().__init__(*args, **kwargs)
        if branch:
            self.fields['class_filter'].queryset = Class.objects.filter(
                branch=branch, is_active=True
            )
            self.fields['section_filter'].queryset = Section.objects.filter(
                class_obj__branch=branch, is_active=True
            )


class StudentEditForm(forms.ModelForm):
    """
    Form for editing student details.
    """
    
    class Meta:
        model = Student
        fields = [
            'first_name', 'last_name', 'father_name', 'mother_name',
            'date_of_birth', 'gender', 'phone_number', 'email',
            'alternate_phone', 'address', 'city', 'postal_code',
            'blood_group', 'medical_conditions', 'emergency_contact_name',
            'emergency_contact_phone', 'profile_picture', 'roll_number',
            'scholarship', 'is_active'
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'medical_conditions': forms.Textarea(attrs={'rows': 3}),
            'address': forms.Textarea(attrs={'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_enctype = 'multipart/form-data'
        
        self.helper.layout = Layout(
            TabHolder(
                Tab(
                    'Basic Information',
                    Row(
                        Column('first_name', css_class='form-group mb-3 col-md-4'),
                        Column('last_name', css_class='form-group mb-3 col-md-4'),
                        Column('roll_number', css_class='form-group mb-3 col-md-4'),
                    ),
                    Row(
                        Column('father_name', css_class='form-group mb-3 col-md-6'),
                        Column('mother_name', css_class='form-group mb-3 col-md-6'),
                    ),
                    Row(
                        Column('date_of_birth', css_class='form-group mb-3 col-md-4'),
                        Column('gender', css_class='form-group mb-3 col-md-4'),
                        Column('blood_group', css_class='form-group mb-3 col-md-4'),
                    ),
                ),
                Tab(
                    'Contact Information',
                    Row(
                        Column('phone_number', css_class='form-group mb-3 col-md-6'),
                        Column('alternate_phone', css_class='form-group mb-3 col-md-6'),
                    ),
                    'email',
                    'address',
                    Row(
                        Column('city', css_class='form-group mb-3 col-md-6'),
                        Column('postal_code', css_class='form-group mb-3 col-md-6'),
                    ),
                ),
                Tab(
                    'Emergency & Medical',
                    Row(
                        Column('emergency_contact_name', css_class='form-group mb-3 col-md-6'),
                        Column('emergency_contact_phone', css_class='form-group mb-3 col-md-6'),
                    ),
                    'medical_conditions',
                ),
                Tab(
                    'Profile & Status',
                    'profile_picture',
                    'is_active',
                ),
            ),
            FormActions(
                Submit('submit', 'Update Student', css_class='btn btn-primary'),
            )
        )


class ParentEditForm(forms.ModelForm):
    """
    Form for editing parent details.
    """
    
    class Meta:
        model = Parent
        fields = [
            'first_name', 'last_name', 'relationship', 'phone_number',
            'alternate_phone', 'email', 'occupation', 'qualification',
            'address', 'city', 'profile_picture', 'is_active'
        ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_enctype = 'multipart/form-data'
        
        self.helper.layout = Layout(
            Row(
                Column('first_name', css_class='form-group mb-3 col-md-4'),
                Column('last_name', css_class='form-group mb-3 col-md-4'),
                Column('relationship', css_class='form-group mb-3 col-md-4'),
            ),
            Row(
                Column('phone_number', css_class='form-group mb-3 col-md-6'),
                Column('alternate_phone', css_class='form-group mb-3 col-md-6'),
            ),
            'email',
            Row(
                Column('occupation', css_class='form-group mb-3 col-md-6'),
                Column('qualification', css_class='form-group mb-3 col-md-6'),
            ),
            'address',
            'city',
            'profile_picture',
            'is_active',
            FormActions(
                Submit('submit', 'Update Parent', css_class='btn btn-primary'),
            )
        )