from django.contrib.auth.models import AbstractUser
from django.http import HttpRequest, HttpResponseBase
from django.shortcuts import redirect
from django.views import View

from .constants import (
    DJANGO_AUTH_CHAIN_USER_HOME,
)


class DelegatingAuthenticatedRedirect(View):
    def __init__(self, delegate: View):
        self._delegate = delegate

    def _is_user_authenticated(self, request: HttpRequest):
        user = request.user
        return isinstance(user, AbstractUser) and user.is_authenticated

    def get(self, request: HttpRequest, html: str) -> HttpResponseBase:
        if self._is_user_authenticated(request):
            return redirect(DJANGO_AUTH_CHAIN_USER_HOME)

        return self._delegate.dispatch(request, "GET", html)

    def post(self, request: HttpRequest, html: str) -> HttpResponseBase:
        if self._is_user_authenticated(request):
            return redirect(DJANGO_AUTH_CHAIN_USER_HOME)

        return self._delegate.dispatch(request, "POST", html)
