"""Forms for the equipment app."""

from django import forms

from apps.equipment.models import Category, Equipment, LifecycleEvent, Location, MovementLog


class CategoryForm(forms.ModelForm):
    """Create or edit an equipment Category."""

    class Meta:
        model = Category
        fields = ('name', 'description', 'color')
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g. Oscilloscopes',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Optional description of this category…',
            }),
            'color': forms.TextInput(attrs={
                'class': 'form-input',
                'type': 'color',
                'style': 'width: 3rem; padding: 0.2rem;',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['color'].required = False
        self.fields['color'].help_text = 'Leave blank for a random unique color.'


class LocationForm(forms.ModelForm):
    """Create or edit a physical Location."""

    class Meta:
        model = Location
        fields = ('name', 'description', 'building', 'room')
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g. Storage Cabinet A',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Optional description…',
            }),
            'building': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g. Engineering Block',
            }),
            'room': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g. Room 301',
            }),
        }


class EquipmentForm(forms.ModelForm):
    """Create or edit a piece of Equipment."""

    class Meta:
        model = Equipment
        fields = (
            'name',
            'description',
            'serial_number',
            'model_number',
            'manufacturer',
            'category',
            'location',
            'owner',
            'status',
            'condition',
            'image',
            'purchase_date',
            'purchase_price',
            'notes',
        )
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Equipment name',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Brief description of the equipment…',
            }),
            'serial_number': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Manufacturer serial number (optional)',
            }),
            'model_number': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Model number (optional)',
            }),
            'manufacturer': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Manufacturer name (optional)',
            }),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'location': forms.Select(attrs={'class': 'form-select'}),
            'owner': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'condition': forms.Select(attrs={'class': 'form-select'}),
            'image': forms.ClearableFileInput(attrs={
                'class': 'form-file-input',
                'accept': 'image/*',
            }),
            'purchase_date': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date',
            }),
            'purchase_price': forms.NumberInput(attrs={
                'class': 'form-input',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Additional notes…',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].required = True
        self.fields['location'].required = True
        self.fields['owner'].required = True
        # Image is required only when creating or when no image exists yet
        if not self.instance or not self.instance.pk or not self.instance.image:
            self.fields['image'].required = True


class LifecycleEventForm(forms.ModelForm):
    """Record a lifecycle event for a piece of equipment."""

    class Meta:
        model = LifecycleEvent
        fields = ('equipment', 'event_type', 'description')
        widgets = {
            'equipment': forms.HiddenInput(),
            'event_type': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 4,
                'placeholder': 'Describe what happened…',
            }),
        }


class MovementLogForm(forms.ModelForm):
    """
    Record a movement of equipment between locations.

    The ``equipment`` field is intentionally excluded here and must be set by
    the view before saving.
    """

    class Meta:
        model = MovementLog
        fields = ('from_location', 'to_location', 'reason')
        widgets = {
            'from_location': forms.Select(attrs={'class': 'form-select'}),
            'to_location': forms.Select(attrs={'class': 'form-select'}),
            'reason': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Reason for moving (optional)',
            }),
        }

    def clean(self):
        cleaned = super().clean()
        from_loc = cleaned.get('from_location')
        to_loc = cleaned.get('to_location')
        if from_loc and to_loc and from_loc == to_loc:
            raise forms.ValidationError(
                'The destination location must be different from the current location.'
            )
        return cleaned


class EquipmentFilterForm(forms.Form):
    """Non-model form for filtering the equipment list view."""

    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Search by name, serial number…',
        }),
        label='Search',
    )
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        empty_label='All categories',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    location = forms.ModelChoiceField(
        queryset=Location.objects.all(),
        required=False,
        empty_label='All locations',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    status = forms.ChoiceField(
        choices=[('', 'All statuses')] + Equipment.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    condition = forms.ChoiceField(
        choices=[('', 'All conditions')] + Equipment.CONDITION_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
