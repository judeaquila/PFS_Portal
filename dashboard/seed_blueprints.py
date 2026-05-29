from django.core.management.base import BaseCommand
from django.db import transaction
from your_app.models import ClientPackage, BlueprintSubactivity

class Command(BaseCommand):
    help = "Populates the database with the core 10-tier service packages and subactivities."

    def handle(self, *args, **options):
        # Master raw blueprint definition data
        blueprints_data = {
            "PRODUCT_REG": {
                "name": "Product Registration Support",
                "desc": "Clients registering products only with the FDA.",
                "tasks": ["Coaching", "Online Portal Setup & Registration", "Label Review", "Sample Submission"]
            },
            "FACILITY_REG": {
                "name": "Facility Registration Support",
                "desc": "Clients registering their facility only with the FDA.",
                "tasks": ["Forms & SOPs Drafting", "Facility Setup Guidance", "Online Portal Setup & Registration", "Training on Documentation"]
            },
            "COMPLETE": {
                "name": "FDA Complete Registration Support",
                "desc": "Complete support package covering both facility and products.",
                "tasks": ["Coaching", "Online Portal Setup & Registration", "Label Review", "Sample Submission", "Forms & SOPs Drafting", "Facility Setup Guidance", "Training on Documentation"]
            },
            "PRODUCT_DEV": {
                "name": "Product Development",
                "desc": "Full cycle product development through to FDA registration.",
                "tasks": ["Product Formulation", "Pilot Production", "Production Process Development", "Laboratory Testing", "Label Design", "Packaging", "Coaching", "Online Portal Setup & Registration", "Label Review", "Sample Submission", "Forms & SOPs Drafting", "Facility Setup Guidance", "Training on Documentation"]
            },
            "QMS_TRAIN": {
                "name": "QMS Setup and Training",
                "desc": "Quality Management System setup for production operations.",
                "tasks": ["Forms & SOPs Development", "Training"]
            },
            "FDA_QUERY": {
                "name": "FDA Query Response Support",
                "desc": "Technical assistance addressing concerns raised by the FDA.",
                "tasks": ["Response Letter Drafting", "Guidance on CAPA", "FDA Follow-ups"]
            },
            "PROD_RENEW": {
                "name": "Product Registration Renewal",
                "desc": "Support for renewing expired product certificates.",
                "tasks": ["Coaching", "Online Portal Setup & Registration", "Label Review", "Sample Submission"]
            },
            "FAC_RENEW": {
                "name": "Facility Registration Renewal",
                "desc": "Support for renewing expired facility certificates.",
                "tasks": ["Forms & SOPs Drafting", "Facility Setup Guidance", "Online Portal Setup & Registration", "Training on Documentation"]
            },
            "AD_REG": {
                "name": "Ad Registration Support",
                "desc": "Registration of product advertisements with the FDA.",
                "tasks": ["Review of Ad", "Application for Registration", "FDA Follow-ups"]
            },
            "OTHERS": {
                "name": "Others",
                "desc": "Unique concerns outside standard categories.",
                "tasks": []
            }
        }

        with transaction.atomic():
            self.stdout.write("Purging old blueprint configurations...")
            ClientPackage.objects.all().delete()

            for order, (code, info) in enumerate(blueprints_data.items(), start=1):
                # 1. Save the master package row
                pkg = ClientPackage.objects.create(
                    code=code,
                    name=info["name"],
                    description=info["desc"],
                    display_order=order
                )
                
                # 2. Save the child subactivity rows pointing to that package
                for sort_idx, task_name in enumerate(info["tasks"], start=1):
                    BlueprintSubactivity.objects.create(
                        package=pkg,
                        activity_name=task_name,
                        sort_order=sort_idx
                    )
                
                self.stdout.write(self.style.SUCCESS(f"Successfully seeded package track: {code}"))