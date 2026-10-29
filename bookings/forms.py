from django import forms
from django.utils import timezone
from .models import AvailabilitySlot, Appointment, ActionItem, NewClientPackage, NewClientProject
from accounts.models import User, UserRole


class AvailabilitySlotForm(forms.ModelForm):
    """Form to create a single availability slot."""
    class Meta:
        model = AvailabilitySlot
        fields = ['date', 'start_time', 'end_time']
        widgets = {
            'date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full rounded-lg border-gray-300 bg-white text-gray-900 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
            }),
            'start_time': forms.TimeInput(attrs={
                'type': 'time',
                'class': 'w-full rounded-lg border-gray-300 bg-white text-gray-900 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
            }),
            'end_time': forms.TimeInput(attrs={
                'type': 'time',
                'class': 'w-full rounded-lg border-gray-300 bg-white text-gray-900 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
            }),
        }

    def clean_date(self):
        date = self.cleaned_data.get('date')
        if date and date < timezone.now().date():
            raise forms.ValidationError("You cannot create slots in the past.")
        return date

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start_time')
        end = cleaned_data.get('end_time')

        if start and end and start >= end:
            raise forms.ValidationError("End time must be strictly after start time.")
        return cleaned_data


class BulkSlotForm(forms.Form):
    """Form to quickly generate multiple slots for a single day."""
    date = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'w-full rounded-lg border-gray-300 bg-white text-gray-900 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
        })
    )
    start_time = forms.TimeField(
        widget=forms.TimeInput(attrs={
            'type': 'time',
            'class': 'w-full rounded-lg border-gray-300 bg-white text-gray-900 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
        })
    )
    end_time = forms.TimeField(
        widget=forms.TimeInput(attrs={
            'type': 'time',
            'class': 'w-full rounded-lg border-gray-300 bg-white text-gray-900 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
        })
    )
    slot_duration = forms.IntegerField(
        initial=30,
        min_value=15,
        max_value=120,
        help_text="Duration in minutes",
        widget=forms.NumberInput(attrs={
            'class': 'w-full rounded-lg border-gray-300 bg-white text-gray-900 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
        })
    )


class ClientBookingForm(forms.ModelForm):
    """Form used by clients to reserve an available slot."""
    class Meta:
        model = Appointment
        fields = ['title', 'client_notes']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full rounded-lg border-gray-300 bg-white text-gray-900 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm',
                'placeholder': 'e.g., Initial Business Consultation'
            }),
            'client_notes': forms.Textarea(attrs={
                'rows': 3,
                'class': 'w-full rounded-lg border-gray-300 bg-white text-gray-900 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm',
                'placeholder': 'Mention key goals or questions for this meeting...'
            }),
        }


class AdminMeetingUpdateForm(forms.ModelForm):
    """Form for admins to attach virtual meeting link, notes, document summaries, and change status."""
    class Meta:
        model = Appointment
        fields = ['meeting_link', 'meeting_notes', 'summary_document', 'status']
        widgets = {
            'meeting_link': forms.URLInput(attrs={
                'class': 'w-full rounded-lg border-gray-300 bg-white text-gray-900 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm',
                'placeholder': 'https://zoom.us/j/... or https://meet.google.com/...'
            }),
            'meeting_notes': forms.Textarea(attrs={
                'rows': 3,
                'class': 'w-full rounded-lg border-gray-300 bg-white text-gray-900 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm',
                'placeholder': 'Key points discussed during the meeting...'
            }),
            'summary_document': forms.FileInput(attrs={
                'class': 'w-full text-xs text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100'
            }),
            'status': forms.Select(attrs={
                'class': 'w-full rounded-lg border-gray-300 bg-white text-gray-900 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
            }),
        }


class ActionItemForm(forms.ModelForm):
    """Form to create or update To-Do action items."""
    class Meta:
        model = ActionItem
        fields = ['task', 'is_completed']
        widgets = {
            'task': forms.TextInput(attrs={
                'class': 'w-full rounded-lg border-gray-300 bg-white text-gray-900 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm',
                'placeholder': 'New action item...'
            }),
            'is_completed': forms.CheckboxInput(attrs={
                'class': 'rounded border-gray-300 text-indigo-600 shadow-sm focus:border-indigo-500 focus:ring-indigo-500'
            }),
        }


class InitiateProjectForm(forms.ModelForm):
    client = forms.ModelChoiceField(
        queryset=User.objects.filter(role=UserRole.USER),
        widget=forms.Select(
            attrs={
                "class": "w-full rounded-xl border border-slate-200 px-4 py-2.5 text-sm text-slate-800 bg-slate-50/50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition"
            }
        ),
        empty_label="Select a client...",
    )

    client_package = forms.ChoiceField(
        widget=forms.Select(
            attrs={
                "class": "w-full rounded-xl border border-slate-200 px-4 py-2.5 text-sm text-slate-800 bg-slate-50/50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition",
                "x-model": "selectedPackageCode",
            }
        )
    )

    assigned_staff = forms.ModelChoiceField(
        queryset=User.objects.filter(role=UserRole.ASSOCIATE_2),
        required=False,
        widget=forms.Select(
            attrs={
                "class": "w-full rounded-xl border border-slate-200 px-4 py-2.5 text-sm text-slate-800 bg-slate-50/50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition"
            }
        ),
        empty_label="Assign staff member...",
    )

    amount_paid_ghs = forms.DecimalField(
        initial=0.00,
        required=False,
        widget=forms.NumberInput(
            attrs={
                "placeholder": "0.00",
                "class": "w-full rounded-xl border border-slate-200 px-4 py-2.5 text-sm text-slate-800 bg-slate-50/50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition"
            }
        )
    )

    class Meta:
        model = NewClientProject
        fields = ["client", "client_package", "assigned_staff", "amount_paid_ghs", "title", "description"]
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "placeholder": "e.g. Organic Shea Body Butter FDA Compliance",
                    "class": "w-full rounded-xl border border-slate-200 px-4 py-2.5 text-sm text-slate-800 bg-slate-50/50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "Add optional details regarding client specifications or target regulatory timelines...",
                    "class": "w-full rounded-xl border border-slate-200 px-4 py-2.5 text-sm text-slate-800 bg-slate-50/50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        client_obj = kwargs.pop('client_obj', None)
        super().__init__(*args, **kwargs)

        # Populate ChoiceField options using package codes and formatted prices
        packages = NewClientPackage.objects.all().order_by('display_order', 'name')
        self.fields['client_package'].choices = [
            (pkg.code, f"{pkg.name} — GHS {pkg.price_ghs:,.2f}" if pkg.price_ghs > 0 else f"{pkg.name} — Custom")
            for pkg in packages
        ]

        # Handle initial value if editing an existing project
        if self.instance and self.instance.pk and self.instance.client_package:
            self.fields['client_package'].initial = self.instance.client_package.code

        # Filter assigned staff strictly to Associate 2 staff members
        self.fields['assigned_staff'].queryset = User.objects.filter(
            role=UserRole.ASSOCIATE_2
        ).order_by('first_name', 'last_name')

        # Lock client field if target client is supplied
        if client_obj:
            self.fields['client'].queryset = User.objects.filter(id=client_obj.id, role=UserRole.USER)
            self.fields['client'].initial = client_obj
            self.fields['client'].widget = forms.HiddenInput()

    def clean_client_package(self):
        """Converts the submitted package code string back into a NewClientPackage database instance."""
        code = self.cleaned_data.get('client_package')
        try:
            return NewClientPackage.objects.get(code=code)
        except NewClientPackage.DoesNotExist:
            raise forms.ValidationError("Please select a valid service package.")