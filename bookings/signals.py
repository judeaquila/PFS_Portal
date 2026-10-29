from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from .models import NewClientProject, NewProjectActivity


@receiver(post_save, sender=NewClientProject)
def populate_default_project_activities(sender, instance, created, **kwargs):
    if created and instance.client_package:
        blueprints = instance.client_package.blueprint_subactivities.all().order_by('sort_order')

        activities_to_create = [
            NewProjectActivity(
                project=instance,
                activity_name=blueprint.activity_name,
                scope=blueprint.scope,
                activity_status=NewProjectActivity.ActivityStatus.NOT_STARTED,
                payment_status=NewProjectActivity.PaymentStatus.INCLUDED
            )
            for blueprint in blueprints
        ]

        if activities_to_create:
            transaction.on_commit(
                lambda: NewProjectActivity.objects.bulk_create(activities_to_create)
            )