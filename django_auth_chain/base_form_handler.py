from abc import ABC, abstractmethod

from django.forms import Form
from django.http import HttpRequest, HttpResponseBase
from django.shortcuts import render
from django.utils.datastructures import MultiValueDict

from .errors import FormNotSetError


class BaseFormHandler(ABC):
    def __init__(self):
        self._form: Form | None = None

    def set_form(self, form: Form):
        self._form = form

    def get_form(self) -> Form:
        if self._form is None:
            raise FormNotSetError()
        return self._form

    def is_form_valid(self) -> bool:
        if self._form is None:
            raise FormNotSetError()
        return True if self._form.is_valid() else False

    def add_error(self, field_name: str | None, error_message: str) -> None:
        if self._form is None:
            raise FormNotSetError()
        self._form.add_error(field_name, error_message)

    def render_with_form(self, request: HttpRequest, html: str) -> HttpResponseBase:
        if self._form is None:
            raise FormNotSetError()
        return render(request, html, {"form": self._form})

    @abstractmethod
    def fill_form_from_none(self) -> None: ...

    @abstractmethod
    def fill_form_from_request_data(self, data: MultiValueDict[str, str]) -> None: ...

