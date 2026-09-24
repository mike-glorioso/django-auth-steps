from django.http import HttpRequest, HttpResponseBase
from django.shortcuts import redirect

from .constants import DJANGO_AUTH_STEPS_USER_HOME


class RedirectIfAuthenticatedMixin:
    """Mix in before django.views.View: sends an already-authenticated
    user straight home instead of back through sign-in."""

    def dispatch(self, request: HttpRequest, *args: object, **kwargs: object) -> HttpResponseBase:
        if request.user.is_authenticated:
            return redirect(DJANGO_AUTH_STEPS_USER_HOME)
        return super().dispatch(request, *args, **kwargs)  # type: ignore[misc]
