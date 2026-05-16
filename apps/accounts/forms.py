"""Forms for the accounts app."""

from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm

from apps.accounts.models import CustomUser, UserProfile


class CustomUserCreationForm(UserCreationForm):
    """Registration form that collects core user fields."""

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'you@example.com',
            'autocomplete': 'email',
        }),
        help_text='Enter a valid email address. This will be used to log in.',
    )
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'username',
            'autocomplete': 'username',
        }),
    )
    first_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'First name',
            'autocomplete': 'given-name',
        }),
    )
    last_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Last name',
            'autocomplete': 'family-name',
        }),
    )
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Create a password',
            'autocomplete': 'new-password',
        }),
    )
    password2 = forms.CharField(
        label='Confirm password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Repeat the password',
            'autocomplete': 'new-password',
        }),
    )

    class Meta:
        model = CustomUser
        fields = ('email', 'username', 'first_name', 'last_name', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data.get('email', '').lower()
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError('An account with this email address already exists.')
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username', '')
        if CustomUser.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('This username is already taken.')
        return username


class CustomUserChangeForm(UserChangeForm):
    """Admin form for editing a CustomUser instance."""

    class Meta:
        model = CustomUser
        fields = ('email', 'username', 'first_name', 'last_name', 'role', 'is_active', 'is_staff')


class LoginForm(forms.Form):
    """Email + password login form with an optional remember-me flag."""

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'you@example.com',
            'autofocus': True,
            'autocomplete': 'email',
        }),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Password',
            'autocomplete': 'current-password',
        }),
    )
    remember_me = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        label='Remember me',
    )


class ProfileUpdateForm(forms.ModelForm):
    """Form for editing a UserProfile instance."""

    class Meta:
        model = UserProfile
        fields = (
            'phone', 'department', 'student_id', 'bio', 'avatar',
            'in_app_notifications', 'email_notifications',
            'notify_borrowing', 'notify_reservations', 'notify_incidents',
            'notify_equipment', 'notify_kits', 'notify_projects', 'notify_system',
        )
        widgets = {
            'phone': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '+880 1xxx-xxxxxx',
            }),
            'department': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g. Computer Science & Engineering',
            }),
            'student_id': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Your student / employee ID',
            }),
            'bio': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 4,
                'placeholder': 'A short bio about yourself…',
            }),
            'avatar': forms.ClearableFileInput(attrs={
                'class': 'form-file-input',
                'accept': 'image/*',
            }),
        }


class UserUpdateForm(forms.ModelForm):
    """Form for editing basic CustomUser identity fields."""

    class Meta:
        model = CustomUser
        fields = ('first_name', 'last_name', 'username')
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'First name',
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Last name',
            }),
            'username': forms.TextInput(attrs={
                'class': 'form-input',
            }),
        }

    def clean_username(self):
        username = self.cleaned_data.get('username', '')
        qs = CustomUser.objects.filter(username__iexact=username).exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('This username is already taken.')
        return username


class RoleAssignForm(forms.ModelForm):
    """Admin form for changing a user's role."""

    class Meta:
        model = CustomUser
        fields = ('role',)
        widgets = {
            'role': forms.Select(attrs={'class': 'form-select'}),
        }
