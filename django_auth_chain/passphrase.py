from django.http import HttpRequest

from .base_form_handler import BaseFormHandler
from .enroller import Enroller
from .utils import get_pending_verification_user
from .verifier import Verifier


class PassphraseEnroller(Enroller):
    def enroll(self, request: HttpRequest, form_handler: BaseFormHandler) -> bool:
        raise NotImplementedError("Self-service passphrase enrollment isn't built yet.")


class PassphraseVerifier(Verifier):
    def verify(self, request: HttpRequest, form_handler: BaseFormHandler) -> bool:
        form = form_handler.get_form()
        passphrase = form.cleaned_data["passphrase_verify"]
        user = get_pending_verification_user(request)
        if not user.check_password(passphrase):
            form_handler.add_error("passphrase_verify", "Incorrect passphrase.")
            return False
        return True
