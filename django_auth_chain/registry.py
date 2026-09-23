from collections.abc import Callable, Sequence
from dataclasses import dataclass

from django.contrib.auth.models import User
from django.http import HttpRequest

from .base_form_handler import BaseFormHandler


@dataclass
class AuthMethod:
    code: str
    label: str
    permission: str | None
    is_enrolled: Callable[[User], bool]
    get_enroll_form_handler: Callable[[], BaseFormHandler]
    get_verify_form_handler: Callable[[], BaseFormHandler]
    enroll: Callable[[HttpRequest, BaseFormHandler], bool]
    verify: Callable[[HttpRequest, BaseFormHandler], bool]
    enroll_html: str
    verify_html: str


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
