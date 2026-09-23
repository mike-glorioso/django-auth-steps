from django.apps import AppConfig


class DjangoAuthChainConfig(AppConfig):
    name = "django_auth_chain"

    def ready(self) -> None:
        from .passphrase import PassphraseEnrollStrategy, PassphraseVerifyStrategy
        from .registry import AuthMethod, register

        register(
            AuthMethod(
                code="passphrase",
                label="Passphrase",
                permission=None,
                is_enrolled=lambda user: user.has_usable_password(),
                enroll_strategy=PassphraseEnrollStrategy(),
                verify_strategy=PassphraseVerifyStrategy(),
            )
        )
