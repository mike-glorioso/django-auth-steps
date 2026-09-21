from django.http import HttpRequest

from .constants import (
    NEXT_VERIFICATION_METHOD_CODE,
    PENDING_ENROLLMENT_USER_IDENTIFIER,
    PENDING_VERIFICATION_USER_KEY,
    VERIFIED_METHOD_CODES,
)
from .view_pair_presentation import (
    ViewPairPresentation,
)
from .views import (
    PassphraseEnrollView,
    PassphraseVerifyView,
)


def clear_pending_user(request: HttpRequest) -> None:
    for key in (
        PENDING_VERIFICATION_USER_KEY,
        PENDING_ENROLLMENT_USER_IDENTIFIER,
        NEXT_VERIFICATION_METHOD_CODE,
        VERIFIED_METHOD_CODES,
    ):
        request.session.pop(key, None)


passphrase_view_pair = ViewPairPresentation(
    enroll_view=PassphraseEnrollView,
    verify_view=PassphraseVerifyView,
)
