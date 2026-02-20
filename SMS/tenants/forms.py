from django import forms
from django.core.validators import MinValueValidator
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, HTML, Fieldset
from crispy_forms.bootstrap import FormActions, TabHolder, Tab
from .models import SchoolTenant, Branch
import re

class SchoolSetupStep1Form(forms.ModelForm):
    """
    Step 1: Basic School Information
    First page where principal enters school details and number of branches.
    """
    
    number_of_branches = forms.IntegerField(
        min_value=1,
        max_value=10,
        initial=1,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        label="Number of Branches",
        help_text="How many branches does your school have? (Max: 10)"
    )
    
    class Meta:
        model = SchoolTenant
        fields = ['name', 'city', 'address', 'phone', 'email', 'established_year', 'registration_number']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'e.g., Springfield International School'}),
            'city': forms.TextInput(attrs={'placeholder': 'e.g., Lahore'}),
            'address': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Full address with street, area, etc.'}),
            'phone': forms.TextInput(attrs={'placeholder': '+92 300 1234567'}),
            'email': forms.EmailInput(attrs={'placeholder': 'principal@school.com'}),
            'established_year': forms.NumberInput(attrs={'placeholder': 'e.g., 2005'}),
            'registration_number': forms.TextInput(attrs={'placeholder': 'Optional registration number'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-12 fw-bold'
        self.helper.field_class = 'col-lg-12'
        
        self.helper.layout = Layout(
            HTML("""
                <div class="alert alert-primary mb-4">
                    <h5><i class="bi bi-building"></i> Step 1 of 3: School Information</h5>
                    <p class="mb-0">Tell us about your school to get started.</p>
                </div>
            """),
            
            Fieldset(
                'School Details',
                Row(
                    Column('name', css_class='form-group mb-3 col-md-12'),
                    css_class='row'
                ),
                Row(
                    Column('city', css_class='form-group mb-3 col-md-6'),
                    Column('established_year', css_class='form-group mb-3 col-md-6'),
                    css_class='row'
                ),
                'address',
                Row(
                    Column('phone', css_class='form-group mb-3 col-md-6'),
                    Column('email', css_class='form-group mb-3 col-md-6'),
                    css_class='row'
                ),
                'registration_number',
            ),
            
            Fieldset(
                'Branch Setup',
                'number_of_branches',
                HTML("""
                    <div class="alert alert-info mt-2">
                        <small><i class="bi bi-info-circle"></i> You'll add branch details in the next step.</small>
                    </div>
                """)
            ),
            
            FormActions(
                Submit('next', 'Next → Add Branches', css_class='btn btn-primary btn-lg w-100 py-3'),
            )
        )
    
    def clean_phone(self):
        """Validate phone number format."""
        phone = self.cleaned_data.get('phone')
        if phone:
            # Remove spaces and dashes
            phone = re.sub(r'[\s\-\(\)]', '', phone)
            if not re.match(r'^\+?[0-9]{10,15}$', phone):
                raise forms.ValidationError("Enter a valid phone number with country code.")
        return phone
    
    def clean_email(self):
        """Validate email."""
        email = self.cleaned_data.get('email')
        if email and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            raise forms.ValidationError("Enter a valid email address.")
        return email


class BranchSetupForm(forms.Form):
    """
    Dynamic form for branch details based on number of branches.
    This form will be instantiated with the number of branches.
    """
    
    def __init__(self, *args, num_branches=1, **kwargs):
        super().__init__(*args, **kwargs)
        self.num_branches = num_branches
        
        # Create dynamic fields for each branch
        for i in range(1, num_branches + 1):
            # Branch name field
            self.fields[f'branch_{i}_name'] = forms.CharField(
                max_length=255,
                required=True,
                widget=forms.TextInput(attrs={
                    'placeholder': f'Branch {i} Name (e.g., Main Campus)',
                    'class': 'form-control'
                }),
                label=f'Branch {i} Name'
            )
            
            # Branch city field
            self.fields[f'branch_{i}_city'] = forms.CharField(
                max_length=100,
                required=True,
                widget=forms.TextInput(attrs={
                    'placeholder': f'Branch {i} City',
                    'class': 'form-control'
                }),
                label=f'Branch {i} City'
            )
            
            # Branch address field
            self.fields[f'branch_{i}_address'] = forms.CharField(
                required=True,
                widget=forms.Textarea(attrs={
                    'rows': 2,
                    'placeholder': f'Branch {i} Full Address',
                    'class': 'form-control'
                }),
                label=f'Branch {i} Address'
            )
            
            # Branch phone field
            self.fields[f'branch_{i}_phone'] = forms.CharField(
                max_length=20,
                required=True,
                widget=forms.TextInput(attrs={
                    'placeholder': f'Branch {i} Phone',
                    'class': 'form-control'
                }),
                label=f'Branch {i} Phone'
            )
            
            # Branch email field
            self.fields[f'branch_{i}_email'] = forms.EmailField(
                required=True,
                widget=forms.EmailInput(attrs={
                    'placeholder': f'Branch {i} Email',
                    'class': 'form-control'
                }),
                label=f'Branch {i} Email'
            )

            # Fee Structure fields
            self.fields[f'branch_{i}_fee_frequency'] = forms.ChoiceField(
                choices=[('monthly', 'Monthly'), ('yearly', 'Yearly')],
                initial='monthly',
                widget=forms.Select(attrs={
                    'class': 'form-select fee-frequency-select',
                    'data-branch': str(i),
                }),
                label=f'Branch {i} Fee Frequency'
            )

            self.fields[f'branch_{i}_monthly_amount'] = forms.DecimalField(
                required=False, min_value=0,
                widget=forms.NumberInput(attrs={
                    'placeholder': 'Monthly fee in PKR',
                    'class': 'form-control monthly-field',
                    'data-branch': str(i),
                }),
                label=f'Branch {i} Monthly Fee (PKR)'
            )

            self.fields[f'branch_{i}_yearly_amount'] = forms.DecimalField(
                required=False, min_value=0,
                widget=forms.NumberInput(attrs={
                    'placeholder': 'Yearly fee in PKR',
                    'class': 'form-control yearly-field',
                    'data-branch': str(i),
                }),
                label=f'Branch {i} Yearly Fee (PKR)'
            )

            self.fields[f'branch_{i}_yearly_installments'] = forms.IntegerField(
                required=False, min_value=1, max_value=12,
                widget=forms.NumberInput(attrs={
                    'placeholder': 'No. of installments',
                    'class': 'form-control yearly-field',
                    'data-branch': str(i),
                }),
                label=f'Branch {i} No. of Installments'
            )
    
    def clean(self):
        """Additional validation for branch fields."""
        cleaned_data = super().clean()

        branch_names = []
        for i in range(1, self.num_branches + 1):
            name = cleaned_data.get(f'branch_{i}_name')
            if name:
                if name in branch_names:
                    self.add_error(f'branch_{i}_name', f'Branch {i} name must be unique.')
                branch_names.append(name)

            freq = cleaned_data.get(f'branch_{i}_fee_frequency')
            if freq == 'monthly':
                if not cleaned_data.get(f'branch_{i}_monthly_amount'):
                    self.add_error(f'branch_{i}_monthly_amount', 'Monthly fee amount is required.')
            elif freq == 'yearly':
                if not cleaned_data.get(f'branch_{i}_yearly_amount'):
                    self.add_error(f'branch_{i}_yearly_amount', 'Yearly fee amount is required.')
                if not cleaned_data.get(f'branch_{i}_yearly_installments'):
                    self.add_error(f'branch_{i}_yearly_installments', 'Number of installments is required.')

        return cleaned_data


class ManagerCredentialsForm(forms.Form):
    """
    Step 3: Manager credentials for each branch.
    Principal can edit manager email and password.
    Uses form_id (from branch.form_id or temp_id) since branch objects are not saved yet.
    """
    
    def __init__(self, *args, branches=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.branches = branches or []
        
        for branch in self.branches:
            form_id = getattr(branch, 'form_id', getattr(branch, 'id') or 0)
            
            # Manager email field
            self.fields[f'manager_email_{form_id}'] = forms.EmailField(
                required=True,
                initial=f"manager.{branch.name.lower().replace(' ', '.')}@school.com",
                widget=forms.EmailInput(attrs={
                    'placeholder': 'manager@email.com',
                    'class': 'form-control'
                }),
                label=f'Manager Email for {branch.name}'
            )
            
            # Manager password field
            self.fields[f'manager_password_{form_id}'] = forms.CharField(
                required=True,
                initial='Temp@123456',
                widget=forms.TextInput(attrs={
                    'placeholder': 'Password',
                    'class': 'form-control',
                    'value': 'Temp@123456'
                }),
                label=f'Manager Password for {branch.name}',
                help_text='You can change this password later.'
            )
            
            # Confirm password field
            self.fields[f'confirm_password_{form_id}'] = forms.CharField(
                required=True,
                initial='Temp@123456',
                widget=forms.TextInput(attrs={
                    'placeholder': 'Confirm Password',
                    'class': 'form-control',
                    'value': 'Temp@123456'
                }),
                label=f'Confirm Password for {branch.name}'
            )

            # Manager salary field
            self.fields[f'manager_salary_{form_id}'] = forms.DecimalField(
                required=False,
                initial=0,
                min_value=0,
                widget=forms.NumberInput(attrs={
                    'placeholder': 'Salary in PKR',
                    'class': 'form-control',
                    'step': '1000',
                }),
                label=f'Manager Salary for {branch.name} (PKR)',
                help_text='Monthly salary for this branch manager.'
            )
    
    def clean(self):
        """Validate that passwords match for each branch."""
        cleaned_data = super().clean()
        
        for branch in self.branches:
            form_id = getattr(branch, 'form_id', getattr(branch, 'id') or 0)
            password = cleaned_data.get(f'manager_password_{form_id}')
            confirm = cleaned_data.get(f'confirm_password_{form_id}')
            
            if password and confirm and password != confirm:
                self.add_error(
                    f'manager_password_{form_id}', 
                    f'Passwords for {branch.name} do not match.'
                )
            
            # Validate password strength
            if password and len(password) < 8:
                self.add_error(
                    f'manager_password_{form_id}',
                    'Password must be at least 8 characters long.'
                )
        
        return cleaned_data


class BranchManagerForm(forms.ModelForm):
    """
    Form for editing branch manager details.
    """
    
    manager_email = forms.EmailField(required=True, label='Manager Email')
    manager_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput,
        label='New Password (leave blank to keep current)'
    )
    confirm_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput,
        label='Confirm New Password'
    )
    
    class Meta:
        model = Branch
        fields = ['name', 'phone', 'email', 'address', 'city', 'is_active']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Row(
                Column('name', css_class='form-group mb-3 col-md-6'),
                Column('city', css_class='form-group mb-3 col-md-6'),
            ),
            'address',
            Row(
                Column('phone', css_class='form-group mb-3 col-md-6'),
                Column('email', css_class='form-group mb-3 col-md-6'),
            ),
            HTML("<hr><h5>Manager Account Settings</h5>"),
            Row(
                Column('manager_email', css_class='form-group mb-3 col-md-6'),
                css_class='row'
            ),
            Row(
                Column('manager_password', css_class='form-group mb-3 col-md-6'),
                Column('confirm_password', css_class='form-group mb-3 col-md-6'),
            ),
            FormActions(
                Submit('submit', 'Update Branch & Manager', css_class='btn btn-primary'),
            )
        )
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('manager_password')
        confirm = cleaned_data.get('confirm_password')
        
        if password and confirm and password != confirm:
            self.add_error('confirm_password', 'Passwords do not match.')
        
        return cleaned_data


