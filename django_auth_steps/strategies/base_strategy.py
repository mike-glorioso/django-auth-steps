from abc import ABC, abstractmethod

from django.http import HttpRequest

from ..base_form_handler import BaseFormHandler


class BaseStrategy(ABC):
    """Everything a router needs for one side (enroll or verify) of one
    AuthMethod: which form to show, how to build it, and how to attempt
    it. execute() should call form_handler.set_execution_state(...) with
    the outcome rather than returning it directly - form_handler is the
    thing that's safely scoped per-request; strategy instances are
    shared singletons registered once at app startup."""

    @property
    @abstractmethod
    def html(self) -> str: ...

    @abstractmethod
    def get_form_handler(self) -> BaseFormHandler: ...

    @abstractmethod
    def execute(self, request: HttpRequest, form_handler: BaseFormHandler) -> None: ...

    def on_display(self, request: HttpRequest, form_handler: BaseFormHandler) -> None:
        """Called once, only on a genuine "show a fresh form" GET (never
        on the throttled-block path, never on POST). Default no-op;
        override for a side effect that has to happen before the form
        is shown, like sending an out-of-band code."""
        return None
