from django.contrib.auth import (
    logout as auth_logout,
)
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils.datastructures import MultiValueDict
from django.views import View

from .constants import DJANGO_AUTH_CHAIN_USER_HOME
from .forms import (
    PassphraseEnrollForm,
    PassphraseVerifyForm,
)
from .router import Router
from .routing_enroll_view import RoutingEnrollView as EnrollView
from .routing_verify_view import RoutingVerifyView as VerifyView


class PassphraseEnrollView(EnrollView):
    def fill_form_from_none(self) -> None:
        self._form = PassphraseEnrollForm(None)
        self._router = Router()

    def fill_form_from_request_data(self, data: MultiValueDict[str, str]) -> None:
        self._form = PassphraseEnrollForm(data)

    def enroll(self) -> bool:
        return False

    def render_with_form(self, request: HttpRequest) -> HttpResponse:
        return render(request, "passphrase_enroll.html", {"form": self._form})

    def is_form_valid(self) -> bool:
        return True if self._form.is_valid() else False

    def add_error(self, field_name: str, error_message: str) -> None:
        self._form.add_error(field_name, error_message)


class PassphraseVerifyView(VerifyView):
    def __init__(self):
        self._router = Router()

    def fill_form_from_none(self) -> None:
        self._form = PassphraseVerifyForm(None)

    def fill_form_from_request_data(self, data: MultiValueDict[str, str]) -> None:
        self._form = PassphraseVerifyForm(data)

    def verify(self) -> bool:
        return False

    def render_with_form(self, request: HttpRequest) -> HttpResponse:
        return render(request, "passphrase_verify.html", {"form": self._form})

    def is_form_valid(self) -> bool:
        return True if self._form.is_valid() else False

    def add_error(self, field_name: str, error_message: str) -> None:
        self._form.add_error(field_name, error_message)


class LogoutView(View):
    def get(self, request: HttpRequest) -> HttpResponse:
        auth_logout(request)
        return redirect(DJANGO_AUTH_CHAIN_USER_HOME)

