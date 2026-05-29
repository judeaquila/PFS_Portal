from django.test import TestCase
from django.contrib.auth import get_user_model
from dashboard.models import ClientProject, ProjectActivity, ClientPackage, ActivityStatus
import datetime

User = get_user_model()

class ClientProjectSignalTest(TestCase):
    def setUp(self):
        # 1. Create a Consultant to assign to the project
        self.consultant = User.objects.create_user(
            email="consultant@pfsgh.com",
            password="securepassword123",
            role="CONSULTANT"
        )
        # 2. Create a Client user
        self.client_user = User.objects.create_user(
            email="testclient@business.com",
            password="clientpassword123",
            business_name="Test Food Corp",
            role="USER"
        )

    def test_project_creates_activities_automatically(self):
        """
        Verifies that saving a ClientProject triggers the signal 
        to populate the expected default subitems.
        """
        # Create a project with the QMS Setup and Training package
        project = ClientProject.objects.create(
            client=self.client_user,
            client_package=ClientPackage.QMS_TRAIN,
            category="FOOD",
            region="GREATER_ACCRA",
            project_start_date=datetime.date.today(),
            assigned_consultant=self.consultant
        )

        # Fetch subitems generated for this specific project
        activities = ProjectActivity.objects.filter(project=project)
        activity_names = list(activities.values_list('activity_name', flat=True))

        # Assertions
        expected_names = ["Onboarding Meeting", "Forms & SOPs Development", "Training"]
        self.assertEqual(activities.count(), 3)
        self.assertEqual(activity_names, expected_names)
        
        # Verify initial progress properties compute to 0%
        self.assertEqual(project.automated_progress, 0)