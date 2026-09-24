from __future__ import annotations

from datetime import datetime

from django.conf import settings
from django.contrib.auth.models import AbstractUser, Group
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

from .throttling import ThrottlingMixin


class UserAuthMethod(ThrottlingMixin, Model):
    # settings.AUTH_USER_MODEL (a string), not a hardcoded concrete User
    # class, so the FK stays swappable-safe; AbstractUser is used only as
    # the type hint's bound (this package's features - has_perm() for
    # permission-gated methods, check_password()/has_usable_password() for
    # the passphrase method - require that combined contract, even though
    # the real configured model need not literally subclass AbstractUser).
    user: ForeignKey[AbstractUser, AbstractUser] = ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=CASCADE, related_name="auth_methods"
    )
    code: CharField[str, str] = CharField(max_length=32)
    order: PositiveSmallIntegerField[int, int] = PositiveSmallIntegerField()
    enabled: BooleanField[bool, bool] = BooleanField(default=True)
    created_at: DateTimeField[datetime, datetime] = DateTimeField(auto_now_add=True)
    updated_at: DateTimeField[datetime, datetime] = DateTimeField(auto_now=True)

    class Meta(ThrottlingMixin.Meta):
        # Lives here, not on a proxy of the user model: a proxy model's
        # base gets baked into its migration as a concrete class at
        # generation time (unlike FK targets, Django doesn't rewrite a
        # proxy base through swappable_dependency), so a "PermissionUser(
        # get_user_model())" proxy breaks the instant AUTH_USER_MODEL is
        # swapped to anything else - confirmed by actually swapping it in
        # a test and hitting "cannot proxy the swapped model" at migrate
        # time. A permission just needs to live on some real model; it
        # doesn't need to be the user model.
        permissions = [("login_with_password", "Can log in using a password")]
        constraints = [
            UniqueConstraint(fields=["user", "order"], name="unique_user_step_order"),
            UniqueConstraint(fields=["user", "code"], name="unique_user_method"),
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
