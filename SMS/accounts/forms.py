from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordChangeForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, HTML, Div, Field
from crispy_forms.bootstrap import FormActions
from .models import CustomUser
import re

class CustomUserCreationForm(UserCreationForm):
    """
    Form for user registration with payment verification requirements.
    Includes terms and conditions checkboxes.
    """
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'placeholder': 'Enter your email'}),
        label='Email Address'
    )
    
    full_name = forms.CharField(
        widget=forms.TextInput(attrs={'placeholder': 'Enter your full name'}),
        label='Full Name'
    )
    
    phone_number = forms.CharField(
        widget=forms.TextInput(attrs={'placeholder': '+923001234567'}),
        label='Phone Number',
        help_text='Enter your WhatsApp number with country code'
    )
    
    city = forms.CharField(
        widget=forms.TextInput(attrs={'placeholder': 'Your city'}),
        label='City',
        required=False
    )
    
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Create a password'}),
        label='Password'
    )
    
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirm password'}),
        label='Confirm Password'
    )
    
    # Terms and conditions checkboxes
    accepted_terms = forms.BooleanField(
        required=True,
        label='I agree to the Terms and Conditions',
        error_messages={'required': 'You must accept the terms and conditions to register.'}
    )
    
    accepted_policies = forms.BooleanField(
        required=True,
        label='I agree to the Privacy Policy',
        error_messages={'required': 'You must accept the privacy policy to register.'}
    )
    
    class Meta:
        model = CustomUser
        fields = ('email', 'full_name', 'phone_number', 'city', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-12 fw-bold'
        self.helper.field_class = 'col-lg-12'
        
        self.helper.layout = Layout(
            HTML("""
                <div class="alert alert-info mb-4">
                    <h5><i class="bi bi-info-circle"></i> Registration Fee: PKR 30,000</h5>
                    <p class="mb-0">After registration, you'll need to submit payment proof to activate your account.</p>
                </div>
            """),
            
            Row(
                Column('email', css_class='form-group mb-3'),
                Column('full_name', css_class='form-group mb-3'),
                css_class='row'
            ),
            
            Row(
                Column('phone_number', css_class='form-group mb-3'),
                Column('city', css_class='form-group mb-3'),
                css_class='row'
            ),
            
            Row(
                Column('password1', css_class='form-group mb-3'),
                Column('password2', css_class='form-group mb-3'),
                css_class='row'
            ),
            
            Div(
                Field('accepted_terms', css_class='form-check-input'),
                Field('accepted_policies', css_class='form-check-input'),
                css_class='terms-checkboxes mb-3'
            ),
            
            HTML("""
                <div class="payment-instructions bg-light p-3 rounded mb-3">
                    <h6><i class="bi bi-wallet2"></i> Payment Instructions:</h6>
                    <p>Send <strong>PKR 30,000</strong> to:</p>
                    <ul>
                        <li><strong>JazzCash Account:</strong> 0328 1525502</li>
                        <li><strong>Account Name:</strong> Uzair Waseem</li>
                    </ul>
                    <p class="text-muted small">After payment, take a screenshot and upload it in the next step.</p>
                </div>
            """),
            
            FormActions(
                Submit('submit', 'Register & Proceed to Payment', 
                       css_class='btn btn-primary w-100 py-2'),
            )
        )
    
    def clean_phone_number(self):
        """Validate phone number format."""
        phone = self.cleaned_data.get('phone_number')
        if phone:
            # Remove any spaces or dashes
            phone = re.sub(r'[\s\-]', '', phone)
            if not re.match(r'^\+?[0-9]{10,15}$', phone):
                raise forms.ValidationError("Enter a valid phone number with country code.")
        return phone
    
    def clean_email(self):
        """Validate email is unique."""
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email
    
    def save(self, commit=True):
        """Save the user but set active=False until payment verification."""
        user = super().save(commit=False)
        user.is_active = False  # Deactivate until payment verified
        user.payment_verified = False
        
        if commit:
            user.save()
        return user


class CustomAuthenticationForm(AuthenticationForm):
    """
    Custom login form with styling.
    """
    
    username = forms.EmailField(
        widget=forms.EmailInput(attrs={'placeholder': 'Enter your email'}),
        label='Email'
    )
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Enter your password'}),
        label='Password'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            'username',
            'password',
            HTML("""
                <div class="form-check mb-3">
                    <input type="checkbox" class="form-check-input" id="remember">
                    <label class="form-check-label" for="remember">Remember me</label>
                </div>
            """),
            FormActions(
                Submit('submit', 'Login', css_class='btn btn-primary w-100 py-2'),
            )
        )


