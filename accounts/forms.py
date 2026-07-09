from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.core.exceptions import ValidationError
from .models import UserRole


User = get_user_model()

# Login Form
class LoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'placeholder': 'you@company.com',
            'class': 'w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-pink-600 focus:border-pink-600 outline-none transition'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': '••••••••',
            'class': 'w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-pink-600 focus:border-pink-600 outline-none transition'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        password = cleaned_data.get("password")

        # Fallback safeguard if user submits blank values
        if email and password:
            user = authenticate(
                email=email,
                password=password
            )

            if not user:
                raise forms.ValidationError("Invalid email or password.")
            
            # Keep account security airtight: check if disabled
            if not user.is_active:
                raise forms.ValidationError("This account has been deactivated.")
            
            cleaned_data["user"] = user

        return cleaned_data
    


# User Registration Form
class RegistrationForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': '••••••••',
            'class': 'w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-pink-600 focus:border-pink-600 outline-none transition'
        }),
        help_text="Must be at least 8 characters long."
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': '••••••••',
            'class': 'w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-pink-600 focus:border-pink-600 outline-none transition'
        }),
        label="Confirm Password"
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'business_name', 'email', 'whatsapp_number', 'region', 'password']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-pink-600 focus:border-pink-600 outline-none transition'}),
            'last_name': forms.TextInput(attrs={'class': 'w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-pink-600 focus:border-pink-600 outline-none transition'}),
            'business_name': forms.TextInput(attrs={'placeholder': 'e.g. Pneuma Food Scientifics', 'class': 'w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-pink-600 focus:border-pink-600 outline-none transition'}),
            'email': forms.EmailInput(attrs={'placeholder': 'you@company.com', 'class': 'w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-pink-600 focus:border-pink-600 outline-none transition'}),
            'whatsapp_number': forms.TextInput(attrs={'placeholder': 'e.g. 0501234567', 'class': 'w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-pink-600 focus:border-pink-600 outline-none transition'}),
            'region': forms.Select(attrs={'class': 'w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-pink-600 focus:border-pink-600 outline-none transition'}),
        }

    def clean_email(self):
        """Ensure emails are unique across the app."""
        email = self.cleaned_data.get('email').lower()
        if User.objects.filter(email=email).exists():
            raise ValidationError("An account with this email already exists.")
        return email

    def clean_password(self):
        """Enforce standard validation rules on the initial password entry."""
        password = self.cleaned_data.get('password')
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long.")
        return password

    def clean(self):
        """Verify that both password entries match."""
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match!")

        return cleaned_data

    def save(self, commit=True):
        """Overriding save to ensure CustomUserManager hashes the password correctly."""
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        
        if commit:
            user.save()
        return user
    

# Ambassador Registration Form
class AmbassadorRegistrationForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': '••••••••',
            'class': 'w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-pink-600 focus:border-pink-600 outline-none transition'
        }),
        help_text="Must be at least 8 characters long."
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': '••••••••',
            'class': 'w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-pink-600 focus:border-pink-600 outline-none transition'
        }),
        label="Confirm Password"
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'whatsapp_number', 'alternative_number', 'region', 'password']
        widgets = {
            'first_name': forms.TextInput(attrs={'placeholder': 'John', 'class': 'w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-pink-600 focus:border-pink-600 outline-none transition'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Doe', 'class': 'w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-pink-600 focus:border-pink-600 outline-none transition'}),
            'email': forms.EmailInput(attrs={'placeholder': 'you@company.com', 'class': 'w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-pink-600 focus:border-pink-600 outline-none transition'}),
            'whatsapp_number': forms.TextInput(attrs={'placeholder': 'e.g. 0501234567', 'class': 'w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-pink-600 focus:border-pink-600 outline-none transition'}),
            'alternative_number': forms.TextInput(attrs={'placeholder': 'Optional alternative line', 'class': 'w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-pink-600 focus:border-pink-600 outline-none transition'}),
            'region': forms.Select(attrs={'class': 'w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-pink-600 focus:border-pink-600 outline-none transition'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email').lower()
        if User.objects.filter(email=email).exists():
            raise ValidationError("An account with this email already exists.")
        return email

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long.")
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match!")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        
        # Explicit role override protection rule
        user.role = UserRole.AMBASSADOR
        
        if commit:
            user.save()
        return user


# A clean, reusable base mixin to handle styles without duplicating strings
class TailwindFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply theme color dynamically (emerald for consultants)
        theme_focus = "focus:ring-emerald-600 focus:border-emerald-600"
        base_classes = f"w-full px-4 py-2 border border-slate-300 rounded-lg outline-none transition {theme_focus}"
        
        for field_name, field in self.fields.items():
            # Keep check boxes or hidden fields safe from default styling if any exist later
            if not isinstance(field.widget, (forms.CheckboxInput, forms.HiddenInput)):
                existing_classes = field.widget.attrs.get('class', '')
                field.widget.attrs['class'] = f"{base_classes} {existing_classes}".strip()


class ConsultantRegistrationForm(TailwindFormMixin, forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': '••••••••'}),
        help_text="Must be at least 8 characters long."
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': '••••••••'}),
        label="Confirm Password"
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'whatsapp_number', 'alternative_number', 'region', 'password']
        widgets = {
            'first_name': forms.TextInput(attrs={'placeholder': 'Jane'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Smith'}),
            'email': forms.EmailInput(attrs={'placeholder': 'expert@company.com'}),
            'whatsapp_number': forms.TextInput(attrs={'placeholder': 'e.g. 0501234567'}),
            'alternative_number': forms.TextInput(attrs={'placeholder': 'Optional alternative line'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email').lower()
        if User.objects.filter(email=email).exists():
            raise ValidationError("An account with this email already exists.")
        return email

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long.")
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match!")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        user.role = UserRole.CONSULTANT
        
        if commit:
            user.save()
        return user