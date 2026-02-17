from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, HTML, Fieldset
from crispy_forms.bootstrap import FormActions
from .models import Class, Section, Subject, SectionSubject
from django.core.exceptions import ValidationError

class ClassCreationStep1Form(forms.Form):
    """
    Step 1: Create class with number of sections.
    """
    
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g., Grade 1, Class 5, O-Level',
            'class': 'form-control form-control-lg'
        }),
        label="Class Name"
    )
    
    numeric_level = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={
            'placeholder': 'e.g., 1, 2, 3...',
            'class': 'form-control'
        }),
        label="Numeric Level",
        help_text="Optional: Enter the grade number for sorting"
    )
    
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': 'Optional description for this class'
        }),
        label="Description"
    )
    
    number_of_sections = forms.IntegerField(
        min_value=1,
        max_value=20,
        initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 1,
            'max': 20
        }),
        label="Number of Sections",
        help_text="How many sections does this class have? (Max: 20)"
    )
    
    def __init__(self, *args, **kwargs):
        self.branch = kwargs.pop('branch', None)
        super().__init__(*args, **kwargs)
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'form-horizontal'
        
        self.helper.layout = Layout(
            HTML("""
                <div class="alert alert-primary mb-4">
                    <h5><i class="bi bi-diagram-3"></i> Step 1 of 2: Class Information</h5>
                    <p class="mb-0">Create a new class and specify how many sections it has.</p>
                </div>
            """),
            
            Fieldset(
                'Class Details',
                Row(
                    Column('name', css_class='form-group mb-3 col-md-8'),
                    Column('numeric_level', css_class='form-group mb-3 col-md-4'),
                ),
                'description',
            ),
            
            Fieldset(
                'Sections Setup',
                'number_of_sections',
                HTML("""
                    <div class="alert alert-info mt-2">
                        <small><i class="bi bi-info-circle"></i> You'll add section names in the next step.</small>
                    </div>
                """)
            ),
            
            FormActions(
                Submit('next', 'Next → Add Sections', css_class='btn btn-primary btn-lg w-100 py-3'),
            )
        )
    
    def clean_name(self):
        """Validate that class name is unique within branch."""
        name = self.cleaned_data.get('name')
        if self.branch and Class.objects.filter(name=name, branch=self.branch).exists():
            raise ValidationError(f"A class with name '{name}' already exists in this branch.")
        return name


class SectionCreationStep2Form(forms.Form):
    """
    Step 2: Add names for each section.
    """
    
    def __init__(self, *args, num_sections=1, **kwargs):
        super().__init__(*args, **kwargs)
        self.num_sections = num_sections
        
        for i in range(1, num_sections + 1):
            # Section name field
            self.fields[f'section_{i}_name'] = forms.CharField(
                max_length=50,
                required=True,
                widget=forms.TextInput(attrs={
                    'placeholder': f'Section {i} Name (e.g., A, B, C, Blue)',
                    'class': 'form-control form-control-lg'
                }),
                label=f'Section {i} Name'
            )
            
            # Section capacity field
            self.fields[f'section_{i}_capacity'] = forms.IntegerField(
                required=False,
                initial=30,
                widget=forms.NumberInput(attrs={
                    'placeholder': 'Student capacity',
                    'class': 'form-control',
                    'min': 1,
                    'max': 100
                }),
                label=f'Section {i} Capacity'
            )
            
            # Section room number
            self.fields[f'section_{i}_room'] = forms.CharField(
                max_length=20,
                required=False,
                widget=forms.TextInput(attrs={
                    'placeholder': 'Room number (optional)',
                    'class': 'form-control'
                }),
                label=f'Section {i} Room'
            )
    
    def clean(self):
        """Validate that section names are unique."""
        cleaned_data = super().clean()
        section_names = []
        
        for i in range(1, self.num_sections + 1):
            name = cleaned_data.get(f'section_{i}_name')
            if name:
                if name in section_names:
                    self.add_error(
                        f'section_{i}_name',
                        f'Section {i} name must be unique. You already have a section named "{name}".'
                    )
                section_names.append(name)
        
        return cleaned_data


