from django.core.management.base import BaseCommand
from django.db import transaction
from bookings.models import NewClientPackage, BlueprintSubactivity, AddOnService


class Command(BaseCommand):
    help = "Populates the database with the PFS Package Comparison Matrix tiers, subactivities, and add-ons."

    def handle(self, *args, **options):
        # 14 Standard Matrix Subactivities with exact scope labels
        matrix_activities = {
            "rev_docs": ("Review of product documentation", "1 Product"),
            "rev_label": ("Review of product label", "1 Label"),
            "fda_portal": ("FDA online portal account creation", "1 Account"),
            "fda_prod_reg": ("FDA online product registration", "1 Product"),
            "fda_fac_reg": ("FDA online facility registration", "1 Facility"),
            "fda_sample_sub": ("Sample submission to the FDA", "1 Product"),
            "app_followups": ("Application follow ups", "1 Product"),
            "audit_followups": ("Audit scheduling follow ups", "1 Facility"),
            "lab_prep": ("Lab sample preparation training", "1 Product"),
            "lab_sub": ("Sample submission to a laboratory", "1 Product"),
            "lab_followups": ("Laboratory test results follow up", "1 Product"),
            "facility_setup": ("Facility setup and audit training", "1 Facility"),
            "draft_forms": ("Drafting of forms", "10 Forms"),
            "draft_sops": ("Drafting of SOPs", "10 SOPs"),
        }

        # Shared Activity Groupings according to document columns
        basic_core = [
            matrix_activities["rev_docs"],
            matrix_activities["rev_label"],
            matrix_activities["fda_portal"],
            matrix_activities["fda_prod_reg"],
        ]

        basic_plus_cosmetics = basic_core + [
            matrix_activities["fda_sample_sub"],
            matrix_activities["app_followups"],
        ]

        basic_plus_food = basic_plus_cosmetics + [
            matrix_activities["lab_prep"],
            matrix_activities["lab_sub"],
            matrix_activities["lab_followups"],
        ]

        standard_core = basic_core + [
            matrix_activities["fda_fac_reg"],
        ]

        standard_plus_food = standard_core + [
            matrix_activities["fda_sample_sub"],
            matrix_activities["app_followups"],
            matrix_activities["audit_followups"],
        ]

        standard_plus_cosmetics = standard_plus_food + [
            matrix_activities["facility_setup"],
            matrix_activities["draft_forms"],
            matrix_activities["draft_sops"],
        ]

        advanced_core = standard_core + [
            matrix_activities["lab_prep"],
        ]

        advanced_plus_food = advanced_core + [
            matrix_activities["fda_sample_sub"],
            matrix_activities["app_followups"],
            matrix_activities["audit_followups"],
            matrix_activities["lab_sub"],
            matrix_activities["lab_followups"],
        ]

        advanced_plus_cosmetics = advanced_plus_food + [
            matrix_activities["facility_setup"],
            matrix_activities["draft_forms"],
            matrix_activities["draft_sops"],
        ]

        # Packages matching matrix structure
        blueprints_data = {
            "BASIC_ALL": {
                "name": "Basic - All (Renewals)",
                "price": 1080.00,
                "desc": "Product registration renewals across all categories (no facility setup support).",
                "tasks": basic_core,
            },
            "BASIC_PLUS_COSMETICS": {
                "name": "Basic Plus - Cosmetics (Renewals)",
                "price": 1440.00,
                "desc": "Cosmetic renewals including FDA sample submission and application follow-ups.",
                "tasks": basic_plus_cosmetics,
            },
            "BASIC_PLUS_FOOD": {
                "name": "Basic Plus - Food (Renewals)",
                "price": 1800.00,
                "desc": "Food renewals including laboratory support, sample submission, and follow-ups.",
                "tasks": basic_plus_food,
            },
            "STANDARD_ALL": {
                "name": "Standard - All (Product Registration)",
                "price": 1320.00,
                "desc": "New product registrations including online facility registration (no setup support).",
                "tasks": standard_core,
            },
            "STANDARD_PLUS_FOOD": {
                "name": "Standard Plus - Food (Product Registration)",
                "price": 2040.00,
                "desc": "Standard food registration with sample submissions, application, and audit follow-ups.",
                "tasks": standard_plus_food,
            },
            "STANDARD_PLUS_COSMETICS": {
                "name": "Standard Plus - Cosmetics (Product Registration)",
                "price": 1680.00,
                "desc": "Standard cosmetics registration with facility setup/audit training, forms, and SOP drafting.",
                "tasks": standard_plus_cosmetics,
            },
            "ADVANCED_ALL": {
                "name": "Advanced - All (Full Setup & Registration)",
                "price": 3480.00,
                "desc": "New registration with facility setup support and lab sample prep training.",
                "tasks": advanced_core,
            },
            "ADVANCED_PLUS_FOOD": {
                "name": "Advanced Plus - Food (Full Setup & Registration)",
                "price": 4200.00,
                "desc": "Comprehensive food setup covering submissions, lab testing, and follow-ups.",
                "tasks": advanced_plus_food,
            },
            "ADVANCED_PLUS_COSMETICS": {
                "name": "Advanced Plus - Cosmetics (Full Setup & Registration)",
                "price": 3840.00,
                "desc": "Full-spectrum package covering facility training, SOPs, forms, lab support, and submission.",
                "tasks": advanced_plus_cosmetics,
            },
            "OTHERS": {
                "name": "Others / Custom Add-on",
                "price": 0.00,
                "desc": "Custom service scopes and tailored compliance tracks.",
                "tasks": [],
            },
        }

        # Add-On Items Pricing Matrix
        add_ons = [
            ("One to One Meeting", 300.00, "General client one to one meeting requests."),
            ("SOP Drafting", 100.00, "Drafting of one SOP for a client."),
            ("Form Drafting", 150.00, "Drafting of one form or activity tracking template for a client."),
            ("GMP Training (Per Head)", 500.00, "Training for client staff on basic to intermediate GMP principles."),
            ("Facility Notices Drafting", 100.00, "Designing of one facility food safety or quality notice."),
            ("Product Label Review", 100.00, "Review of a client label, charged per review round."),
            ("FDA Follow Ups / Enquiries", 200.00, "Any additional follow up request, enquiry or errand to FDA requested by the client."),
            ("Lab Sample Preparation Training", 300.00, "Training on laboratory sample preparation with cost guidance."),
            ("FDA Online Product Registration", 300.00, "Completion of online registration for one product."),
            ("FDA Online Facility Registration", 300.00, "Completion of online registration for one facility."),
        ]

        with transaction.atomic():
            self.stdout.write("Purging old blueprint configurations & add-ons...")
            NewClientPackage.objects.all().delete()
            AddOnService.objects.all().delete()

            for order, (code, info) in enumerate(blueprints_data.items(), start=1):
                pkg = NewClientPackage.objects.create(
                    code=code,
                    name=info["name"],
                    price_ghs=info["price"],
                    description=info["desc"],
                    display_order=order,
                )

                for sort_idx, (task_name, scope) in enumerate(info["tasks"], start=1):
                    BlueprintSubactivity.objects.create(
                        package=pkg,
                        activity_name=task_name,
                        scope=scope,
                        sort_order=sort_idx,
                    )

                self.stdout.write(self.style.SUCCESS(f"Seeded Package Track: {code} (GHS {info['price']:,.2f})"))

            for name, price, desc in add_ons:
                AddOnService.objects.create(name=name, price_ghs=price, description=desc)
                
            self.stdout.write(self.style.SUCCESS("Successfully seeded Add-On Pricing matrix."))