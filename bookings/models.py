import os
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError


class AvailabilitySlot(models.Model):
    """
    Slots created by the Administrator defining when meetings can take place.
    """
    admin = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='availability_slots'
    )
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_booked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['date', 'start_time']
        unique_together = ['admin', 'date', 'start_time']

    def __str__(self):
        status = "Booked" if self.is_booked else "Available"
        return f"{self.date} ({self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')}) [{status}]"

    def clean(self):
        super().clean()
        if self.start_time and self.end_time:
            if self.start_time >= self.end_time:
                raise ValidationError({
                    'end_time': "Start time must be before end time."
                })


class Appointment(models.Model):
    """
    Confirmed booking made by a client linked to an AvailabilitySlot.
    """
    class StatusChoices(models.TextChoices):
        SCHEDULED = 'SCHEDULED', 'Scheduled'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    slot = models.OneToOneField(
        AvailabilitySlot, 
        on_delete=models.CASCADE, 
        related_name='appointment'
    )
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='appointments'
    )
    title = models.CharField(max_length=200, help_text="Topic or title of the meeting")
    client_notes = models.TextField(blank=True, null=True, help_text="Initial notes or requirements from client")
    
    # Meeting details populated by Admin
    meeting_link = models.URLField(blank=True, null=True, help_text="Virtual meeting URL (Zoom, Google Meet, Teams, etc.)")
    
    # Post-meeting details
    summary_document = models.FileField(
        upload_to='meeting_summaries/%Y/%m/', 
        blank=True, 
        null=True,
        help_text="PDF or Word document summarizing the meeting"
    )
    meeting_notes = models.TextField(blank=True, null=True, help_text="General text summary or notes")
    
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.SCHEDULED)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-slot__date', '-slot__start_time']

    def __str__(self):
        return f"{self.title} - {self.client.get_full_name() or self.client.first_name} ({self.slot.date})"

    @property
    def summary_filename(self):
        if self.summary_document:
            return os.path.basename(self.summary_document.name)
        return ""


class ActionItem(models.Model):
    """
    To-Do items generated during/after the meeting.
    Admin manages these; Client sees them as read-only.
    """
    appointment = models.ForeignKey(
        Appointment, 
        on_delete=models.CASCADE, 
        related_name='action_items'
    )
    task = models.CharField(max_length=255)
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.task} ({'Done' if self.is_completed else 'Pending'})"


class InAppNotification(models.Model):
    """
    In-app notification system for reminders and updates.
    """
    class NotificationTypes(models.TextChoices):
        BOOKING_CONFIRMED = "BOOKING CONFIRMED", 'Booking Confirmed'
        LINK_ADDED = "LINK ADDED", 'Meeting Link Added'
        REMINDER = "REMINDER", 'Upcoming Meeting Reminder'
        SUMMARY_READY = "SUMMARY READY", 'Meeting Summary & Action Items Ready'

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='in_app_notifications'
    )
    appointment = models.ForeignKey(
        Appointment, 
        on_delete=models.CASCADE, 
        related_name='notifications',
        null=True,
        blank=True
    )
    title = models.CharField(max_length=150)
    message = models.TextField()
    notification_type = models.CharField(max_length=30, choices=NotificationTypes.choices)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.recipient.first_name}: {self.title}"


class NewClientPackage(models.Model):
    """
    Master package model representing the primary compliance tracks/tiers.
    """
    code = models.CharField(
        max_length=50, 
        unique=True, 
        help_text="Unique key (e.g., BASIC_ALL, ADVANCED_PLUS_FOOD)"
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    price_ghs = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Package price in GHS")
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['display_order', 'name']

    def __str__(self):
        return f"{self.name} - GHS {self.price_ghs:,.2f} ({self.code})"


class BlueprintSubactivity(models.Model):
    """
    Template subactivities tied to a ClientPackage blueprint.
    """
    package = models.ForeignKey(
        NewClientPackage, 
        on_delete=models.CASCADE, 
        related_name='blueprint_subactivities'
    )
    activity_name = models.CharField(max_length=255)
    scope = models.CharField(max_length=100, blank=True, null=True, help_text="e.g. 1 Product, 1 Facility, 10 SOPs")
    sort_order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['package', 'sort_order']
        unique_together = ('package', 'activity_name')

    def __str__(self):
        return f"{self.package.code} - Step {self.sort_order}: {self.activity_name}"


class NewClientProject(models.Model):
    """
    Client project instance pointing to a selected ClientPackage row.
    """
    class PaymentStatus(models.TextChoices):
            NOT_PAID = 'NOT_PAID', 'Not Paid'
            PART_PAYMENT = 'PART_PAYMENT', 'Part Payment'
            INCLUDED = 'INCLUDED', 'Included in Package'
            PAID = 'PAID', 'Paid'

    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    client_package = models.ForeignKey(
        NewClientPackage, 
        on_delete=models.PROTECT, 
        related_name='projects'
    )
    assigned_staff = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_client_projects',
        help_text="Staff assigned to manage this project"
    )
    amount_paid_ghs = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Amount paid by the client in GHS")
    payment_status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.NOT_PAID)

    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def progress_percentage(self):
        acts = list(self.activities.all())
        total = len(acts)
        if total == 0:
            return 0
        completed = sum(1 for a in acts if a.activity_status == 'COMPLETED')
        return int((completed / total) * 100)

    @property
    def package_price_ghs(self):
        return self.client_package.price_ghs

    @property
    def balance_due_ghs(self):
        return max(0.00, float(self.package_price_ghs) - float(self.amount_paid_ghs))

    def __str__(self):
        return self.title


class NewProjectActivity(models.Model):
    class ActivityStatus(models.TextChoices):
        NOT_STARTED = 'NOT_STARTED', 'Not Started'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        COMPLETED = 'COMPLETED', 'Completed'

    class PaymentStatus(models.TextChoices):
        NOT_PAID = 'NOT_PAID', 'Not Paid'
        INCLUDED = 'INCLUDED', 'Included in Package'
        PAID = 'PAID', 'Paid'

    project = models.ForeignKey(NewClientProject, on_delete=models.CASCADE, related_name='activities')
    activity_name = models.CharField(max_length=255)
    scope = models.CharField(max_length=100, blank=True, null=True)
    activity_status = models.CharField(
        max_length=50, 
        choices=ActivityStatus.choices, 
        default=ActivityStatus.NOT_STARTED
    )
    payment_status = models.CharField(
        max_length=50, 
        choices=PaymentStatus.choices, 
        default=PaymentStatus.INCLUDED
    )

    def __str__(self):
        return f"{self.project.title} - {self.activity_name}"


class AddOnService(models.Model):
    """
    Add-on activities available outside of default package scopes.
    """
    name = models.CharField(max_length=255)
    price_ghs = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} (GHS {self.price_ghs:,.2f})"