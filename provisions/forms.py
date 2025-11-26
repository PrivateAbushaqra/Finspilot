from django import forms
from django.utils.translation import gettext_lazy as _
from .models import ProvisionType, Provision, ProvisionEntry
from journal.models import Account


class ProvisionTypeForm(forms.ModelForm):
    class Meta:
        model = ProvisionType
        fields = ['name', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ProvisionForm(forms.ModelForm):
    class Meta:
        model = Provision
        fields = ['provision_type', 'custom_type', 'name', 'description', 'related_account', 'provision_account', 'amount', 'fiscal_year', 'start_date', 'end_date', 'is_active']
        widgets = {
            'provision_type': forms.Select(attrs={'class': 'form-control'}),
            'custom_type': forms.Select(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'related_account': forms.Select(attrs={'class': 'form-control'}),
            'provision_account': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'fiscal_year': forms.NumberInput(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter active accounts
        self.fields['related_account'].queryset = Account.objects.filter(is_active=True)
        self.fields['provision_account'].queryset = Account.objects.filter(is_active=True)


class ProvisionEntryForm(forms.ModelForm):
    class Meta:
        model = ProvisionEntry
        fields = ['provision', 'date', 'amount', 'description']
        widgets = {
            'provision': forms.Select(attrs={'class': 'form-control'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }