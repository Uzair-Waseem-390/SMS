from django import forms
from .models import STUDENT_STATUS_CHOICES, STAFF_STATUS_CHOICES


class StudentAttendanceForm(forms.Form):
    """Form for a single student's attendance in a bulk-mark page."""
    student_id = forms.IntegerField(widget=forms.HiddenInput())
    status = forms.ChoiceField(
        choices=STUDENT_STATUS_CHOICES, initial='present',
        widget=forms.Select(attrs={'class': 'form-select form-select-sm attendance-status'}),
    )
    remarks = forms.CharField(
        required=False, max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Remarks'}),
    )


class StaffAttendanceForm(forms.Form):
    """Form for a single staff member's attendance in a bulk-mark page."""
    user_id = forms.IntegerField(widget=forms.HiddenInput())
    status = forms.ChoiceField(
        choices=STAFF_STATUS_CHOICES, initial='present',
        widget=forms.Select(attrs={'class': 'form-select form-select-sm attendance-status'}),
    )
    late_time = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control form-control-sm'}),
    )
    half_leave_time = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control form-control-sm'}),
    )
    remarks = forms.CharField(
        required=False, max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Remarks'}),
    )


class DatePickerForm(forms.Form):
    """Simple date picker to select the attendance date."""
    date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label="Attendance Date"
    )
