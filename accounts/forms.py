from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.core.exceptions import ValidationError
from .models import UserRole

User = get_user_model()


# ==============================================================================
# BASE MIXINS & CLASSES
# ==============================================================================

class TailwindFormMixin:
    """
    Reusable mixin to automatically inject Tailwind CSS classes into form widgets.
    Allows overriding theme_focus_class for different form variants.
    """
    theme_focus_class = "focus:ring-pink-600 focus:border-pink-600"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        base_classes = (
            f"w-full px-4 py-2 border border-slate-300 rounded-lg outline-none transition {self.theme_focus_class}"
        )

        for field_name, field in self.fields.items():
            if not isinstance(field.widget, (forms.CheckboxInput, forms.HiddenInput)):
                existing_classes = field.widget.attrs.get('class', '')
                field.widget.attrs['class'] = f"{base_classes} {existing_classes}".strip()


class BaseUserRegistrationForm(TailwindFormMixin, forms.ModelForm):
    """
    Base registration form handling core validation (email uniqueness, password length,
    matching passwords) and hashed password saving across all user roles.
    """
    assigned_role = UserRole.USER

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
        fields = ['first_name', 'last_name', 'email', 'whatsapp_number', 'region', 'password']

    def clean_email(self):
        """Safely check email uniqueness without throwing AttributeError on empty inputs."""
        email = self.cleaned_data.get('email')
        if not email:
            return email

        email = email.lower()
        if User.objects.filter(email=email).exists():
            raise ValidationError("An account with this email already exists.")
        return email

    def clean_password(self):
        """Enforce password length safely without throwing TypeError on empty inputs."""
        password = self.cleaned_data.get('password')
        if password and len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long.")
        return password

    def clean(self):
        """Ensure password and confirm_password match."""
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match!")

        return cleaned_data

    def save(self, commit=True):
        """Hash password and set explicit role prior to saving."""
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        user.role = self.assigned_role

        if commit:
            user.save()
        return user


# ==============================================================================
# AUTHENTICATION FORMS
# ==============================================================================

class LoginForm(TailwindFormMixin, forms.Form):
    """Form to handle authentication and active status validation."""
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'placeholder': 'you@company.com'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': '••••••••'})
    )

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        password = cleaned_data.get("password")

        if email and password:
            user = authenticate(email=email, password=password)

            if not user:
                raise forms.ValidationError("Invalid email or password.")

            if not user.is_active:
                raise forms.ValidationError("This account has been deactivated.")

            cleaned_data["user"] = user

        return cleaned_data


# ==============================================================================
# REGISTRATION FORMS
# ==============================================================================

class RegistrationForm(BaseUserRegistrationForm):
    """Standard Client/User registration form."""
    assigned_role = UserRole.USER

    class Meta(BaseUserRegistrationForm.Meta):
        fields = ['first_name', 'last_name', 'business_name', 'email', 'whatsapp_number', 'sector', 'region', 'password']
        widgets = {
            'first_name': forms.TextInput(attrs={'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Last Name'}),
            'business_name': forms.TextInput(attrs={'placeholder': 'e.g. Pneuma Food Scientifics'}),
            'email': forms.EmailInput(attrs={'placeholder': 'you@company.com'}),
            'whatsapp_number': forms.TextInput(attrs={'placeholder': 'e.g. 0501234567'}),
            'alternative_number': forms.TextInput(attrs={'placeholder': 'For calls: e.g. 0501234567'}),
            'region': forms.Select(),
            'sector': forms.Select(),
        }


class AmbassadorRegistrationForm(BaseUserRegistrationForm):
    """Ambassador registration form."""
    assigned_role = UserRole.AMBASSADOR

    class Meta(BaseUserRegistrationForm.Meta):
        fields = ['first_name', 'last_name', 'email', 'whatsapp_number', 'alternative_number', 'region', 'password']
        widgets = {
            'first_name': forms.TextInput(attrs={'placeholder': 'John'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Doe'}),
            'email': forms.EmailInput(attrs={'placeholder': 'you@company.com'}),
            'whatsapp_number': forms.TextInput(attrs={'placeholder': 'e.g. 0501234567'}),
            'alternative_number': forms.TextInput(attrs={'placeholder': 'Optional alternative line'}),
            'region': forms.Select(),
        }


class ConsultantRegistrationForm(BaseUserRegistrationForm):
    """Consultant registration form with emerald accent theme."""
    assigned_role = UserRole.CONSULTANT
    theme_focus_class = "focus:ring-emerald-600 focus:border-emerald-600"

    class Meta(BaseUserRegistrationForm.Meta):
        fields = ['first_name', 'last_name', 'email', 'whatsapp_number', 'alternative_number', 'region', 'password']
        widgets = {
            'first_name': forms.TextInput(attrs={'placeholder': 'Jane'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Smith'}),
            'email': forms.EmailInput(attrs={'placeholder': 'expert@company.com'}),
            'whatsapp_number': forms.TextInput(attrs={'placeholder': 'e.g. 0501234567'}),
            'alternative_number': forms.TextInput(attrs={'placeholder': 'Optional alternative line'}),
            'region': forms.Select(),
        }