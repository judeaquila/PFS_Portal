# dashboards/forms.py
from django import forms
from django.contrib.auth import get_user_model

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