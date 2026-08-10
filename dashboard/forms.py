from django import forms
from django.contrib.auth import get_user_model
from .models import AmbassadorProfile, ConsultantProfile, Availability
from django.forms import ModelForm, modelformset_factory


User = get_user_model()


class TailwindFormMixin:
    """Reusable mixin to inject styled Tailwind classes across management forms."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        base_input = "w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-pink-500/20 focus:border-pink-500 outline-none transition-all text-sm"
        
        for field_name, field in self.fields.items():
            if isinstance(field.widget, (forms.FileInput,)):
                field.widget.attrs['class'] = 'block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-sm file:font-semibold file:bg-pink-50 file:text-pink-700 hover:file:bg-pink-100'
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'w-5 h-5 accent-pink-600 rounded cursor-pointer'
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs['class'] = f"{base_input} resize-none"
            else:
                field.widget.attrs['class'] = base_input


class BaseUserProfileForm(TailwindFormMixin, forms.ModelForm):
    """Base form for updating standard contact details across user roles."""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'whatsapp_number', 'alternative_number']
        widgets = {
            'whatsapp_number': forms.TextInput(attrs={'placeholder': '+233...'}),
            'alternative_number': forms.TextInput(attrs={'placeholder': 'Optional line'}),
        }


class ClientProfileForm(BaseUserProfileForm):
    """
    Profile form specifically for regular Client/User accounts.
    Inherits fields from BaseUserProfileForm. Add extra client-only fields here if needed.
    """
    pass


class AmbassadorVerificationForm(TailwindFormMixin, forms.ModelForm):
    """Handles verification media upload requirements for Ambassadors."""
    class Meta:
        model = AmbassadorProfile
        fields = ['id_card', 'verification_selfie', 'bio']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Tell us briefly about your experience...'}),
        }


class ConsultantVerificationForm(TailwindFormMixin, forms.ModelForm):
    """Handles verification media upload requirements for Consultants."""
    class Meta:
        model = ConsultantProfile
        fields = ['cv', 'id_card', 'verification_selfie', 'bio']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Tell us briefly about your experience...'}),
        }


class AdminUserManagementForm(TailwindFormMixin, forms.ModelForm):
    """Allows Superadmin/Admin to update core credentials, role, and active status."""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'whatsapp_number', 'alternative_number', 'role', 'is_active', 'is_staff']
        widgets = {
            'whatsapp_number': forms.TextInput(attrs={'placeholder': '+233...'}),
        }

    def clean_email(self):
        """Ensure email uniqueness excluding current instance."""
        email = self.cleaned_data.get('email')
        if email:
            email = email.lower()
            if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError("Another account with this email address already exists.")
        return email


class BusinessProfileForm(forms.ModelForm):
    """Form to allow clients to update their company and sector details."""
    
    class Meta:
        model = User
        fields = ['business_name', 'company_logo', 'sector', 'region', 'whatsapp_number']
        widgets = {
            'business_name': forms.TextInput(attrs={
                'class': 'w-full rounded-lg border border-slate-300 px-4 py-2.5 text-sm focus:border-pink-500 focus:ring-1 focus:ring-pink-500 transition',
                'placeholder': 'e.g., Pneuma Food Scientifics'
            }),
            'company_logo': forms.FileInput(attrs={
                'class': 'w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-pink-500 focus:ring-1 focus:ring-pink-500 transition text-slate-500 file:mr-4 file:py-1.5 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-pink-50 file:text-pink-700 hover:file:bg-pink-100 cursor-pointer',
                'accept': 'image/*'
            }),
            'sector': forms.Select(attrs={
                'class': 'w-full rounded-lg border border-slate-300 px-4 py-2.5 text-sm focus:border-pink-500 focus:ring-1 focus:ring-pink-500 transition bg-white'
            }),
            'region': forms.Select(attrs={
                'class': 'w-full rounded-lg border border-slate-300 px-4 py-2.5 text-sm focus:border-pink-500 focus:ring-1 focus:ring-pink-500 transition bg-white'
            }),
            'whatsapp_number': forms.TextInput(attrs={
                'class': 'w-full rounded-lg border border-slate-300 px-4 py-2.5 text-sm focus:border-pink-500 focus:ring-1 focus:ring-pink-500 transition',
                'placeholder': 'e.g., 0501234567'
            }),
        }


# Availability Form
class AvailabilityForm(forms.ModelForm):
    class Meta:
        model = Availability
        fields = (
            "weekday",
            "start_time",
            "end_time",
        )

        widgets = {
            "weekday": forms.Select(
                attrs={
                    "class": "w-full rounded-lg border-slate-300"
                }
            ),
            "start_time": forms.TimeInput(
                attrs={
                    "type": "time",
                    "class": "w-full rounded-lg border-slate-300"
                }
            ),
            "end_time": forms.TimeInput(
                attrs={
                    "type": "time",
                    "class": "w-full rounded-lg border-slate-300"
                }
            ),
        }

    def clean(self):
        cleaned = super().clean()

        start = cleaned.get("start_time")
        end = cleaned.get("end_time")

        if start and end and end <= start:
            raise forms.ValidationError(
                "End time must be later than the start time."
            )

        return cleaned