from django.contrib.auth.models import (
    AbstractUser,
)
from django.http import HttpRequest, HttpResponseBase
from django.shortcuts import redirect
from django.views import View

from .constants import DJANGO_AUTH_CHAIN_USER_HOME

# from .enroll_view import EnrollView
# from .verify_view import VerifyView

class DelegatingAuthenticatedRedirect(View):
    def __init__(self, delegate: View):
        self._delegate = delegate

    def _is_user_authenticated(self, request: HttpRequest):
        user = request.user
        return isinstance(user, AbstractUser) and user.is_authenticated

    def get(self, request: HttpRequest) -> HttpResponseBase:
        if self._is_user_authenticated(request):
            return redirect(DJANGO_AUTH_CHAIN_USER_HOME)

        return self._delegate.dispatch(request)


    def post(self, request: HttpRequest) -> HttpResponseBase:
        if self._is_user_authenticated(request):
            return redirect(DJANGO_AUTH_CHAIN_USER_HOME)

        return self._delegate.dispatch(request, "POST")

