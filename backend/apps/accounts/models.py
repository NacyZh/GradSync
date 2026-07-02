from django.contrib.auth.models import AbstractUser
from django.db import models

from .managers import UserManager


class User(AbstractUser):
    class GlobalRole(models.TextChoices):
        ADVISOR = "advisor", "Advisor"
        STUDENT = "student", "Student"
        ADMIN = "admin", "Administrator"

    class Status(models.TextChoices):
        INVITED = "invited", "Invited"
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"
        ARCHIVED = "archived", "Archived"

    username = None
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255)
    global_role = models.CharField(
        max_length=20, choices=GlobalRole.choices, default=GlobalRole.STUDENT
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    locale = models.CharField(max_length=5, default="en")

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    objects = UserManager()

    def __str__(self) -> str:
        return self.email

    @property
    def is_advisor(self) -> bool:
        return self.global_role in {self.GlobalRole.ADVISOR, self.GlobalRole.ADMIN}

    @property
    def is_administrator(self) -> bool:
        return self.global_role == self.GlobalRole.ADMIN
