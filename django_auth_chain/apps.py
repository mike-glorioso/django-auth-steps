from django.apps import AppConfig


class DjangoAuthChainConfig(AppConfig):
    name = "django_auth_chain"

    def ready(self) -> None:
        from .form_handlers import PassphraseEnrollFormHandler, PassphraseVerifyFormHandler
        from .passphrase import PassphraseEnroller, PassphraseVerifier
        from .registry import AuthMethod, register

        enroller = PassphraseEnroller()
        verifier = PassphraseVerifier()

        register(
            AuthMethod(
                code="passphrase",
                label="Passphrase",
                permission=None,
                is_enrolled=lambda user: user.has_usable_password(),
                get_enroll_form_handler=PassphraseEnrollFormHandler,
                get_verify_form_handler=PassphraseVerifyFormHandler,
                enroll=enroller.enroll,
                verify=verifier.verify,
                enroll_html="passphrase_enroll.html",
                verify_html="passphrase_verify.html",
            )
        )
