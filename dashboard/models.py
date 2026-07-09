from django.db import models
from django.conf import settings


class ConsultantProfile(models.Model):
    class VerificationStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending Review'
        APPROVED = 'APPROVED', 'Approved'
        DECLINED = 'DECLINED', 'Declined'

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='consultant_profile'
    )
    avatar = models.ImageField(
        upload_to='consultants/avatars/', 
        help_text="Needed for visual verification.",
        blank=True
    )
    bio = models.TextField(blank=True)

    cv = models.FileField(upload_to="consultant_docs/%Y/%m/",
         help_text="Upload your CV."
    )
    
    id_card = models.ImageField(
        upload_to='consultants/ids/', 
        help_text="Upload a valid Government Issued National ID Card, Passport, or Driver's License."
    )
    verification_selfie = models.ImageField(
        upload_to='consultants/selfies/', 
        help_text="Live clear selfie photo matching your ID Card profile snapshot."
    )
    
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING
    )
    is_active_consultant = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Consultant: {self.user.get_full_name() or self.user.first_name} ({self.verification_status})"
    

class DocumentType(models.TextChoices):
    BUSINESS_CERT = "BUSINESS_CERT", "Business Registration Certificate"
    HEALTH_CARD = "HEALTH_CARD", "Medical Fitness Certificates (Health Cards)"
    FACILITY_SKETCH = "FACILITY_SKETCH", "Facility Floor Sketch Plan"
    PRODUCT_LABEL = "PRODUCT_LABEL", "Proposed Product Labels"
    WATER_ANALYSIS = "WATER_ANALYSIS", "Water Analysis Report (If Applicable)"
    PEST_CONTROL = "PEST_CONTROL", "Pest Control Contract/Certificate"
    SOP_MANUAL = "SOP_MANUAL", "Standard Operating Procedures (SOPs)"
    SUPPLEMENTARY = "SUPPLEMENTARY_DOC", "Supplementary Documents"


class DocumentStatus(models.TextChoices):
    PENDING = "PENDING", "Pending Review"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected / Needs Resubmission"


class ClientDocument(models.Model):
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name="documents"
    )
    document_type = models.CharField(
        max_length=50, 
        choices=DocumentType.choices
    )
    custom_title = models.CharField(max_length=255, blank=True, null=True)
    file = models.FileField(upload_to="client_docs/%Y/%m/")
    status = models.CharField(
        max_length=20, 
        choices=DocumentStatus.choices, 
        default=DocumentStatus.PENDING
    )
    rejection_reason = models.TextField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='documents_uploaded_by_me',
        help_text="Tracks the explicit actor (Client vs. Ambassador)."
    )

    @property
    def is_uploaded_by_proxy(self):
        """Returns True if someone other than the file owner committed the upload."""
        return self.uploaded_by != self.user

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['client', 'document_type'],
                condition=~models.Q(document_type=DocumentType.SUPPLEMENTARY),
                name='unique_core_document_per_client'
            ),
            models.UniqueConstraint(
                fields=['client', 'document_type', 'custom_title'],
                condition=models.Q(document_type=DocumentType.SUPPLEMENTARY),
                name='unique_supplementary_document_title_per_client'
            )
        ]

    def get_display_name(self):
        if self.document_type == DocumentType.SUPPLEMENTARY and self.custom_title:
            return self.custom_title
        return self.get_document_type_display()

    def __str__(self):
        return f"{self.client.business_name or self.client.email} - {self.get_display_name()}"
    


class LogCategory(models.TextChoices):
    PROFILE = "PROFILE", "Profile Update"
    DOCUMENT = "DOCUMENT", "Document Upload"
    PAYMENT = "PAYMENT", "Payment Transaction"
    SYSTEM = "SYSTEM", "System Notification"


class ActivityLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name="activities"
    )
    category = models.CharField(
        max_length=20, 
        choices=LogCategory.choices, 
        default=LogCategory.SYSTEM
    )
    description = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user.email} | {self.category} | {self.timestamp.strftime('%Y-%m-%d %H:%M')}"
    

