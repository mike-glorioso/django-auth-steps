from django.contrib.auth.models import User
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


def get_pending_verification_user(request: HttpRequest) -> User:
    pk = request.session.get(PENDING_VERIFICATION_USER_KEY)
    if pk is None:
        raise UserNotFoundError()
    user = User.objects.filter(pk=pk).first()
    if user is None:
        raise UserNotFoundError()
    return user
