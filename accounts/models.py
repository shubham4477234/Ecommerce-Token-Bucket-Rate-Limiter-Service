
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from .managers import UserManager

class User(AbstractBaseUser, PermissionsMixin):
    objects = UserManager()
    ROLE_CHOICES = [
        ("customer", "Customer"),
        ("admin", "Admin"),
        ("service", "Service"),
    ]

    TIER_CHOICES = [
        ("free", "Free"),
        ("premium", "Premium"),
    ]

    id = models.BigAutoField(primary_key=True)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15, unique=True)
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="customer"
    )
    tier = models.CharField(
        max_length=10,
        choices=TIER_CHOICES,
        default="free"
    )

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["phone"]

    def __str__(self):
        return self.email