class ProjectGroup(models.TextChoices):
    FDA_ACTIVE = "FDA_ACTIVE", "FDA ACTIVE Clients"
    PROD_DEV = "PROD_DEV", "Product Development Clients"
    QMS_SETUP = "QMS_SETUP", "Quality Systems Setup"
    INTERNAL = "INTERNAL", "INTERNAL"


class ClientPackage(models.TextChoices):
    PRODUCT_REG = "PRODUCT_REG", "Product Registration Support"
    FACILITY_REG = "FACILITY_REG", "Facility Registration Support"
    COMPLETE = "COMPLETE", "FDA Complete Registration Support"
    PROD_DEV = "PROD_DEV", "Product Development"
    QMS_TRAIN = "QMS_TRAIN", "QMS Setup and Training"
    QUERY_RESP = "QUERY_RESP", "FDA Query Response Support"
    PROD_RENEW = "PROD_RENEW", "Product Registration Renewal"
    FAC_RENEW = "FAC_RENEW", "Facility Registration Renewal"
    AD_REG = "AD_REG", "Ad Registration Support"
    OTHERS = "OTHERS", "Others"


class ProductCategory(models.TextChoices):
    FOOD = "FOOD", "Food"
    COSMETICS = "COSMETICS", "Cosmetics"
    PHARMA = "PHARMA", "Pharmaceuticals"
    FABRICS = "FABRICS", "Fabrics"
    NON_FOOD = "NON_FOOD", "Non Food"
    SUPPLEMENTS = "SUPPLEMENTS", "Supplements"
    OTHERS = "OTHERS", "Others"


class ClientRegion(models.TextChoices):
    AHAFO = "AHAFO", "Ahafo"
    ASHANTI = "ASHANTI", "Ashanti"
    BONO = "BONO", "Bono"
    BONO_EAST = "BONO_EAST", "Bono East"
    CENTRAL = "CENTRAL", "Central"
    EASTERN = "EASTERN", "Eastern"
    GREATER_ACCRA = "GREATER_ACCRA", "Greater Accra"
    NORTH_EAST = "NORTH_EAST", "North East"
    NORTHERN = "NORTHERN", "Northern"
    OTI = "OTI", "Oti"
    SAVANNAH = "SAVANNAH", "Savannah"
    UPPER_EAST = "UPPER_EAST", "Upper East"
    UPPER_WEST = "UPPER_WEST", "Upper West"
    VOLTA = "VOLTA", "Volta"
    WESTERN = "WESTERN", "Western"
    WESTERN_NORTH = "WESTERN_NORTH", "Western North"
    DIASPORA = "DIASPORA", "Diaspora"


class PaymentStatus(models.TextChoices):
    PAID = "PAID", "Paid"
    PAID_PART = "PAID_PART", "Paid Part"
    AWAITING = "AWAITING", "Awaiting Payment"
    NOT_PAID = "NOT_PAID", "Not Paid"
    TBD = "TBD", "TBD"
    NA = "NA", "N/A"
    PENDING = "PENDING", "Pending"


class ActivityStatus(models.TextChoices):
    PAUSED = "PAUSED", "Paused"
    ONGOING = "ONGOING", "Ongoing"
    COMPLETED = "COMPLETED", "Completed"
    NOT_STARTED = "NOT_STARTED", "Not Started"
    CLIENT_TASK = "CLIENT_TASK", "Client Task"
    PENDING = "PENDING", "Pending"


