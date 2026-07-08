from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.contrib.auth.base_user import BaseUserManager
from django.utils.translation import gettext_lazy as _

# User Roles
class UserRole(models.TextChoices):
    SUPER_ADMIN = "SUPER_ADMIN", "Super Admin"
    SUPERVISOR = "SUPERVISOR", "Supervisor"
    CONSULTANT = "CONSULTANT", "Consultant"
    AMBASSADOR = "AMBASSADOR", "Ambassador"
    USER = "USER", "User"


# User Region
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


# Custom User Creation
class CustomUserManager(BaseUserManager):
    # Create User
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required!")
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    # Create Super User
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", UserRole.SUPER_ADMIN)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)
    

# Custom User Model
class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    
    whatsapp_number = models.CharField(max_length=20, blank=True, null=True, help_text=_("Primary contact number for updates."))
    alternative_number = models.CharField(max_length=20, blank=True, null=True, help_text=_("Secondary contact number for updates."))
    business_name = models.CharField(max_length=255, blank=True, null=True, help_text=_("Registered business name (Applicable to clients/users)."))

    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.USER
    )

    region = models.CharField(
        max_length = 20,
        choices=ClientRegion.choices,
        default=ClientRegion.AHAFO
    )

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"
    
    @property
    def is_super_admin(self):
        return self.role == UserRole.SUPER_ADMIN
    
    @property
    def is_supervisor(self):
        return self.role == UserRole.SUPERVISOR
    
    @property
    def is_consultant(self):
        return self.role == UserRole.CONSULTANT
    
    @property
    def is_ambassador(self):
        return self.role == UserRole.AMBASSADOR
    
    @property
    def is_regular_user(self):
        return self.role == UserRole.USER