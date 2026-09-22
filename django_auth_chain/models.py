from __future__ import annotations

from datetime import datetime

from django.contrib.auth.models import Group, User
from django.db.models import (
    CASCADE,
    BooleanField,
    CharField,
    DateTimeField,
    ForeignKey,
    Model,
    PositiveSmallIntegerField,
    UniqueConstraint,
)


class PermissionUser(User):
    class Meta(User.Meta):
        permissions = [("login_with_password", "Can log in using a password")]
        proxy = True


class UserAuthMethod(Model):
    user: ForeignKey[User, User] = ForeignKey(User, on_delete=CASCADE, related_name="auth_methods")
    code: CharField[str, str] = CharField(max_length=32)
    order: PositiveSmallIntegerField[int, int] = PositiveSmallIntegerField()
    enabled: BooleanField[bool, bool] = BooleanField(default=True)
    created_at: DateTimeField[datetime, datetime] = DateTimeField(auto_now_add=True)
    updated_at: DateTimeField[datetime, datetime] = DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            UniqueConstraint(fields=["user", "order"], name="unique_user_step_order"),
        ]

    def __str__(self) -> str:
        return f"{self.user} - {self.code} (step {self.order})"


class GroupDefaultAuthMethod(Model):
    group: ForeignKey[Group, Group] = ForeignKey(
        Group, on_delete=CASCADE, related_name="auth_methods"
    )
    code: CharField[str, str] = CharField(max_length=32)
    order: PositiveSmallIntegerField[int, int] = PositiveSmallIntegerField()
    enabled: BooleanField[bool, bool] = BooleanField(default=True)
    created_at: DateTimeField[datetime, datetime] = DateTimeField(auto_now_add=True)
    updated_at: DateTimeField[datetime, datetime] = DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            UniqueConstraint(fields=["group", "order"], name="unique_group_step_order"),
        ]

    def __str__(self) -> str:
        return f"{self.group} - {self.code} (step {self.order})"
