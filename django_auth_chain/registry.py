from collections.abc import Callable, Sequence
from dataclasses import dataclass

from django.contrib.auth.models import User

from .enroll_view import EnrollView
from .verify_view import VerifyView


@dataclass
class AuthMethod:
    code: str
    label: str
    permission: str | None
    is_enrolled: Callable[[User], bool]
    enroll_view: EnrollView
    verify_view: VerifyView
    is_enrolled_for_code: Callable[[str,str,str], bool]
    has_verified_for_code: Callable[[str,str,str], bool]

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

def is_matching_for_code(key: str, code: str, pk: str):
    user = User.objects.filter(
            user__pk==pk
    ).first()

