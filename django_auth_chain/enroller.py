from abc import ABC, abstractmethod

from django.http import HttpRequest

from .base_form_handler import BaseFormHandler


class Enroller(ABC):
    @abstractmethod
    def enroll(self, request: HttpRequest, form_handler: BaseFormHandler) -> bool: ...
