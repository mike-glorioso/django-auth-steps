from django.contrib.auth import logout as auth_logout
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.views import View

from .constants import DJANGO_AUTH_CHAIN_USER_HOME, DJANGO_AUTH_CHAIN_USER_SELECT


class LogoutView(View):
    def get(self, request: HttpRequest) -> HttpResponse:
        auth_logout(request)
        return redirect(DJANGO_AUTH_CHAIN_USER_HOME)


class UserHomeView(View):
    def get(self, request: HttpRequest) -> HttpResponse:
        if not request.user.is_authenticated:
            return redirect(DJANGO_AUTH_CHAIN_USER_SELECT)
        return HttpResponse(f"Signed in as {request.user}.")
