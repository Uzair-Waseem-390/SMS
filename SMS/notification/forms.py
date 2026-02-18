from django import forms
from django.utils import timezone
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, Fieldset, HTML
from crispy_forms.bootstrap import FormActions
from .models import Notification, Timetable, NOTIFICATION_TYPE_CHOICES, VISIBILITY_CHOICES
from tenants.models import Branch


class NotificationForm(forms.ModelForm):
    class Meta:
        model = Notification
        fields = ['title', 'notification_type', 'visibility', 'date', 'time', 'duration_days', 'message', 'branch']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'time': forms.TimeInput(attrs={'type': 'time'}),
            'message': forms.Textarea(attrs={'rows': 5}),
        }

    def __init__(self, *args, user=None, school=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.school = school

        if not self.fields['date'].initial and not self.instance.pk:
            self.fields['date'].initial = timezone.now().date()
        if not self.fields['time'].initial and not self.instance.pk:
            self.fields['time'].initial = timezone.now().strftime('%H:%M')

        if user and school:
            branches = Branch.objects.filter(school=school, is_active=True)
            if user.user_type == 'manager':
                branch = getattr(user, 'managed_branch', None)
                if branch:
                    self.fields['branch'].queryset = Branch.objects.filter(id=branch.id)
                    self.fields['branch'].initial = branch.id
                    self.fields['branch'].widget = forms.HiddenInput()
                else:
                    self.fields['branch'].queryset = Branch.objects.none()
            else:
                self.fields['branch'].queryset = branches
        else:
            self.fields['branch'].queryset = Branch.objects.none()

        self.helper = FormHelper()
        self.helper.form_method = 'post'

        layout_fields = [
            Fieldset('Notification Details',
                Row(Column('title', css_class='col-md-6 mb-3'), Column('notification_type', css_class='col-md-3 mb-3'), Column('visibility', css_class='col-md-3 mb-3')),
                Row(Column('date', css_class='col-md-3 mb-3'), Column('time', css_class='col-md-3 mb-3'), Column('duration_days', css_class='col-md-3 mb-3'), Column('branch', css_class='col-md-3 mb-3')),
                'message',
            ),
        ]
        btn_label = 'Update Notification' if self.instance.pk else 'Create Notification'
        layout_fields.append(FormActions(Submit('submit', btn_label, css_class='btn btn-primary btn-lg')))
        self.helper.layout = Layout(*layout_fields)


class TimetableForm(forms.ModelForm):
    class Meta:
        model = Timetable
        fields = ['title', 'image', 'description', 'branch', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, user=None, school=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.school = school

        if user and school:
            branches = Branch.objects.filter(school=school, is_active=True)
            if user.user_type == 'manager':
                branch = getattr(user, 'managed_branch', None)
                if branch:
                    self.fields['branch'].queryset = Branch.objects.filter(id=branch.id)
                    self.fields['branch'].initial = branch.id
                    self.fields['branch'].widget = forms.HiddenInput()
                else:
                    self.fields['branch'].queryset = Branch.objects.none()
            else:
                self.fields['branch'].queryset = branches
        else:
            self.fields['branch'].queryset = Branch.objects.none()

        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_enctype = 'multipart/form-data'

        btn_label = 'Update Timetable' if self.instance.pk else 'Upload Timetable'
        self.helper.layout = Layout(
            Fieldset('Timetable Details',
                Row(Column('title', css_class='col-md-6 mb-3'), Column('branch', css_class='col-md-6 mb-3')),
                'image',
                'description',
                'is_active',
            ),
            FormActions(Submit('submit', btn_label, css_class='btn btn-primary btn-lg')),
        )
