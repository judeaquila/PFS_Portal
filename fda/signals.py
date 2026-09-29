from django.db.models.signals import post_save
from django.dispatch import receiver
from dashboard.models import ClientProject
from .models import FDAProjectTracker, FDAWorkflowStage, FDAProjectStageActivity

@receiver(post_save, sender=ClientProject)
def initialize_fda_tracker(sender, instance, created, **kwargs):
    if created:
        tracker = FDAProjectTracker.objects.create(project=instance)
        stages = FDAWorkflowStage.objects.all()
        activities = [
            FDAProjectStageActivity(tracker=tracker, stage=stage)
            for stage in stages
        ]
        FDAProjectStageActivity.objects.bulk_create(activities)