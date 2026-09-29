from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator

from accounts.models import UserRole
from dashboard.models import ClientProject
from payments.models import PaymentRequest, Payment


# ==========================================
# 1. ENUMS & CHOICES
# ==========================================

class FDAActivityStatus(models.TextChoices):
    COMPLETE = 'COMPLETE', _('Complete')
    ONGOING = 'ONGOING', _('Ongoing')
    WAITING_INTERNAL = 'WAITING_INTERNAL', _('Waiting Internal')
    WAITING_EXTERNAL = 'WAITING_EXTERNAL', _('Waiting External')
    DISCONTINUED = 'DISCONTINUED', _('Discontinued')
    ON_HOLD = 'ON_HOLD', _('On Hold')
    NOT_APPLICABLE = 'NOT_APPLICABLE', _('Not Applicable')


class FDAPaymentGateStatus(models.TextChoices):
    TO_CONFIRM = 'TO_CONFIRM', _('To Confirm')
    PENDING = 'PENDING', _('Pending')
    PART_PAID = 'PART_PAID', _('Part Paid')
    PAID = 'PAID', _('Paid')
    WAIVED = 'WAIVED', _('Waived')
    NOT_REQUIRED = 'NOT_REQUIRED', _('Not Required')


class FDAWorkClearance(models.TextChoices):
    CLEARED = 'CLEARED', _('CLEARED TO PROCEED')
    PAYMENT_PENDING = 'PAYMENT_PENDING', _('PAYMENT PENDING - DO NOT START')
    PAYMENT_FOLLOW_UP = 'PAYMENT_FOLLOW_UP', _('PAYMENT FOLLOW-UP')
    FOLLOW_UP_EXTERNAL = 'FOLLOW_UP_EXTERNAL', _('FOLLOW UP EXTERNAL')
    ON_HOLD = 'ON_HOLD', _('ON HOLD - DO NOT START')


class PaymentScope(models.TextChoices):
    STAGE_LEVEL = 'STAGE', _('Stage Level')
    PROJECT_LEVEL = 'PROJECT', _('Project Level')


# ==========================================
# 2. MASTER WORKFLOW CONFIGURATION
# ==========================================

class FDAWorkflowStage(models.Model):
    """
    Corresponds to the 'Setup' tab: Master list of 20 stages (5% to 100%).
    """
    stage_number = models.PositiveIntegerField(
        unique=True, 
        validators=[MinValueValidator(1), MaxValueValidator(20)]
    )
    stage_percentage = models.PositiveIntegerField(
        validators=[MinValueValidator(5), MaxValueValidator(100)]
    )
    full_activity_name = models.CharField(max_length=255)
    short_stage_name = models.CharField(max_length=100)
    
    assigned_role = models.CharField(
        max_length=30, 
        choices=UserRole.choices,
        default=UserRole.ASSOCIATE_1
    )
    default_payment_check = models.BooleanField(
        default=False, 
        help_text="Requires payment gate check by default"
    )

    class Meta:
        ordering = ['stage_number']
        verbose_name = "FDA Workflow Stage"
        verbose_name_plural = "FDA Workflow Stages"

    def __str__(self):
        return f"Stage {self.stage_number} ({self.stage_percentage}%): {self.short_stage_name}"


# ==========================================
# 3. TRACKER MATRIX (PER CLIENT PROJECT)
# ==========================================

