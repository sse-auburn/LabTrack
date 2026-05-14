"""Forms for the P-Card app."""

from django import forms
from django.forms import inlineformset_factory

from apps.pcard.models import PcardItem, PcardTransaction


class PcardTransactionForm(forms.ModelForm):
    """Create or edit a P-Card transaction."""

    class Meta:
        model = PcardTransaction
        fields = ('transaction_date', 'total_price', 'receipt_file', 'notes')
        widgets = {
            'transaction_date': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date',
            }),
            'total_price': forms.NumberInput(attrs={
                'class': 'form-input',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0',
            }),
            'receipt_file': forms.ClearableFileInput(attrs={
                'class': 'form-file-input',
                'accept': 'image/*,application/pdf',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Optional notes about this purchase…',
            }),
        }

    def clean_total_price(self):
        total = self.cleaned_data.get('total_price')
        if total is not None and total < 0:
            raise forms.ValidationError('Total price cannot be negative.')
        return total


class PcardItemForm(forms.ModelForm):
    """Create or edit an item line within a P-Card transaction."""

    class Meta:
        model = PcardItem
        fields = ('name', 'description', 'quantity', 'unit_price')
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Item name',
            }),
            'description': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Description (optional)',
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': '1',
                'step': '1',
            }),
            'unit_price': forms.NumberInput(attrs={
                'class': 'form-input',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0',
            }),
        }

    def clean_quantity(self):
        qty = self.cleaned_data.get('quantity')
        if qty is not None and qty < 1:
            raise forms.ValidationError('Quantity must be at least 1.')
        return qty


PcardItemFormSet = inlineformset_factory(
    PcardTransaction,
    PcardItem,
    form=PcardItemForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True,
)


class PcardFilterForm(forms.Form):
    """Non-model form for filtering P-Card transactions by date."""

    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-input',
            'type': 'date',
        }),
        label='From',
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-input',
            'type': 'date',
        }),
        label='To',
    )
