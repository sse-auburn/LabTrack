"""Forms for the reservations app."""

from django import forms
from django.utils import timezone

from apps.equipment.models import Equipment
from apps.kits.models import Kit
from apps.reservations.models import Reservation, WaitlistEntry


class ReservationForm(forms.ModelForm):
    """Form for creating or editing a reservation for equipment or a kit."""

    equipment = forms.ModelChoiceField(
        queryset=Equipment.objects.filter(is_active=True),
        required=False,
        empty_label='-- Select Equipment --',
        help_text='Select equipment OR a kit, not both.',
    )
    kit = forms.ModelChoiceField(
        queryset=Kit.objects.filter(is_active=True),
        required=False,
        empty_label='-- Select Kit --',
        help_text='Select a kit OR equipment, not both.',
    )

    class Meta:
        model = Reservation
        fields = ['equipment', 'kit', 'start_date', 'end_date', 'purpose']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'purpose': forms.Textarea(attrs={'rows': 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        equipment = cleaned_data.get('equipment')
        kit = cleaned_data.get('kit')
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        # Exactly one of equipment or kit required.
        if not equipment and not kit:
            raise forms.ValidationError(
                'You must select either a piece of equipment or a kit.'
            )
        if equipment and kit:
            raise forms.ValidationError(
                'Please select either equipment or a kit, not both.'
            )

        # Date order validation.
        if start_date and end_date:
            if end_date < start_date:
                raise forms.ValidationError('End date must be on or after the start date.')

            if start_date < timezone.now().date():
                raise forms.ValidationError('Start date must be today or a future date.')

            # Overlap check: no CONFIRMED reservation for the same item in this window.
            from django.db.models import Q
            overlap_qs = Reservation.objects.filter(status='CONFIRMED')
            # Exclude the current instance when editing.
            if self.instance and self.instance.pk:
                overlap_qs = overlap_qs.exclude(pk=self.instance.pk)

            if equipment:
                kit_ids = equipment.kit_memberships.values_list('kit_id', flat=True)
                overlap_qs = overlap_qs.filter(
                    Q(equipment=equipment) | Q(kit_id__in=kit_ids)
                )
            else:
                eq_ids = list(kit.items.values_list('equipment_id', flat=True))
                overlap_qs = overlap_qs.filter(
                    Q(kit=kit) | Q(equipment_id__in=eq_ids)
                )

            # Overlapping date ranges: existing.start <= new.end AND existing.end >= new.start
            overlap_qs = overlap_qs.filter(
                start_date__lte=end_date,
                end_date__gte=start_date,
            )

            if overlap_qs.exists():
                item_name = str(equipment or kit)
                raise forms.ValidationError(
                    f'"{item_name}" already has a confirmed reservation overlapping '
                    f'the selected dates ({start_date} – {end_date}).'
                )

        return cleaned_data


class BulkReservationForm(forms.Form):
    """Shared date range and purpose when reserving multiple equipment items at once."""

    start_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        help_text='Start date for all reservations.',
    )
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        help_text='End date for all reservations.',
    )
    purpose = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        help_text='Purpose for reserving these items.',
    )

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if start_date and end_date:
            if end_date < start_date:
                raise forms.ValidationError('End date must be on or after the start date.')
            if start_date < timezone.now().date():
                raise forms.ValidationError('Start date must be today or a future date.')

        return cleaned_data


class WaitlistEntryForm(forms.ModelForm):
    """Form for joining the waitlist for a piece of equipment or a kit."""

    equipment = forms.ModelChoiceField(
        queryset=Equipment.objects.filter(is_active=True),
        required=False,
        empty_label='-- Select Equipment --',
    )
    kit = forms.ModelChoiceField(
        queryset=Kit.objects.filter(is_active=True),
        required=False,
        empty_label='-- Select Kit --',
    )

    class Meta:
        model = WaitlistEntry
        fields = ['equipment', 'kit', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        equipment = cleaned_data.get('equipment')
        kit = cleaned_data.get('kit')

        if not equipment and not kit:
            raise forms.ValidationError(
                'You must select either a piece of equipment or a kit.'
            )
        if equipment and kit:
            raise forms.ValidationError(
                'Please select either equipment or a kit, not both.'
            )

        return cleaned_data


class ReturnForm(forms.Form):
    """Form for recording the return of a reserved item."""

    CONDITION_CHOICES = [
        ('EXCELLENT', 'Excellent'),
        ('GOOD', 'Good'),
        ('FAIR', 'Fair'),
        ('POOR', 'Poor'),
        ('DAMAGED', 'Damaged'),
    ]

    return_condition = forms.ChoiceField(
        choices=CONDITION_CHOICES,
        initial='GOOD',
        help_text='Condition of the item on return.',
    )
    notes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
        help_text='Any notes about the return (damage, issues, etc.).',
    )
