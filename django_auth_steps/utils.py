from typing import cast

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.http import HttpRequest

from .constants import (
    PENDING_ENROLLMENT_USER_IDENTIFIER,
    PENDING_VERIFICATION_USER_KEY,
    VERIFIED_METHOD_CODES,
)
from .errors import UserNotFoundError


def clear_pending_user(request: HttpRequest) -> None:
    for key in (
        PENDING_VERIFICATION_USER_KEY,
        PENDING_ENROLLMENT_USER_IDENTIFIER,
        VERIFIED_METHOD_CODES,
    ):
        request.session.pop(key, None)


def get_pending_verification_user(request: HttpRequest) -> AbstractUser:
    pk = request.session.get(PENDING_VERIFICATION_USER_KEY)
    if pk is None:
        raise UserNotFoundError()
    # django-stubs types get_user_model() as type[AbstractBaseUser] (the
    # least common denominator); this package's contract needs the wider
    # AbstractUser surface (has_perm(), USERNAME_FIELD) everywhere a user
    # is looked up, so it's cast here rather than weakening every caller's
    # annotation to AbstractBaseUser.
    user_model = cast(type[AbstractUser], get_user_model())
    user = user_model.objects.filter(pk=pk).first()
    if user is None:
        raise UserNotFoundError()
    return user
