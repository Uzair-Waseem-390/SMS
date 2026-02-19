from django import forms
from django.utils import timezone
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, Fieldset, HTML
from crispy_forms.bootstrap import FormActions
from .models import (
    BranchFeeStructure, Scholarship, StudentFee, Expense, SalaryRecord,
    FREQUENCY_CHOICES, SCHOLARSHIP_TYPE_CHOICES, FEE_TYPE_CHOICES,
    EXPENSE_CATEGORY_CHOICES,
)
import calendar
from tenants.models import Branch
from academics.models import Class, Section


class BranchFeeStructureForm(forms.ModelForm):
    class Meta:
        model = BranchFeeStructure
        fields = ['frequency', 'monthly_amount', 'yearly_amount', 'yearly_installments', 'is_active']
        widgets = {
            'monthly_amount': forms.NumberInput(attrs={'placeholder': 'Monthly fee in PKR'}),
            'yearly_amount': forms.NumberInput(attrs={'placeholder': 'Yearly fee in PKR'}),
            'yearly_installments': forms.NumberInput(attrs={'placeholder': 'e.g. 3', 'min': 1, 'max': 12}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            'frequency',
            Row(Column('monthly_amount', css_class='col-md-6 mb-3')),
            Row(Column('yearly_amount', css_class='col-md-6 mb-3'), Column('yearly_installments', css_class='col-md-6 mb-3')),
            'is_active',
            FormActions(Submit('submit', 'Save Fee Structure', css_class='btn btn-primary btn-lg')),
        )

    def clean(self):
        cd = super().clean()
        freq = cd.get('frequency')
        if freq == 'monthly' and not cd.get('monthly_amount'):
            self.add_error('monthly_amount', 'Monthly fee amount is required.')
        if freq == 'yearly':
            if not cd.get('yearly_amount'):
                self.add_error('yearly_amount', 'Yearly fee amount is required.')
            if not cd.get('yearly_installments'):
                self.add_error('yearly_installments', 'Number of installments is required.')
        return cd


class ScholarshipForm(forms.ModelForm):
    class Meta:
        model = Scholarship
        fields = ['name', 'description', 'scholarship_type', 'percentage_amount', 'fixed_amount', 'start_date', 'end_date', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'percentage_amount': forms.NumberInput(attrs={'placeholder': 'e.g. 25', 'min': 0, 'max': 100, 'step': '0.01'}),
            'fixed_amount': forms.NumberInput(attrs={'placeholder': 'Fixed amount in PKR', 'step': '0.01'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields['start_date'].initial = timezone.now().date()
        btn_label = 'Update Scholarship' if self.instance.pk else 'Create Scholarship'
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Fieldset('Scholarship Details',
                Row(Column('name', css_class='col-md-6 mb-3'), Column('scholarship_type', css_class='col-md-6 mb-3')),
                Row(Column('percentage_amount', css_class='col-md-6 mb-3'), Column('fixed_amount', css_class='col-md-6 mb-3')),
                Row(Column('start_date', css_class='col-md-4 mb-3'), Column('end_date', css_class='col-md-4 mb-3'), Column('is_active', css_class='col-md-4 mb-3')),
                'description',
            ),
            FormActions(Submit('submit', btn_label, css_class='btn btn-primary btn-lg')),
        )

    def clean(self):
        cd = super().clean()
        stype = cd.get('scholarship_type')
        if stype == 'percentage' and not cd.get('percentage_amount'):
            self.add_error('percentage_amount', 'Percentage is required.')
        if stype == 'fixed' and not cd.get('fixed_amount'):
            self.add_error('fixed_amount', 'Fixed amount is required.')
        return cd


class GenerateFeeForm(forms.Form):
    """Form for generating fees for students (bulk or individual)."""

    fee_type = forms.ChoiceField(
        choices=FEE_TYPE_CHOICES,
        initial='academic',
        widget=forms.RadioSelect(attrs={'class': 'form-check-input', 'id': 'id_fee_type'}),
        label="Fee Type"
    )
    class_filter = forms.ModelChoiceField(
        queryset=Class.objects.none(), required=False,
        empty_label="All Classes",
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_class_filter'}),
        label="Class"
    )
    section_filter = forms.ModelChoiceField(
        queryset=Section.objects.none(), required=False,
        empty_label="All Sections",
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_section_filter'}),
        label="Section"
    )
    due_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label="Due Date"
    )
    label = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': "e.g. 'February 2026' or 'Installment 1 of 3'"}),
        label="Fee Label"
    )
    installment_number = forms.IntegerField(
        required=False, min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'For yearly: installment #'}),
        label="Installment # (yearly only)"
    )

    # Special fee fields
    special_fee_name = forms.CharField(
        required=False, max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Exam Fund, Lab Fee, Sports Fee'}),
        label="Special Fee Name"
    )
    special_fee_amount = forms.DecimalField(
        required=False, max_digits=10, decimal_places=2, min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Amount in PKR'}),
        label="Special Fee Amount (PKR)"
    )

    def __init__(self, *args, branch=None, **kwargs):
        super().__init__(*args, **kwargs)
        if branch:
            self.fields['class_filter'].queryset = Class.objects.filter(branch=branch, is_active=True).order_by('numeric_level')
            self.fields['section_filter'].queryset = Section.objects.filter(class_obj__branch=branch, is_active=True).order_by('class_obj__numeric_level', 'name')

            if 'class_filter' in self.data:
                try:
                    class_id = int(self.data.get('class_filter'))
                    self.fields['section_filter'].queryset = Section.objects.filter(
                        class_obj_id=class_id, class_obj__branch=branch, is_active=True
                    ).order_by('name')
                except (TypeError, ValueError):
                    pass
        if not self.fields['due_date'].initial:
            self.fields['due_date'].initial = timezone.now().date()

        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Fieldset('Fee Type',
                'fee_type',
            ),
            Fieldset('Student Filter',
                Row(Column('class_filter', css_class='col-md-6 mb-3'), Column('section_filter', css_class='col-md-6 mb-3')),
            ),
            Fieldset('Special Fee Details',
                Row(Column('special_fee_name', css_class='col-md-6 mb-3'), Column('special_fee_amount', css_class='col-md-6 mb-3')),
                css_id='special-fields',
            ),
            Fieldset('Fee Info',
                Row(Column('due_date', css_class='col-md-4 mb-3'), Column('label', css_class='col-md-4 mb-3'), Column('installment_number', css_class='col-md-4 mb-3', css_id='installment-wrap')),
            ),
            FormActions(Submit('generate', 'Generate Fees', css_class='btn btn-primary btn-lg')),
        )

    def clean(self):
        cd = super().clean()
        fee_type = cd.get('fee_type')
        if fee_type == 'special':
            if not cd.get('special_fee_name'):
                self.add_error('special_fee_name', 'Fee name is required for special fees.')
            if not cd.get('special_fee_amount'):
                self.add_error('special_fee_amount', 'Amount is required for special fees.')
        return cd


