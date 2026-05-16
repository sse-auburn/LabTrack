"""Forms for the borrowing app."""

from django import forms
from django.utils import timezone

from apps.borrowing.models import BorrowRequest
from apps.equipment.models import Equipment
from apps.kits.models import Kit
from apps.reservations.models import Reservation


class BorrowRequestForm(forms.ModelForm):
    """Form for creating a borrow request for a piece of equipment or a kit."""

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
        model = BorrowRequest
        fields = ['equipment', 'kit', 'purpose', 'due_date']
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            'purpose': forms.Textarea(attrs={'rows': 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        equipment = cleaned_data.get('equipment')
        kit = cleaned_data.get('kit')
        due_date = cleaned_data.get('due_date')

        # Exactly one of equipment or kit must be selected.
        if not equipment and not kit:
            raise forms.ValidationError(
                'You must select either a piece of equipment or a kit.'
            )
        if equipment and kit:
            raise forms.ValidationError(
                'Please select either equipment or a kit, not both.'
            )

        # Validate equipment availability.
        # RESERVED is handled by the date-overlap check below — a future reservation
        # must not block a borrow whose due_date falls before the reservation starts.
        if equipment and equipment.status in ('BORROWED', 'MAINTENANCE', 'DAMAGED', 'RETIRED'):
            raise forms.ValidationError(
                f'"{equipment.name}" is currently not available '
                f'(status: {equipment.get_status_display()}).'
            )

        # Validate kit availability.
        if kit:
            unavailable = [
                item.equipment.name
                for item in kit.items.select_related('equipment')
                if item.equipment.status in ('BORROWED', 'MAINTENANCE', 'DAMAGED', 'RETIRED')
            ]
            if unavailable:
                raise forms.ValidationError(
                    f'The following items in kit "{kit.name}" are not available: '
                    + ', '.join(unavailable)
                )

        # Due date must be in the future.
        if due_date and due_date < timezone.now().date():
            raise forms.ValidationError('Due date must be today or a future date.')

        # Check for conflicting confirmed reservations.
        # A borrow from today through due_date conflicts with a reservation if:
        # reservation.start_date <= due_date AND reservation.end_date >= today
        today = timezone.now().date()
        if equipment and due_date:
            conflict = Reservation.objects.filter(
                equipment=equipment,
                status='CONFIRMED',
                start_date__lte=due_date,
                end_date__gte=today,
            ).first()
            if conflict:
                raise forms.ValidationError(
                    f'"{equipment.name}" has a confirmed reservation from '
                    f'{conflict.start_date} to {conflict.end_date}. '
                    f'Your due date must be before {conflict.start_date}.'
                )

        if kit and due_date:
            for kit_item in kit.items.select_related('equipment'):
                conflict = Reservation.objects.filter(
                    equipment=kit_item.equipment,
                    status='CONFIRMED',
                    start_date__lte=due_date,
                    end_date__gte=today,
                ).first()
                if conflict:
                    raise forms.ValidationError(
                        f'"{kit_item.equipment.name}" (in kit "{kit.name}") has a confirmed '
                        f'reservation from {conflict.start_date} to {conflict.end_date}. '
                        f'Your due date must be before {conflict.start_date}.'
                    )

        return cleaned_data


class BulkBorrowForm(forms.Form):
    """Shared purpose/due_date when borrowing multiple equipment items at once."""

    purpose = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        help_text='Why are you borrowing these items?',
    )
    due_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        help_text='Return all items by this date.',
    )

    def clean_due_date(self):
        due_date = self.cleaned_data.get('due_date')
        if due_date and due_date < timezone.now().date():
            raise forms.ValidationError('Due date must be today or a future date.')
        return due_date


class ReturnForm(forms.Form):
    """Form for recording the return of borrowed equipment or a kit."""

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
