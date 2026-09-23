from abc import ABC, abstractmethod

from django.http import HttpRequest

from .base_form_handler import BaseFormHandler


class Verifier(ABC):
    @abstractmethod
    def verify(self, request: HttpRequest, form_handler: BaseFormHandler) -> bool: ...
