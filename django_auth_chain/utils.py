from django.http import HttpRequest

from .constants import (
    PENDING_ENROLLMENT_USER_IDENTIFIER,
    PENDING_VERIFICATION_USER_KEY,
    VERIFICATION_METHOD_CODE,
    VERIFIED_METHOD_CODES,
)


def clear_pending_user(request: HttpRequest) -> None:
    for key in (
        PENDING_VERIFICATION_USER_KEY,
        PENDING_ENROLLMENT_USER_IDENTIFIER,
        VERIFICATION_METHOD_CODE,
        VERIFIED_METHOD_CODES,
    ):
        request.session.pop(key, None)