class PaymentVerificationForm(forms.Form):
    """
    Form for payment verification - upload screenshot and transaction ID.
    """
    
    transaction_id = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'placeholder': 'Enter transaction ID'}),
        label='Transaction ID / Reference Number'
    )
    
    # payment_screenshot = forms.ImageField(
    #     label='Payment Screenshot',
    #     help_text='Upload screenshot of your JazzCash payment'
    # )
    payment_screenshot = forms.ImageField(
        label='Payment Screenshot',
        help_text='Upload screenshot of your JazzCash payment',
        widget=forms.ClearableFileInput(attrs={
            'accept': 'image/*'
        })
    )
    
    whatsapp_confirmation = forms.BooleanField(
        required=True,
        label='I have sent the screenshot to WhatsApp number 0328 1525502',
        error_messages={'required': 'You must confirm sending the screenshot to WhatsApp.'}
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_enctype = 'multipart/form-data'
        
        self.helper.layout = Layout(
            HTML("""
                <div class="alert alert-warning">
                    <h5><i class="bi bi-exclamation-triangle"></i> Important:</h5>
                    <p class="mb-0">After uploading, please send the same screenshot to <strong>0328 1525502</strong> on WhatsApp for manual verification. Your account will be activated within 24 hours.</p>
                </div>
                
                <div class="payment-details bg-light p-3 rounded mb-4">
                    <h6>Payment Details:</h6>
                    <ul class="list-unstyled">
                        <li><strong>Amount:</strong> PKR 30,000</li>
                        <li><strong>JazzCash Number:</strong> 0328 1525502</li>
                        <li><strong>Account Name:</strong> Uzair Waseem</li>
                    </ul>
                </div>
            """),
            
            'transaction_id',
            'payment_screenshot',
            'whatsapp_confirmation',
            
            FormActions(
                Submit('submit', 'Submit Payment Proof', css_class='btn btn-success w-100 py-2'),
            )
        )


class UserProfileForm(forms.ModelForm):
    """
    Form for editing user profile.
    """
    
    class Meta:
        model = CustomUser
        fields = ['full_name', 'phone_number', 'city']
        widgets = {
            'full_name': forms.TextInput(attrs={'placeholder': 'Your full name'}),
            'phone_number': forms.TextInput(attrs={'placeholder': '+923001234567'}),
            'city': forms.TextInput(attrs={'placeholder': 'Your city'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Row(
                Column('full_name', css_class='form-group mb-3'),
                css_class='row'
            ),
            Row(
                Column('phone_number', css_class='form-group mb-3'),
                Column('city', css_class='form-group mb-3'),
                css_class='row'
            ),
            FormActions(
                Submit('submit', 'Update Profile', css_class='btn btn-primary'),
            )
        )


class CustomPasswordChangeForm(PasswordChangeForm):
    """
    Custom password change form with styling.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        
        for field in self.fields:
            self.fields[field].widget.attrs.update({
                'class': 'form-control',
                'placeholder': f'Enter {self.fields[field].label.lower()}'
            })
        
        self.helper.layout = Layout(
            'old_password',
            'new_password1',
            'new_password2',
            FormActions(
                Submit('submit', 'Change Password', css_class='btn btn-primary'),
            )
        )




from django.contrib.auth.forms import PasswordChangeForm
from django.core.validators import RegexValidator


# then for profile update form
class EditProfileForm(forms.ModelForm):
    """
    Form for editing user profile information.
    """
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in format: '+999999999'. Up to 15 digits allowed."
    )
    
    phone_number = forms.CharField(
        validators=[phone_regex],
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter phone number'
        })
    )
    
    class Meta:
        model = CustomUser
        fields = ['full_name', 'phone_number', 'city']
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter full name'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter city'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})

class CustomPasswordChangeForm(PasswordChangeForm):
    """
    Custom password change form with Bootstrap styling.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({
                'class': 'form-control',
                'placeholder': f'Enter {field.replace("_", " ")}'
            })