from django.contrib.auth import (
    logout as auth_logout,
)
from django.http import HttpRequest, HttpResponse, HttpResponseBase
from django.shortcuts import redirect, render
from django.utils.datastructures import MultiValueDict
from django.views import View

from .constants import DJANGO_AUTH_CHAIN
from .enroll_view import EnrollView
from .forms import (
    PassphraseEnrollForm,
    PassphraseVerifyForm,
)
from .router import Router
from .verify_view import VerifyView
from .view_pair_presentation import (
    ViewPairPresentation,
)


class StubEnrollView(EnrollView):
    def fill_form_from_none(self) -> None: ...

    def fill_form_from_request_data(self, data: MultiValueDict[str, str]) -> None: ...

    def enroll(self) -> bool:
        return False

    def render_with_form(self, request: HttpRequest) -> HttpResponse:
        raise NotImplementedError()

    def is_form_valid(self) -> bool:
        return False

    def add_error(self, field_name: str, error_message:str) -> None: ...

    def post(self, request: HttpRequest) -> HttpResponseBase:
        raise NotImplementedError()


class StubVerifyView(VerifyView):
    def fill_form_from_none(self) -> None: ...

    def fill_form_from_request_data(self, data: MultiValueDict[str, str]) -> None: ...

    def verify(self) -> bool:
        return False

    def render_with_form(self, request: HttpRequest) -> HttpResponse:
        raise NotImplementedError()

    def is_form_valid(self) -> bool:
        return False

    def add_error(self, field_name: str, error_message:str) -> None: ...

    def post(self, request: HttpRequest) -> HttpResponseBase:
        raise NotImplementedError()


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

    def add_error(self, field_name: str, error_message:str) -> None:
        self._form.add_error(field_name, error_message)

    def post(self, request: HttpRequest) -> HttpResponseBase:
        return self._router.route_try_next_method(request, self)


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

    def add_error(self, field_name: str, error_message:str) -> None:
        self._form.add_error(field_name, error_message)

    def post(self, request: HttpRequest) -> HttpResponseBase:
        return self._router.route_try_next_method(request, self)


class LogoutView(View):
    def get(self, request: HttpRequest) -> HttpResponse:
        auth_logout(request)
        return redirect(f'{DJANGO_AUTH_CHAIN}:logout')

passphrase_view_pair = ViewPairPresentation(
    enroll_view=PassphraseEnrollView(),
    verify_view=PassphraseVerifyView(),
)
