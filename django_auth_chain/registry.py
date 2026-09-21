from collections.abc import Callable, Sequence
from dataclasses import dataclass

from django.contrib.auth.models import User

from .view_pair_presentation import ViewPairPresentation


@dataclass
class AuthMethod:
    code: str
    label: str
    permission: str | None
    is_enrolled: Callable[[User, AuthMethod], bool]
    enroll_and_verify: ViewPairPresentation


_methods: dict[str, AuthMethod] = {}


def register(method: AuthMethod) -> bool:
    exists = _methods.get(method.code, None)
    if exists is not None:
        return False

    _methods[method.code] = method
    return True


def get(code: str) -> AuthMethod | None:
    return _methods.get(code, None)


def codes() -> Sequence[str]:
    return list(_methods)