class SubjectForm(forms.ModelForm):
    """
    Form for creating/editing subjects.
    """
    
    class Meta:
        model = Subject
        fields = ['name', 'code', 'subject_type', 'description', 
                 'total_marks', 'pass_marks', 'is_optional']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'e.g., Mathematics'}),
            'code': forms.TextInput(attrs={'placeholder': 'e.g., MATH-101'}),
            'description': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Subject description'}),
            'total_marks': forms.NumberInput(attrs={'min': 1, 'max': 200}),
            'pass_marks': forms.NumberInput(attrs={'min': 1}),
        }
    
    def __init__(self, *args, **kwargs):
        self.branch = kwargs.pop('branch', None)
        super().__init__(*args, **kwargs)
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Row(
                Column('name', css_class='form-group mb-3 col-md-6'),
                Column('code', css_class='form-group mb-3 col-md-6'),
            ),
            Row(
                Column('subject_type', css_class='form-group mb-3 col-md-6'),
                Column('is_optional', css_class='form-group mb-3 col-md-6'),
            ),
            'description',
            Row(
                Column('total_marks', css_class='form-group mb-3 col-md-6'),
                Column('pass_marks', css_class='form-group mb-3 col-md-6'),
            ),
            FormActions(
                Submit('submit', 'Save Subject', css_class='btn btn-primary'),
            )
        )
    
    def clean_code(self):
        """Validate subject code uniqueness within branch."""
        code = self.cleaned_data.get('code')
        if self.branch:
            # Check if code exists in this branch
            existing = Subject.objects.filter(code=code, branch=self.branch)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise ValidationError(f"Subject with code '{code}' already exists in this branch.")
        return code
    
    def clean(self):
        """Validate pass marks vs total marks."""
        cleaned_data = super().clean()
        total = cleaned_data.get('total_marks')
        pass_marks = cleaned_data.get('pass_marks')
        
        if total and pass_marks and pass_marks > total:
            self.add_error('pass_marks', 'Passing marks cannot be greater than total marks.')
        
        return cleaned_data
    
    def save(self, commit=True):
        """Save subject with branch."""
        subject = super().save(commit=False)
        if self.branch:
            subject.branch = self.branch
        if commit:
            subject.save()
        return subject


class SectionSubjectAssignmentForm(forms.Form):
    """
    Form for assigning subjects to sections.
    """
    
    def __init__(self, *args, section=None, available_subjects=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.section = section
        
        if available_subjects:
            for subject in available_subjects:
                self.fields[f'subject_{subject.id}'] = forms.BooleanField(
                    required=False,
                    initial=False,
                    label=subject.name,
                    widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
                )
                
                # Teacher assignment for this subject
                self.fields[f'teacher_{subject.id}'] = forms.ModelChoiceField(
                    required=False,
                    queryset=self.get_teachers(),
                    empty_label="-- Select Teacher --",
                    widget=forms.Select(attrs={'class': 'form-select'}),
                    label=f"Teacher for {subject.name}"
                )
    
    def get_teachers(self):
        """Get available teachers in this branch (from UserRole or user_type)."""
        from django.contrib.auth import get_user_model
        from django.db.models import Q
        from rbac.models import UserRole
        User = get_user_model()
        if not self.section:
            return User.objects.none()
        branch = self.section.branch
        teacher_ids = UserRole.objects.filter(
            role__name='teacher', is_active=True
        ).filter(Q(branch=branch) | Q(branch__isnull=True)).values_list('user_id', flat=True)
        if teacher_ids:
            return User.objects.filter(pk__in=teacher_ids, is_active=True).order_by('full_name')
        return User.objects.filter(user_type='teacher', is_active=True).order_by('full_name')

    def save(self, assigned_by=None):
        """Save subject assignments."""
        if not self.section:
            return []

        assignments = []
        for name, value in self.cleaned_data.items():
            if name.startswith('subject_') and value:
                subject_id = int(name.split('_')[1])
                teacher = self.cleaned_data.get(f'teacher_{subject_id}')
                
                assignment, created = SectionSubject.objects.update_or_create(
                    section=self.section,
                    subject_id=subject_id,
                    defaults={
                        'teacher': teacher,
                        'assigned_by': assigned_by,
                        'is_active': True
                    }
                )
                assignments.append(assignment)
        
        return assignments


class ClassEditForm(forms.ModelForm):
    """
    Form for editing an existing class (name, numeric_level, description only).
    Sections are managed separately.
    """
    class Meta:
        model = Class
        fields = ['name', 'numeric_level', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Grade 1'}),
            'numeric_level': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '1'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.branch = kwargs.pop('branch', None)
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_tag = False  # Template provides its own form tag and buttons
        self.helper.layout = Layout('name', 'numeric_level', 'description', 'is_active')
    
    def clean_name(self):
        """Validate that class name is unique within branch."""
        name = self.cleaned_data.get('name')
        branch = self.branch or (self.instance.branch if self.instance else None)
        if branch and self.instance:
            if Class.objects.filter(name=name, branch=branch).exclude(pk=self.instance.pk).exists():
                raise ValidationError(f"A class with name '{name}' already exists in this branch.")
        return name


class SectionEditForm(forms.ModelForm):
    """Form for editing section details."""

    class Meta:
        model = Section
        fields = ['name', 'capacity', 'room_number', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'room_number': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_tag = False
        self.helper.layout = Layout('name', 'capacity', 'room_number', 'description', 'is_active')


class SectionFilterForm(forms.Form):
    """
    Form for filtering sections by class.
    """
    
    class_filter = forms.ModelChoiceField(
        queryset=None,
        required=False,
        empty_label="All Classes",
        widget=forms.Select(attrs={'class': 'form-select', 'onchange': 'this.form.submit();'})
    )
    
    def __init__(self, *args, branch=None, **kwargs):
        super().__init__(*args, **kwargs)
        if branch:
            self.fields['class_filter'].queryset = Class.objects.filter(
                branch=branch, is_active=True
            )