"""Forms for the projects app."""

from django import forms
from django.contrib.auth import get_user_model

from apps.equipment.models import Equipment
from apps.kits.models import Kit
from apps.projects.models import Project, ProjectMember

User = get_user_model()


class ProjectForm(forms.ModelForm):
    """Form for creating or editing a Project."""

    initial_members = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(is_active=True).order_by('first_name', 'last_name', 'username'),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label='Members',
        help_text='Select members to add to this project (you will be added as Lead automatically).',
    )

    class Meta:
        model = Project
        fields = ['name', 'description', 'status', 'start_date', 'end_date', 'equipment', 'kits']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'equipment': forms.CheckboxSelectMultiple,
            'kits': forms.CheckboxSelectMultiple,
        }

    def __init__(self, *args, current_user=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Exclude the current user from the members list (they're auto-added as Lead)
        if current_user:
            self.fields['initial_members'].queryset = User.objects.filter(
                is_active=True
            ).exclude(pk=current_user.pk).order_by('first_name', 'last_name', 'username')
        self.fields['equipment'].queryset = Equipment.objects.filter(
            is_active=True
        ).select_related('category').order_by('name')
        self.fields['kits'].queryset = Kit.objects.filter(
            is_active=True
        ).order_by('name')

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if start_date and end_date and end_date < start_date:
            raise forms.ValidationError('End date must be on or after the start date.')

        return cleaned_data


class ProjectMemberForm(forms.ModelForm):
    """Form for adding a member to a project."""

    user = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True),
        empty_label='-- Select User --',
    )

    class Meta:
        model = ProjectMember
        fields = ['user', 'role']

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Exclude users who are already members of this project.
        if project is not None:
            existing_ids = project.project_members.values_list('user_id', flat=True)
            self.fields['user'].queryset = User.objects.filter(
                is_active=True
            ).exclude(pk__in=existing_ids)
