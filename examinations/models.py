from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


class QuestionCategory(models.TextChoices):
    COMPANY_KNOWLEDGE = 'COMPANY_KNOWLEDGE', 'PFS Company Knowledge'
    SERVICES = 'SERVICES', 'PFS Services'
    CLIENT_MANAGEMENT = 'CLIENT_MANAGEMENT', 'Client Management'
    COMMUNICATION = 'COMMUNICATION', 'Communication'
    PROFESSIONALISM = 'PROFESSIONALISM', 'Professionalism'
    PRODUCT_DEVELOPMENT = 'PRODUCT_DEVELOPMENT', 'Product Development'
    FDA = 'FDA', 'FDA'
    GMP = 'GMP', 'GMP'
    SALES = 'SALES', 'Sales'
    CULTURE = 'CULTURE', 'PFS Culture'

class Question(models.Model):
    OPTION_CHOICES = [
        ('A', 'Option A'),
        ('B', 'Option B'),
        ('C', 'Option C'),
        ('D', 'Option D'),
    ]

    category = models.CharField(max_length=50, choices=QuestionCategory.choices)
    text = models.TextField()
    option_a = models.CharField(max_length=255)
    option_b = models.CharField(max_length=255)
    option_c = models.CharField(max_length=255)
    option_d = models.CharField(max_length=255)
    correct_answer = models.CharField(max_length=1, choices=OPTION_CHOICES)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name='created_questions', null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.get_category_display()}] {self.text[:40]}..."



class ExamAttempt(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='exam_attempts')
    total_questions = models.IntegerField(default=0)
    correct_answers = models.IntegerField(default=0)
    score_percentage = models.FloatField(default=0.0)
    passed = models.BooleanField(default=False)
    attempt_date = models.DateTimeField(auto_now_add=True)
    next_attempt_allowed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-attempt_date']

    def save(self, *args, **kwargs):
        # Calculate percentage score
        if self.total_questions > 0:
            self.score_percentage = round((self.correct_answers / self.total_questions) * 100, 2)
            self.passed = self.score_percentage >= 80.0
        
        # Set 5-day lock period if the candidate failed
        if not self.passed and not self.next_attempt_allowed_at:
            # Setting lock from current attempt timestamp
            base_time = self.attempt_date or timezone.now()
            self.next_attempt_allowed_at = base_time + timedelta(minutes=5)
            
        super().save(*args, **kwargs)

    @property
    def is_locked(self):
        """Returns True if user is still inside the 5-day waiting period."""
        if self.passed:
            return True  # Exam completed, no retakes needed
        if self.next_attempt_allowed_at and timezone.now() < self.next_attempt_allowed_at:
            return True
        return False

    def __str__(self):
        return f"{self.user} - Score: {self.score_percentage}% ({'Passed' if self.passed else 'Failed'})"