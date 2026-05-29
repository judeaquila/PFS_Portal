from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from .models import ClientProject, ProjectActivity, ClientPackage, ActivityStatus, PaymentStatus

def get_activities_for_package(package_type):
    """
    Returns a clean, completely deduplicated list of standardized compliance 
    subactivity names matching the specific chosen service track.
    """
    # 01: Product Registration Core Milestones
    prod_reg_core = [
        "Onboarding Meeting",
        "Product Registration Coaching",
        "Lab Testing",
        "Lab Sample Submission",
        "Product Label Review",
        "Online Portal Setup & Registration"
    ]
    
    # 02: Facility Registration Core Milestones
    fac_reg_core = [
        "Onboarding Meeting",
        "Forms & SOPs Drafting",
        "Facility Setup Guidance",
        "Online Portal Setup & Registration",
        "Training on Documentation"
    ]
    
    # 03: Combined Registration Track (Deduplicated cleanly)
    complete_core = list(dict.fromkeys(prod_reg_core + fac_reg_core))

    # Match framework selection to its corresponding pipeline list
    if package_type in [ClientPackage.PRODUCT_REG, ClientPackage.PROD_RENEW]:
        return prod_reg_core
        
    elif package_type in [ClientPackage.FACILITY_REG, ClientPackage.FAC_RENEW]:
        return fac_reg_core
        
    elif package_type == ClientPackage.COMPLETE:
        return complete_core
        
    elif package_type == ClientPackage.PROD_DEV:
        # 04: Product Development Scratch Steps
        prod_dev_specific = [
            "Onboarding Meeting",
            "Product Formulation",
            "Pilot Production",
            "Production Process Development",
            "Laboratory Testing",
            "Label Design",
            "Packaging"
        ]
        # Merges R&D and complete registration with zero internal task friction
        return list(dict.fromkeys(prod_dev_specific + complete_core))
        
    elif package_type == ClientPackage.QMS_TRAIN:
        return ["Onboarding Meeting", "Forms & SOPs Development", "Training"]
        
    elif package_type == ClientPackage.QUERY_RESP:
        return ["Onboarding Meeting", "Response Letter Drafting", "Guidance on CAPA", "FDA Follow-ups"]
        
    elif package_type == ClientPackage.AD_REG:
        return ["Onboarding Meeting", "Review of Ad", "Application for Registration", "FDA Follow-ups"]
        
    else:
        # Default fallback context boundary (e.g., OTHERS)
        return ["Onboarding Meeting", "Initial Consultation"]


@receiver(post_save, sender=ClientProject)
def populate_default_project_activities(sender, instance, created, **kwargs):
    """
    Signal gatekeeper that handles structural generation of tracking records 
    automatically upon instance initialization.
    """
    if created:
        activity_names = get_activities_for_package(instance.client_package)
        
        # Assemble memory-buffered models without writing individual row executions
        activities_to_create = [
            ProjectActivity(
                project=instance,
                activity_name=name,
                activity_status=ActivityStatus.NOT_STARTED,
                payment_status=PaymentStatus.NOT_PAID
            )
            for name in activity_names
        ]
        
        # Enforcing transaction commitment alignment execution
        if activities_to_create:
            transaction.on_commit(
                lambda: ProjectActivity.objects.bulk_create(activities_to_create)
            )