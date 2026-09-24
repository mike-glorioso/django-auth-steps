from collections.abc import Callable, Sequence
from dataclasses import dataclass

from django.contrib.auth.models import AbstractUser

from .strategies.enroll_strategy import EnrollStrategy
from .strategies.verify_strategy import VerifyStrategy


@dataclass
class AuthMethod:
    code: str
    label: str
    permission: str | None
    is_enrolled: Callable[[AbstractUser], bool]
    enroll_strategy: EnrollStrategy
    verify_strategy: VerifyStrategy


_methods: dict[str, AuthMethod] = {}


def register_strategy(method: AuthMethod) -> bool:
    exists = _methods.get(method.code, None)
    if exists is not None:
        return False

    _methods[method.code] = method
    return True


def get_strategy(code: str) -> AuthMethod | None:
    return _methods.get(code, None)


def strategy_codes() -> Sequence[str]:
    return list(_methods)
