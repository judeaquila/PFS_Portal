import secrets
from decimal import Decimal, ROUND_HALF_UP
from django.conf import settings
from django.db import models


class PackageType(models.TextChoices):
    STANDARD = 'STANDARD', 'Standard Onboarding'
    PROD_DEV = 'PROD_DEV', 'Product Development'
    BUDGET_TECH = 'BUDGET_TECH', 'Budgeting & Technical'
    FULL_COSTING = 'FULL_COSTING', 'Full Project Costing'
    BUSINESS_PLAN = 'BUSINESS_PLAN', 'Business Plan & Proposal'
    CUSTOM = 'CUSTOM', 'Custom / Ad-Hoc Charge'


class AssessmentPackage(models.Model):
    """Stores bookings or orders for specific package types."""
    
    package_type = models.CharField(
        max_length=50, 
        choices=PackageType.choices,
        default=PackageType.STANDARD
    )
    custom_title = models.CharField(
        max_length=255, 
        null=True, 
        blank=True, 
        help_text="Custom charge name (e.g., 'Top Up for Product Development')"
    )
    custom_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True, 
        help_text="Custom price for ad-hoc billing"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def price(self):
        # Override with custom_price if present or if package is CUSTOM
        if self.custom_price is not None:
            return self.custom_price
        prices = {
            PackageType.STANDARD: Decimal("200.00"),
            PackageType.PROD_DEV: Decimal("300.00"),
            PackageType.BUDGET_TECH: Decimal("500.00"),
            PackageType.FULL_COSTING: Decimal("1000.00"),
            PackageType.BUSINESS_PLAN: Decimal("3000.00"),
        }
        return prices.get(self.package_type, Decimal("0.00"))

    @property
    def title(self):
        """Returns the custom title if provided, otherwise the standard choice label."""
        if self.custom_title:
            return self.custom_title
        return self.get_package_type_display()

    def __str__(self):
        return f"Package #{self.id} - {self.get_package_type_display()}"


class Payment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="payments")
    package = models.ForeignKey(AssessmentPackage, on_delete=models.SET_NULL, null=True, blank=True)
    business_name = models.CharField(max_length=255, help_text="Name on Business Certificate")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    ref = models.CharField(max_length=200, unique=True)
    email = models.EmailField()
    verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def save(self, *args, **kwargs):
        if not self.ref:
            self.ref = secrets.token_urlsafe(20)
        super().save(*args, **kwargs)

    def amount_value(self):
        """Converts GHS decimal to Paystack pesewas integer."""
        pesewas = (self.amount * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        return int(pesewas)

    @property
    def status_label(self):
        """Returns string label representation of verification state."""
        return "Successful" if self.verified else "Pending"

    @property
    def status_color(self):
        """Returns Tailwind color key based on status."""
        return "emerald" if self.verified else "amber"

    def __str__(self):
        email = getattr(self.user, 'email', 'No User')
        return f"Payment #{self.ref} - {email} ({self.package})"



class PaymentRequest(models.Model):
    class StatusType(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        PAID = 'PAID', 'Paid'
        CANCELLED = 'CANCELLED', 'Cancelled'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='payment_requests'
    )
    service_name = models.CharField(max_length=255, help_text="e.g. Top Up Fee")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    note = models.TextField(blank=True, null=True, help_text="Explanation or breakdown for the client")
    
    reference = models.CharField(max_length=100, unique=True, blank=True)
    status = models.CharField(max_length=20, choices=StatusType.choices, default=StatusType.PENDING)
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='created_payment_requests'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    @property
    def is_paid(self):
        return self.status == self.StatusType.PAID

    @property
    def is_pending(self):
        return self.status == self.StatusType.PENDING

    @property
    def is_cancelled(self):
        return self.status == self.StatusType.CANCELLED

    def save(self, *args, **kwargs):
        if not self.reference:
            # Generate a unique Paystack reference e.g., PR-7F2A9B1C
            self.reference = f"PR-{secrets.token_hex(4).upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.service_name} - {self.user.email} (GHS {self.amount})"