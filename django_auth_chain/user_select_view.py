from django.contrib.auth.models import User
from django.http import HttpRequest, HttpResponseBase
from django.shortcuts import redirect
from django.views import View

from .constants import (
    DJANGO_AUTH_CHAIN_VERIFY,
    PENDING_VERIFICATION_USER_KEY,
    USER_SELECT_HTML,
    VERIFIED_METHOD_CODES,
)
from .form_handlers import UserSelectFormHandler
from .models import UserAuthMethod
from .redirect_if_authenticated import RedirectIfAuthenticatedMixin
from .utils import clear_pending_user


class UserSelectView(RedirectIfAuthenticatedMixin, View):
    def get(self, request: HttpRequest) -> HttpResponseBase:
        clear_pending_user(request)
        form_handler = UserSelectFormHandler()
        form_handler.fill_form_from_none()
        return form_handler.render_with_form(request, USER_SELECT_HTML)

    def post(self, request: HttpRequest) -> HttpResponseBase:
        form_handler = UserSelectFormHandler()
        form_handler.fill_form_from_request_data(request.POST)
        if not form_handler.is_form_valid():
            return form_handler.render_with_form(request, USER_SELECT_HTML)

        user_identifier = form_handler.get_form().cleaned_data["user_identifier"]
        user = User.objects.filter(username__iexact=user_identifier).first()
        has_any_method = user is not None and UserAuthMethod.objects.filter(
            user=user,
            enabled=True,
        ).exists()

        if user is None or not has_any_method:
            form_handler.add_error(None, "Invalid username.")
            return form_handler.render_with_form(request, USER_SELECT_HTML)

        request.session[PENDING_VERIFICATION_USER_KEY] = user.pk
        request.session[VERIFIED_METHOD_CODES] = []
        return redirect(DJANGO_AUTH_CHAIN_VERIFY)
