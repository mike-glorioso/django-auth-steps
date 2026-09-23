from django.apps import AppConfig


class DjangoAuthChainConfig(AppConfig):
    name = "django_auth_chain"

    def ready(self) -> None:
        from .passphrase_strategy import (
            register_with_permission as register,
        )

        register()
