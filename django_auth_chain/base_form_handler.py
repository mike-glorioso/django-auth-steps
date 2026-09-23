from abc import ABC, abstractmethod

from django.forms import Form
from django.http import HttpRequest, HttpResponseBase
from django.shortcuts import render
from django.template.backends.utils import csrf_input
from django.utils.datastructures import MultiValueDict

from .errors import ExecutionStateNotSetError, FormNotSetError


class BaseFormHandler(ABC):
    def __init__(self):
        self._form: Form | None = None
        self._execution_state: bool | None = None

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
        # Computed here in plain Python, not left to the template, so
        # these templates render identically under either Django template
        # backend. Jinja2 auto-injects csrf_input into context; DTL
        # doesn't (it uses the {% csrf_token %} tag instead) - calling
        # this explicitly works under both. non_field_errors() is a real
        # method on Form, not a property: DTL's {{ }} auto-calls no-arg
        # callables, Jinja2's doesn't, so calling it here and passing the
        # plain list avoids needing engine-specific template syntax too.
        context = {
            "form": self._form,
            "non_field_errors": self._form.non_field_errors(),
            "csrf_input": csrf_input(request),
        }
        return render(request, html, context)

    def set_execution_state(self, succeeded: bool) -> None:
        self._execution_state = succeeded

    def execution_state(self) -> bool:
        if self._execution_state is None:
            raise ExecutionStateNotSetError()
        return self._execution_state

    @abstractmethod
    def fill_form_from_none(self) -> None: ...

    @abstractmethod
    def fill_form_from_request_data(self, data: MultiValueDict[str, str]) -> None: ...
