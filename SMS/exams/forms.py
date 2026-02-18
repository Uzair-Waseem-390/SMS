from django import forms
from django.utils import timezone
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, Fieldset, HTML
from crispy_forms.bootstrap import FormActions
from .models import Exam, EXAM_TYPE_CHOICES
from academics.models import Class, Section, Subject


class ExamBulkCreateForm(forms.Form):
    """Allows creating an exam across multiple classes/sections at once."""

    name = forms.CharField(max_length=200, label="Exam Name")
    exam_type = forms.ChoiceField(choices=EXAM_TYPE_CHOICES, label="Exam Type")
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), label="Exam Date")
    start_time = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}), label="Start Time")
    duration_minutes = forms.IntegerField(min_value=1, label="Duration (minutes)")
    subject = forms.ModelChoiceField(queryset=Subject.objects.none(), label="Subject")
    total_marks = forms.IntegerField(initial=100, min_value=1, label="Total Marks")
    passing_marks = forms.IntegerField(initial=33, min_value=0, label="Passing Marks")
    description = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}), required=False,
        label="Description / Instructions"
    )

    classes = forms.ModelMultipleChoiceField(
        queryset=Class.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        label="Select Classes",
    )
    sections = forms.ModelMultipleChoiceField(
        queryset=Section.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        label="Select Sections",
    )

    def __init__(self, *args, branch=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.branch = branch

        if branch:
            self.fields['subject'].queryset = Subject.objects.filter(branch=branch, is_active=True)
            self.fields['classes'].queryset = Class.objects.filter(branch=branch, is_active=True).order_by('numeric_level')

        if not self.initial.get('date') and not self.data.get('date'):
            self.fields['date'].initial = timezone.now().date()

        if self.data.getlist('classes'):
            try:
                class_ids = [int(c) for c in self.data.getlist('classes')]
                self.fields['sections'].queryset = Section.objects.filter(
                    class_obj_id__in=class_ids, class_obj__branch=branch, is_active=True
                ).select_related('class_obj').order_by('class_obj__numeric_level', 'name')
            except (TypeError, ValueError):
                pass

    def clean(self):
        cleaned = super().clean()
        sections = cleaned.get('sections', [])
        classes = cleaned.get('classes', [])
        if not sections:
            self.add_error('sections', 'Select at least one section.')
        for sec in sections:
            if sec.class_obj not in classes:
                self.add_error('sections', f'Section "{sec}" does not belong to a selected class.')
                break
        tm = cleaned.get('total_marks', 100)
        pm = cleaned.get('passing_marks', 33)
        if pm > tm:
            self.add_error('passing_marks', 'Passing marks cannot exceed total marks.')
        return cleaned


class ExamEditForm(forms.ModelForm):
    """Edit a single existing exam."""

    class Meta:
        model = Exam
        fields = [
            'name', 'exam_type', 'date', 'start_time', 'duration_minutes',
            'subject', 'class_obj', 'section', 'total_marks', 'passing_marks', 'description',
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, branch=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.branch = branch

        if branch:
            self.fields['subject'].queryset = Subject.objects.filter(branch=branch, is_active=True)
            self.fields['class_obj'].queryset = Class.objects.filter(branch=branch, is_active=True).order_by('numeric_level')
        else:
            self.fields['subject'].queryset = Subject.objects.none()
            self.fields['class_obj'].queryset = Class.objects.none()

        self.fields['section'].queryset = Section.objects.none()

        if 'class_obj' in self.data:
            try:
                cid = int(self.data.get('class_obj'))
                self.fields['section'].queryset = Section.objects.filter(
                    class_obj_id=cid, class_obj__branch=branch, is_active=True
                )
            except (TypeError, ValueError):
                pass
        elif self.instance.pk:
            self.fields['section'].queryset = Section.objects.filter(
                class_obj=self.instance.class_obj, is_active=True
            )

        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Fieldset('Exam Details',
                Row(Column('name', css_class='col-md-6 mb-3'), Column('exam_type', css_class='col-md-6 mb-3')),
                Row(Column('date', css_class='col-md-4 mb-3'), Column('start_time', css_class='col-md-4 mb-3'), Column('duration_minutes', css_class='col-md-4 mb-3')),
            ),
            Fieldset('Academic Details',
                Row(Column('subject', css_class='col-md-4 mb-3'), Column('class_obj', css_class='col-md-4 mb-3'), Column('section', css_class='col-md-4 mb-3')),
                Row(Column('total_marks', css_class='col-md-6 mb-3'), Column('passing_marks', css_class='col-md-6 mb-3')),
            ),
            'description',
            FormActions(Submit('submit', 'Update Exam', css_class='btn btn-primary btn-lg')),
        )
