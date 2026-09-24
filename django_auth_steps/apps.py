from django.apps import AppConfig


class DjangoAuthStepsConfig(AppConfig):
    name = "django_auth_steps"

    def ready(self) -> None:
        from .passphrase_strategy import (
            register_with_permission as register,
        )

        register()