class SchoolEditForm(forms.ModelForm):
    """
    Form for editing school information (Principal only).
    """
    class Meta:
        model = SchoolTenant
        fields = ['name', 'city', 'address', 'phone', 'email', 'established_year', 'registration_number']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'School Name'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+92 300 0000000'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'school@email.com'}),
            'established_year': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '2000'}),
            'registration_number': forms.TextInput(attrs={'class': 'form-control'}),
        }


class BranchCreateForm(forms.ModelForm):
    """
    Form for creating a new branch along with a manager account.
    """
    manager_email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'manager@school.com'}),
        label='Manager Email'
    )
    manager_password = forms.CharField(
        required=True,
        initial='Temp@123456',
        widget=forms.TextInput(attrs={'class': 'form-control', 'value': 'Temp@123456', 'placeholder': 'Password'}),
        label='Manager Password',
        help_text='Temporary password — manager should change it after first login.'
    )
    confirm_password = forms.CharField(
        required=True,
        initial='Temp@123456',
        widget=forms.TextInput(attrs={'class': 'form-control', 'value': 'Temp@123456', 'placeholder': 'Confirm Password'}),
        label='Confirm Password'
    )
    manager_salary = forms.DecimalField(
        required=False,
        min_value=0,
        initial=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Monthly Salary (PKR)', 'step': '1000'}),
        label='Manager Monthly Salary (PKR)'
    )

    class Meta:
        model = Branch
        fields = ['name', 'city', 'address', 'phone', 'email', 'is_main_branch']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Main Campus'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+92 300 0000000'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'branch@school.com'}),
            'is_main_branch': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('manager_password')
        confirm = cleaned_data.get('confirm_password')
        if password and confirm and password != confirm:
            self.add_error('confirm_password', 'Passwords do not match.')
        if password and len(password) < 8:
            self.add_error('manager_password', 'Password must be at least 8 characters.')
        return cleaned_data


class BranchUpdateForm(forms.ModelForm):
    """
    Form for updating an existing branch and optionally updating manager credentials.
    """
    manager_email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
        label='Manager Email'
    )
    manager_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Manager Full Name'}),
        label='Manager Full Name'
    )
    new_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label='New Password (leave blank to keep current)'
    )
    confirm_new_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label='Confirm New Password'
    )

    class Meta:
        model = Branch
        fields = ['name', 'city', 'address', 'phone', 'email', 'is_main_branch', 'is_active', 'manager_salary']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'is_main_branch': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'manager_salary': forms.NumberInput(attrs={'class': 'form-control', 'step': '1000'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('new_password')
        confirm = cleaned_data.get('confirm_new_password')
        if password and confirm and password != confirm:
            self.add_error('confirm_new_password', 'Passwords do not match.')
        if password and len(password) < 8:
            self.add_error('new_password', 'Password must be at least 8 characters.')
        return cleaned_data