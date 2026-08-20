from django import forms
from django.utils import timezone
from .models import PaymentRequest

class HistoricalPaymentRequestForm(forms.ModelForm):
    """Allows Superadmins to backdate custom payments for existing clients."""
    
    paid_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
        help_text="Select the date when this payment was made in the past."
    )

    class Meta:
        model = PaymentRequest
        fields = ['service_name', 'amount', 'payment_method', 'note', 'admin_notes']
        widgets = {
            'service_name': forms.TextInput(attrs={'placeholder': 'e.g. FDA Inspection Fee (Pre-platform)'}),
            'amount': forms.NumberInput(attrs={'placeholder': '0.00', 'step': '0.01'}),
            'note': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Breakdown shown to client'}),
            'admin_notes': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Internal migration memo'}),
        }

    def save(self, user, created_by, commit=True):
        instance = super().save(commit=False)
        instance.user = user
        instance.created_by = created_by
        instance.status = PaymentRequest.StatusType.PAID
        
        # Combine selected date with current time for accurate DateTime field
        paid_date = self.cleaned_data.get('paid_date')
        if paid_date:
            # Gets current local time safely
            current_time = timezone.localtime().time()
            
            # Combines date + time as a naive datetime, then makes it aware
            naive_dt = timezone.datetime.combine(paid_date, current_time)
            instance.paid_at = timezone.make_aware(naive_dt, timezone.get_current_timezone())
        
        if commit:
            instance.save()
        return instance