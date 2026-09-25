from django.http import HttpRequest

from .base_form_handler import BaseFormHandler
from .form_handlers import (
    PassphraseEnrollFormHandler,
    PassphraseVerifyFormHandler,
)
from .registry import (
    AuthMethod,
    register_strategy,
)
from .strategies.enroll_strategy import EnrollStrategy
from .strategies.verify_strategy import VerifyStrategy
from .utils import (
    get_pending_verification_user,
)


class PassphraseEnrollStrategy(EnrollStrategy):
    @property
    def html(self) -> str:
        return "passphrase_enroll.html"

    def get_form_handler(self) -> BaseFormHandler:
        return PassphraseEnrollFormHandler()

    def execute(self, request: HttpRequest, form_handler: BaseFormHandler) -> None:
        form = form_handler.get_form()
        passphrase = form.cleaned_data["passphrase_entry"]
        user = get_pending_verification_user(request)
        user.set_password(passphrase)
        user.save(update_fields=["password"])
        form_handler.set_execution_state(True)


class PassphraseVerifyStrategy(VerifyStrategy):
    @property
    def html(self) -> str:
        return "passphrase_verify.html"

    def get_form_handler(self) -> BaseFormHandler:
        return PassphraseVerifyFormHandler()

    def execute(self, request: HttpRequest, form_handler: BaseFormHandler) -> None:
        form = form_handler.get_form()
        passphrase = form.cleaned_data["passphrase_verify"]
        user = get_pending_verification_user(request)
        if not user.check_password(passphrase):
            form_handler.add_error("passphrase_verify", "Incorrect passphrase.")
            form_handler.set_execution_state(False)
            return
        form_handler.set_execution_state(True)


def register_without_permission():
    register_strategy(
        AuthMethod(
            code="passphrase",
            label="Passphrase",
            permission=None,
            is_enrolled=lambda user: user.has_usable_password(),
            enroll_strategy=PassphraseEnrollStrategy(),
            verify_strategy=PassphraseVerifyStrategy(),
        )
    )


def register_with_permission():
    register_strategy(
        AuthMethod(
            code="passphrase",
            label="Passphrase",
            permission="django_auth_steps.login_with_password",
            is_enrolled=lambda user: user.has_usable_password(),
            enroll_strategy=PassphraseEnrollStrategy(),
            verify_strategy=PassphraseVerifyStrategy(),
        )
    )