class ClientProject(models.Model):
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="projects",
        limit_choices_to={'role': 'USER'},
        help_text="The client this project belongs to."
    )
    group = models.CharField(
        max_length=20, choices=ProjectGroup.choices, default=ProjectGroup.FDA_ACTIVE
    )
    client_package = models.CharField(max_length=20, choices=ClientPackage.choices)
    category = models.CharField(max_length=20, choices=ProductCategory.choices)
    region = models.CharField(max_length=20, choices=ClientRegion.choices)
    
    project_start_date = models.DateField()
    product_names = models.TextField(
        blank=True, null=True, help_text="List of products (e.g. Elite Cereal Mix)."
    )
    overall_project_notes = models.TextField(blank=True, null=True)
    
    assigned_consultant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_projects",
        limit_choices_to={'role': 'CONSULTANT'},
        help_text="Consultant handling this client's operational workflow."
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Project File: {self.client.business_name or self.client.email}"

    @property
    def automated_progress(self):
        total = self.activities.count()
        if total == 0:
            return 0
        completed = self.activities.filter(activity_status=ActivityStatus.COMPLETED).count()
        return round((completed / total) * 100)


class ProjectActivity(models.Model):
    project = models.ForeignKey(
        ClientProject, 
        on_delete=models.CASCADE, 
        related_name="activities"
    )
    activity_name = models.CharField(max_length=255)
    payment_status = models.CharField(
        max_length=20, 
        choices=PaymentStatus.choices, 
        default=PaymentStatus.NOT_PAID
    )
    activity_status = models.CharField(
        max_length=20, 
        choices=ActivityStatus.choices, 
        default=ActivityStatus.NOT_STARTED
    )
    activity_notes = models.TextField(blank=True, null=True)
    activity_deadline = models.DateField(blank=True, null=True)
    
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Project Activities"

    def __str__(self):
        return f"{self.project.client.business_name or self.project.client.email} - {self.activity_name}"
    

class ActivityNote(models.Model):
    activity = models.ForeignKey(
        ProjectActivity, 
        on_delete=models.CASCADE, 
        related_name="notes_stream"
    )
    note_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']


class AmbassadorProfile(models.Model):
    class VerificationStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending Review'
        APPROVED = 'APPROVED', 'Approved'
        DECLINED = 'DECLINED', 'Declined'

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='ambassador_profile'
    )
    avatar = models.ImageField(
        upload_to='ambassadors/avatars/', 
        help_text="Critical for in-person visual client verification.",
        blank=True
    )
    bio = models.TextField(blank=True)
    
    id_card = models.ImageField(
        upload_to='ambassadors/ids/', 
        help_text="Upload a valid Government Issued National ID Card, Passport, or Driver's License."
    )
    verification_selfie = models.ImageField(
        upload_to='ambassadors/selfies/', 
        help_text="Live clear selfie photo matching your ID Card profile snapshot."
    )
    
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING
    )
    is_active_field_agent = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Ambassador: {self.user.get_full_name() or self.user.username} ({self.verification_status})"


class AmbassadorAssignment(models.Model):
    ASSISTANCE_MODALITY = [
        ('REMOTE', 'Remote Assistance'),
        ('IN_PERSON', 'In-Person Field Visit'),
    ]
    
    TASK_STATUS = [
        ('ASSIGNED', 'Assigned / In Progress'),
        ('COMPLETED', 'Fully Resolved'),
        ('CANCELLED', 'Cancelled'),
    ]

    ambassador = models.ForeignKey(AmbassadorProfile, on_delete=models.CASCADE, related_name='assignments')
    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='assigned_ambassadors')
    project = models.ForeignKey(ClientProject, on_delete=models.SET_NULL, null=True, blank=True)
    
    modality = models.CharField(max_length=10, choices=ASSISTANCE_MODALITY, default='REMOTE')
    status = models.CharField(max_length=15, choices=TASK_STATUS, default='ASSIGNED')
    
    # Dual Sign-off Closures
    client_marked_complete = models.BooleanField(default=False)
    client_completed_at = models.DateTimeField(null=True, blank=True)
    
    ambassador_marked_complete = models.BooleanField(default=False)
    ambassador_completed_at = models.DateTimeField(null=True, blank=True)
    
    payout_processed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def check_and_finalize_payout(self):
        """Triggers the payout engine if both entities clear the completion gate."""
        if self.client_marked_complete and self.ambassador_marked_complete and not self.payout_processed:
            self.status = 'COMPLETED'
            # Execute logic linking to your accounting ledger/stripe batching here
            self.payout_processed = True
            self.save()