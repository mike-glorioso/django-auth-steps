from abc import ABC, abstractmethod

from django.http import HttpRequest, HttpResponseBase
from django.utils.datastructures import MultiValueDict

from .utils import clear_pending_user


class BaseView(ABC):
    def get(self, request: HttpRequest) -> HttpResponseBase:
        clear_pending_user(request)
        self.fill_form_from_none()
        return self.render_with_form(request)

    @abstractmethod
    def is_form_valid(self) -> bool: ...

    @abstractmethod
    def add_error(self, field_name: str, error_message: str) -> None: ...

    @abstractmethod
    def fill_form_from_none(self) -> None: ...

    @abstractmethod
    def fill_form_from_request_data(self, data: MultiValueDict[str, str]) -> None: ...

    @abstractmethod
    def render_with_form(self, request: HttpRequest) -> HttpResponseBase: ...

    @abstractmethod
    def post(self, request: HttpRequest) -> HttpResponseBase: ...