class RecordPaymentForm(forms.Form):
    """Form for recording a payment against a student fee."""

    PAYMENT_TYPE_CHOICES = [
        ('full', 'Full Payment (mark as Paid)'),
        ('partial', 'Partial Payment'),
    ]

    payment_type = forms.ChoiceField(
        choices=PAYMENT_TYPE_CHOICES,
        initial='full',
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        label="Payment Type"
    )
    amount = forms.DecimalField(
        max_digits=10, decimal_places=2, min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'Amount in PKR'}),
        label="Payment Amount (PKR)"
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Optional notes'}),
        label="Notes"
    )

    def __init__(self, *args, max_amount=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_amount = max_amount
        if max_amount:
            self.fields['amount'].initial = max_amount
            self.fields['amount'].widget.attrs['max'] = str(max_amount)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            'payment_type', 'amount', 'notes',
            FormActions(Submit('pay', 'Record Payment', css_class='btn btn-success btn-lg')),
        )

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if self.max_amount and amount and amount > self.max_amount:
            raise forms.ValidationError(f'Amount cannot exceed PKR {self.max_amount}')
        return amount

    def clean(self):
        cd = super().clean()
        ptype = cd.get('payment_type')
        amount = cd.get('amount')
        if ptype == 'full' and self.max_amount and amount and amount < self.max_amount:
            self.add_error('amount', f'Full payment requires PKR {self.max_amount}. Use "Partial Payment" for a smaller amount.')
        return cd


class EditSpecialFeeForm(forms.Form):
    """Form for editing a special fee for a specific student."""

    special_fee_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label="Fee Name"
    )
    amount = forms.DecimalField(
        max_digits=10, decimal_places=2, min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Amount in PKR'}),
        label="Amount (PKR)"
    )
    due_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label="Due Date"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Row(Column('special_fee_name', css_class='col-md-4 mb-3'),
                Column('amount', css_class='col-md-4 mb-3'),
                Column('due_date', css_class='col-md-4 mb-3')),
            FormActions(Submit('save', 'Update Special Fee', css_class='btn btn-primary btn-lg')),
        )


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['title', 'category', 'amount', 'expense_date', 'description']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'e.g. Monthly Rent', 'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'placeholder': 'Amount in PKR', 'class': 'form-control', 'step': '0.01'}),
            'expense_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Optional details'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields['expense_date'].initial = timezone.now().date()
        btn_label = 'Update Expense' if self.instance.pk else 'Add Expense'
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Row(Column('title', css_class='col-md-6 mb-3'), Column('category', css_class='col-md-6 mb-3')),
            Row(Column('amount', css_class='col-md-6 mb-3'), Column('expense_date', css_class='col-md-6 mb-3')),
            'description',
            FormActions(Submit('submit', btn_label, css_class='btn btn-primary btn-lg')),
        )


MONTH_CHOICES = [(i, calendar.month_name[i]) for i in range(1, 13)]


class GenerateSalaryForm(forms.Form):
    """Form for generating salary records for all employees of a branch for a given month."""

    month = forms.ChoiceField(
        choices=MONTH_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Month"
    )
    year = forms.IntegerField(
        min_value=2020, max_value=2099,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        label="Year"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        now = timezone.now()
        self.fields['month'].initial = now.month
        self.fields['year'].initial = now.year
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Row(Column('month', css_class='col-md-6 mb-3'), Column('year', css_class='col-md-6 mb-3')),
            FormActions(Submit('generate', 'Generate Salary Records', css_class='btn btn-primary btn-lg')),
        )


class EditSalaryForm(forms.Form):
    """Edit salary amount for a specific salary record."""

    salary_amount = forms.DecimalField(
        max_digits=10, decimal_places=2, min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Amount in PKR'}),
        label="Salary Amount (PKR)"
    )
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Notes'}),
        label="Notes"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Row(Column('salary_amount', css_class='col-md-6 mb-3'), Column('description', css_class='col-md-6 mb-3')),
            FormActions(Submit('save', 'Update Salary', css_class='btn btn-primary btn-lg')),
        )
