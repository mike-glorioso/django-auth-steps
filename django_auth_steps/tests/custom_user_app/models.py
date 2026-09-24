from typing import ClassVar

from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.db.models import EmailField

from .manager import EmailUserManager


class EmailUser(AbstractBaseUser, PermissionsMixin):
    """Deliberately has no username field at all - proves the package
    doesn't assume django.contrib.auth.models.User's shape, only the
    swappable-user contract (AbstractBaseUser + PermissionsMixin)."""

    email: EmailField[str, str] = EmailField(unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: ClassVar[list[str]] = []

    objects: EmailUserManager = EmailUserManager()

    class Meta(AbstractBaseUser.Meta, PermissionsMixin.Meta):
        pass

    def __str__(self) -> str:
        return self.email
