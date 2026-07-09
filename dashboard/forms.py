# dashboards/forms.py
from django import forms
from django.contrib.auth import get_user_model
from .models import AmbassadorProfile, ConsultantProfile

User = get_user_model()

class ClientProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'whatsapp_number']


class AmbassadorProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'whatsapp_number', 'alternative_number']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-pink-500/20 focus:border-pink-500 outline-none transition-all text-sm'}),
            'last_name': forms.TextInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-pink-500/20 focus:border-pink-500 outline-none transition-all text-sm'}),
            'whatsapp_number': forms.TextInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-pink-500/20 focus:border-pink-500 outline-none transition-all text-sm', 'placeholder': '+233...'}),
            'alternative_number': forms.TextInput(attrs={'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-pink-500/20 focus:border-pink-500 outline-none transition-all text-sm'}),
        }


class AmbassadorBaseUserForm(forms.ModelForm):
    """Handles updating standard contact details on User model."""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'whatsapp_number', 'alternative_number']
        widgets = {
            field: forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-pink-500/20 focus:border-pink-500 outline-none transition-all text-sm'
            }) for field in ['first_name', 'last_name', 'whatsapp_number', 'alternative_number']
        }
        widgets['whatsapp_number'].attrs['placeholder'] = '+233...'


class AmbassadorVerificationForm(forms.ModelForm):
    """Handles verification media upload requirements."""
    class Meta:
        model = AmbassadorProfile
        fields = ['id_card', 'verification_selfie', 'bio']
        widgets = {
            'bio': forms.Textarea(attrs={
                'rows': 3, 
                'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-pink-500/20 focus:border-pink-500 outline-none transition-all text-sm',
                'placeholder': 'Tell us briefly about your experience...'
            }),
            'id_card': forms.FileInput(attrs={'class': 'block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-sm file:font-semibold file:bg-pink-50 file:text-pink-700 hover:file:bg-pink-100'}),
            'verification_selfie': forms.FileInput(attrs={'class': 'block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-sm file:font-semibold file:bg-pink-50 file:text-pink-700 hover:file:bg-pink-100'}),
        }

    
class ConsultantBaseUserForm(forms.ModelForm):
    """Handles updating standard contact details on User model."""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'whatsapp_number', 'alternative_number']
        widgets = {
            field: forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-pink-500/20 focus:border-pink-500 outline-none transition-all text-sm'
            }) for field in ['first_name', 'last_name', 'whatsapp_number', 'alternative_number']
        }
        widgets['whatsapp_number'].attrs['placeholder'] = '+233...'


class ConsultantVerificationForm(forms.ModelForm):
    """Handles verification media upload requirements."""
    class Meta:
        model = ConsultantProfile
        fields = ['cv', 'id_card', 'verification_selfie', 'bio']
        widgets = {
            'bio': forms.Textarea(attrs={
                'rows': 3, 
                'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-pink-500/20 focus:border-pink-500 outline-none transition-all text-sm',
                'placeholder': 'Tell us briefly about your experience...'
            }),
            'id_card': forms.FileInput(attrs={'class': 'block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-sm file:font-semibold file:bg-pink-50 file:text-pink-700 hover:file:bg-pink-100'}),
            'verification_selfie': forms.FileInput(attrs={'class': 'block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-sm file:font-semibold file:bg-pink-50 file:text-pink-700 hover:file:bg-pink-100'}),
            'cv': forms.FileInput(attrs={'class': 'block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-sm file:font-semibold file:bg-pink-50 file:text-pink-700 hover:file:bg-pink-100'}),
        }