class FDAProjectTracker(models.Model):
    """
    Integrates with dashboard.ClientProject. Represents a client's 20-stage tracker sheet row.
    """
    project = models.OneToOneField(
        ClientProject, 
        on_delete=models.CASCADE, 
        related_name='fda_tracker'
    )
    last_contacted = models.DateField(blank=True, null=True)
    latest_update_blocker = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"FDA Tracker - {self.project.client.business_name or self.project.client.email}"

    @property
    def highest_stage_percentage(self):
        """Calculates highest completed or ongoing stage percentage."""
        completed_or_active = self.stage_activities.filter(
            status__in=[FDAActivityStatus.COMPLETE, FDAActivityStatus.ONGOING]
        ).select_related('stage')
        if not completed_or_active.exists():
            return 0
        return max(activity.stage.stage_percentage for activity in completed_or_active)

    @property
    def active_stages(self):
        """Returns queryset of ongoing stages."""
        return self.stage_activities.filter(status=FDAActivityStatus.ONGOING)

    @property
    def active_handlers(self):
        """Returns list of users assigned to active stages."""
        roles = self.active_stages.values_list('stage__assigned_role', flat=True)
        return settings.AUTH_USER_MODEL.objects.filter(role__in=roles).distinct()

    @property
    def has_payment_alert(self):
        """Checks if there are pending payment gates."""
        return self.payment_gates.filter(
            status__in=[FDAPaymentGateStatus.PENDING, FDAPaymentGateStatus.TO_CONFIRM]
        ).exists()


class FDAProjectStageActivity(models.Model):
    """
    Individual activity cell for a project stage (Client Project x Stage).
    """
    tracker = models.ForeignKey(
        FDAProjectTracker, 
        on_delete=models.CASCADE, 
        related_name='stage_activities'
    )
    stage = models.ForeignKey(FDAWorkflowStage, on_delete=models.CASCADE)
    status = models.CharField(
        max_length=20, 
        choices=FDAActivityStatus.choices, 
        default=FDAActivityStatus.NOT_APPLICABLE
    )
    handler_override = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='assigned_fda_activities',
        help_text="Overrides default workflow role handler if set."
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('tracker', 'stage')
        ordering = ['stage__stage_number']
        verbose_name_plural = "FDA Project Stage Activities"

    def __str__(self):
        return f"{self.tracker.project.client.business_name} - {self.stage.short_stage_name}: {self.get_status_display()}"


# ==========================================
# 4. PAYMENT REGISTER & CLEARANCE GATE
# ==========================================

class FDAPaymentGate(models.Model):
    """
    Tracks financial clearances for stages or overall projects.
    Links directly to payments.PaymentRequest or payments.Payment for verification.
    """
    tracker = models.ForeignKey(
        FDAProjectTracker, 
        on_delete=models.CASCADE, 
        related_name='payment_gates'
    )
    scope = models.CharField(
        max_length=10, 
        choices=PaymentScope.choices, 
        default=PaymentScope.STAGE_LEVEL
    )
    stage = models.ForeignKey(
        FDAWorkflowStage, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    payment_required = models.BooleanField(default=True)
    amount_due = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    status = models.CharField(
        max_length=20, 
        choices=FDAPaymentGateStatus.choices, 
        default=FDAPaymentGateStatus.PENDING
    )
    
    # Links to existing payment records
    payment_request = models.ForeignKey(
        PaymentRequest, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='fda_gates'
    )
    verified_payment = models.ForeignKey(
        Payment, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='fda_gates'
    )
    
    date_paid = models.DateField(blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        scope_lbl = f"Stage {self.stage.stage_number}" if self.scope == PaymentScope.STAGE_LEVEL and self.stage else "Project-Level"
        return f"{self.tracker.project.client.business_name} ({scope_lbl}) - {self.get_status_display()}"

    def compute_work_clearance(self, activity_status):
        """
        Calculates operational clearance based on payment state and activity status.
        """
        if activity_status == FDAActivityStatus.ON_HOLD:
            return FDAWorkClearance.ON_HOLD
        if self.payment_required and self.status == FDAPaymentGateStatus.PENDING:
            return FDAWorkClearance.PAYMENT_PENDING
        if self.status == FDAPaymentGateStatus.TO_CONFIRM:
            return FDAWorkClearance.PAYMENT_FOLLOW_UP
        if activity_status == FDAActivityStatus.WAITING_EXTERNAL:
            return FDAWorkClearance.FOLLOW_UP_EXTERNAL
        return FDAWorkClearance.CLEARED