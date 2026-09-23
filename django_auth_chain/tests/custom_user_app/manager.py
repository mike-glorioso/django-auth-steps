from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib.auth.base_user import BaseUserManager

if TYPE_CHECKING:
    from .models import EmailUser


class EmailUserManager(BaseUserManager["EmailUser"]):
    def create_user(self, email: str, password: str | None = None) -> EmailUser:
        user = self.model(email=self.normalize_email(email))
        user.set_password(password)
        user.save(using=self._db)
        return user
