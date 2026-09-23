from django.apps import AppConfig


class DjangoAuthChainConfig(AppConfig):
    name = "django_auth_chain"

    def ready(self) -> None:
        # not defaulting to password enabled
        pass
